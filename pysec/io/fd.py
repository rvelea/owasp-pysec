# Python Security Project (PySec) and its related class files.
#
# PySec is a set of tools for secure application development under Linux
#
# Copyright 2014 PySec development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# -*- coding: ascii -*-
"""Contains FD and FD-like classes for operations with file descriptors"""
from pysec.core import Error, Object, unistd
from pysec.xsplit import xlines
from pysec.alg import knp_first
from pysec.io import fcheck
from pysec.utils import xrange
from pysec import log
import os
import fcntl


__name__ = 'pysec.io.fd'


class FDError(Error):
    """Generic error for fd module"""

    def __init__(self, fd):
        super(FDError, self).__init__()
        self.fd = int(fd)


class NotReadableFD(FDError):
    """Raise when try to read a no-readable fd"""
    pass


class NotWriteableFD(FDError):
    """Raise when try to write a no-writeable fd"""
    pass


class IncompleteWrite(FDError):
    """Raise when write operation was not successfully
    performed"""

    def __init__(self, fd, size):
        super(IncompleteWrite, self).__init__(fd)
        self.size = int(size)


def read_check(func):
    """Decorator to control read permission in reader methods"""
    def _read(fd, *args, **kargs):
        """*func* wrapped with read check"""
        if not fd.flags & os.O_WRONLY:
            return func(fd, *args, **kargs)
        raise NotReadableFD(fd)
    return _read


def write_check(func):
    """Decorator to control write permission in writer methods"""
    def _write(fd, *args, **kargs):
        """*func* wrapped with write check"""
        if fd.flags & os.O_WRONLY or fd.flags & os.O_APPEND:
            return func(fd, *args, **kargs)
        raise NotWriteableFD(fd)
    return _write


log.register_actions('FD_NEW', 'FD_CLOSE')


class FD(Object):
    """FD represents a File Descriptor"""

    @log.wrap(log.actions.FD_NEW, fields=('fd',), lib=__name__)
    def __init__(self, fd):
        fd = int(fd)
        if fd < 0:
            raise ValueError("wrong fd value")
        self.fd = fd

    def fileno(self):
        """Return file descriptor's int"""
        return int(self.fd)

    def __int__(self):
        """Return file descriptor's int"""
        return int(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return 0

    @log.wrap(log.actions.FD_CLOSE, fields=('path',), lib=__name__)
    def close(self):
        """Closes file descriptor"""
        unistd.close(self.fd)

    # stat methods
    def stat(self):
        """Returns result of a stat call"""
        return os.fstat(self.fd)

    @property
    def mode(self):
        """Get inode protection mode. See stat()"""
        return os.fstat(self.fd).st_mode

    @property
    def inode(self):
        """Get inode number. See stat()"""
        return os.fstat(self.fd).st_ino

    @property
    def device(self):
        """Get device inode resides on. See stat()"""
        return os.fstat(self.fd).st_dev

    @property
    def nlink(self):
        """Get number of links to the inode. See stat()"""
        return os.fstat(self.fd).st_nlink

    @property
    def uid(self):
        """Get user id of the owner. See stat()"""
        return os.fstat(self.fd).st_uid

    @property
    def gid(self):
        """Get group id of the owner. See stat()"""
        return os.fstat(self.fd).st_gid

    @property
    def size(self):
        """Get size in bytes of a lain file, or amount of data waiting on some
        special files. See stat()"""
        return os.fstat(self.fd).st_size

    @property
    def atime(self):
        """Get last access time. See stat()"""
        return os.fstat(self.fd).st_atime

    @property
    def mtime(self):
        """Get last modification time. See stat()"""
        return os.fstat(self.fd).st_mtime

    @property
    def ctime(self):
        """The *ctime* as reported by the operating system. On some systems
        (like Unix) is the time of the last metadata change, and, on others
        (like Windows), is the creation time (see platform documentation for
        details)."""
        return os.fstat(self.fd).st_ctime

    # fcntl methods
    @property
    def flags(self):
        """Get file descriptor's flags (fcntl.F_GETFL)"""
        return int(fcntl.fcntl(self.fd, fcntl.F_GETFL))

    @flags.setter
    def flags(self, flags):
        """Set file descriptor's flags (fcntl.F_SETFL)"""
        fcntl.fcntl(self.fd, fcntl.F_SETFL, int(flags))


### Open modes for regular files
# create a new file and raise error if it exists, use read mode
FO_READNEW = 0
# read only and raise error if it doesn't exists
FO_READEX = 1
# create a new file and raise error if it exists, use write mode
FO_WRNEW = 2
# open a existing file in write mode
FO_WREX = 3
# open a existing file in write mode and truncate it
FO_WREXTR = 4
# create a new file and raise error if it exists, use append mode
FO_APNEW = 5
# open a existing file in append mode
FO_APEX = 6
# open a existing file in append mode and truncate it
FO_APEXTR = 7
# open the file in read-only mode, if it doesn't exist create it
FO_READ = 8
# open the file in write-only mode, if it doesn't exist create it
FO_WRITE = 9
# open the file in append mode, if it doesn't exist create it
FO_APPEND = 10


_FO_NEW_MODES = FO_READNEW, FO_WRNEW, FO_APNEW, FO_READ, FO_WRITE, FO_APPEND


FO_MODES = FO_READNEW, FO_READEX, FO_WRNEW, FO_WREX, FO_WREXTR, \
           FO_APNEW, FO_APEX, FO_APEXTR, FO_READ, FO_WRITE, FO_APPEND


def _fo_readnew(fpath, mode):
    """Creates and open a regular file in read-only mode,
    raises an error if it exists"""
    return os.open(fpath, os.O_RDONLY | os.O_CREAT | os.O_EXCL, mode)


def _fo_readex(fpath, _):
    """Opens a regular file in read-only mode,
    raises an error if it doesn't exists"""
    return os.open(fpath, os.O_RDONLY)


def _fo_wrnew(fpath, mode):
    """Creates and opens a regular file in write-only,
    raises an error if it exists"""
    return os.open(fpath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)


def _fo_wrex(fpath, _):
    """Opens a regular file in write-only mode,
    raises an error if it doesn't exists"""
    return os.open(fpath, os.O_WRONLY)

    
def _fo_wrextr(fpath, _):
    """Opens a regular file in write-only mode and truncates it,
    raises an error if it doesn't exists"""
    return os.open(fpath, os.O_WRONLY | os.O_TRUNC)
    

def _fo_apnew(fpath, mode):
    """Creates and opens a regular file in append mode,
    raises an error if it exists"""
    return os.open(fpath, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL, mode)


def _fo_apex(fpath, _):
    """Opens a regular file in append mode,
    raises an error if it doesn't exists"""
    return os.open(fpath, os.O_WRONLY | os.O_APPEND)


def _fo_apextr(fpath, _):
    """Opens a regular file in append mode and truncates it,
    raises an error if it doesn't exists"""
    return os.open(fpath, os.O_WRONLY | os.O_APPEND | os.O_TRUNC)


def _fo_read(fpath, mode):
    """Opens a regular file in read-only mode,
    if it doesn't exist a new file will be created"""
    return os.open(fpath, os.O_RDONLY | os.O_CREAT, mode)


def _fo_write(fpath, mode):
    """Opens a regular file in write-only mode,
    if it doesn't exist a new file will be created"""
    return os.open(fpath, os.O_WRONLY | os.O_CREAT, mode)


def _fo_append(fpath, mode):
    """Opens a regular file in append mode,
    if it doesn't exist a new file will be created"""
    return os.open(fpath, os.O_WRONLY | os.O_APPEND | os.O_CREAT, mode)


FO_READNEW, FO_READEX, FO_WRNEW, FO_WREX, FO_WREXTR, \
           FO_APNEW, FO_APEX, FO_READ, FO_WRITE, FO_APPEND

_FOMODE2FUNC = _fo_readnew, _fo_readex, _fo_wrnew, _fo_wrex, _fo_wrextr, \
               _fo_apnew, _fo_apex, _fo_apextr,_fo_read, _fo_write, _fo_append


log.register_actions('REGFILE_OPEN', 'REGFILE_READ', 'REGFILE_WRITE',
                     'REGFILE_PREAD', 'REGFILE_PWRITE', 'REGFILE_MOVE',
                     'REGFILE_TRUNC')


class File(FD):
    """File represents a Regular File's file descriptor."""

    def __init__(self, fd):
        super(self.__class__, self).__init__(fd)
        self.pos = 0

    def __len__(self):
        """Returns file's size"""
        return self.size

    def __getitem__(self, index):
        if isinstance(index, int):
            return self.pread(1, index)
        elif isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            if step == 1:
                return self.pread(stop - start, start)
            else:
                return ''.join(self.pread(1, pos) for pos
                               in xrange(start, stop, step))
        raise IndexError('wrong index type: %s' % type(index))

    @staticmethod
    @log.wrap(log.actions.REGFILE_OPEN,
              fields=('fpath', 'oflag', 'mode'), lib=__name__)
    def open(fpath, oflag, mode=0666):
        """Open a file descript for a regular file in fpath using the open mode
        specifie by *oflag* with *mode*"""
        oflag = int(oflag)
        if oflag not in FO_MODES:
            raise ValueError("unknown file open mode: %r" % oflag)
        mode = int(mode)
        if not fcheck.mode_check(mode):
            raise ValueError("wrong mode: %r" % oct(mode))
        fopen = _FOMODE2FUNC[oflag]
        fd = -1
        try:
            fd = fopen(fpath, mode)
            fd = File(fd)
            if mode in _FO_NEW_MODES and not fcheck.ino_check(int(fd)):
                raise OSError("not enough free inodes")
        except:
            if fd > -1:
                os.close(fd)
            raise
        return fd

    @staticmethod
    def touch(fpath, mode=0666):
        """Create a new file with passed *mode* in *fpath*.
        If file *fpath* exists, a IOError will be raised."""
        mode = int(mode)
        if not fcheck.mode_check(mode):
            raise ValueError("wrong mode: %r" % oct(mode))
        fd = -1
        try:
            fd = os.open(fpath, os.O_RDONLY | os.O_CREAT, mode)
        finally:
            if fd >= 0:
                os.close(fd)

    @read_check
    @log.wrap(log.actions.REGFILE_READ, fields=('size', 'pos'), lib=__name__)
    def read(self, size=None, pos=None):
        """Read *pos*-length data starting from position *pos*."""
        size = int(self.size) if size is None else int(size)
        pos = int(self.pos if pos is None else pos)
        if size < 0:
            raise ValueError("invalid size, %d" % size)
        chunk = unistd.pread(self.fd, size, pos)
        self.pos = pos + len(chunk)
        return chunk

    @read_check
    @log.wrap(log.actions.REGFILE_PREAD, fields=('size', 'pos'), lib=__name__)
    def pread(self, size=None, pos=None):
        """Read *pos*-length data starting from position *pos*.
        This operation doesn't change the pointer position."""
        size = int(self.size) if size is None else int(size)
        pos = int(self.pos if pos is None else pos)
        if size < 0:
            raise ValueError("invalid size, %d" % size)
        chunk = unistd.pread(self.fd, size, pos)
        return chunk

    @write_check
    @log.wrap(log.actions.REGFILE_WRITE, fields=('data', 'pos'), lib=__name__)
    def write(self, data, pos=None, tries=3):
        """Write data starting from position *pos* and do maximum *tries*
        write attempt, if all will fail it raises a IncompleteWrite
        exception. This operation moves the position pointer at end of written
        data."""
        fd = int(self)
        _tries = tries = int(tries)
        pos = int(self.pos if pos is None else pos)
        data = str(data)
        if not data:
            return
        dlen = len(data)
        dev = self.device
        if not fcheck.space_check(fd, dlen):
            raise OSError("not enough free space in device %r" % dev)
        wlen = 0
        while wlen < dlen:
            _wlen = unistd.pwrite(fd, data[wlen:], pos + wlen)
            if not _wlen:
                _tries -= 1
                if not _tries:
                    raise IncompleteWrite(fd, pos, tries)
            else:
                wlen += _wlen
                _tries = tries
        self.pos = pos + wlen

    @write_check
    @log.wrap(log.actions.REGFILE_READ, fields=('data', 'pos'), lib=__name__)
    def pwrite(self, data, pos=None, tries=3):
        """Write data starting from position *pos* and do maximum *tries*
        write attempt, if all will fail it raises a IncompleteWrite
        exception. This operation doesn't change the pointer position."""
        fd = int(self)
        _tries = tries = int(tries)
        pos = int(self.pos if pos is None else pos)
        data = str(data)
        if not data:
            return
        dlen = len(data)
        dev = self.device
        if not fcheck.space_check(fd, dlen):
            raise OSError("not enough free space in device %r" % dev)
        wlen = 0
        while wlen < dlen:
            _wlen = unistd.pwrite(fd, data[wlen:], pos + wlen)
            if not _wlen:
                _tries -= 1
                if not _tries:
                    raise IncompleteWrite(fd, pos, tries)
            else:
                wlen += _wlen
                _tries = tries

    @write_check
    @log.wrap(log.actions.REGFILE_TRUNC, fields=('length',), lib=__name__)
    def truncate(self, length=0):
        """Truncate the file and if the pointer is in a inexistent part of file
        it will be moved to the end of file."""
        fd = int(self)
        length = int(length)
        if length < 0:
            raise ValueError("negative length: %r" % length)
        size = self.size
        os.ftruncate(fd, length)
        if size > length:
            self.moveto(length)

    @log.wrap(log.actions.REGFILE_MOVE, fields=('pos',), lib=__name__)
    def moveto(self, pos):
        """Move position pointer in position *pos* from start of FD."""
        pos = int(pos)
        if pos < 0:
            raise ValueError("invalid negative position: %d" % pos)
        self.pos = pos

    def lines(self, start=None, stop=None, eol='\n', keep_eol=0):
        """Splits FD's content in lines that end with *eol*, it'll start from
        *start* position and it'll stop at stop position, if *stop* is None it
        will stop at the end of FD. If keep_eol is true doesn't remove *eol*
        from the line"""
        start = self.pos if start is None else int(start)
        return xlines(self, eol, keep_eol, start, stop, knp_first)

    def chunks(self, size,  start=0, stop=None):
        """Divides FD's content in chunk of length *size* starting from *start*
        and stopping at *stop*, if *stop* is None it'll stop at end of FD's
        content."""
        size = int(size)
        for offset in xrange(*slice(int(start),
                             None if stop is None
                             else int(stop), size).indices(len(self))):
            yield self.pread(size, offset)


class Directory(FD):
    """Directory represents a Directory's file descriptor."""

    def __init__(self, fd):
        super(self.__class__, self).__init__(fd)
        """pos field is unused but might be useful if we implement __getitem__ in the future"""
        self.pos = 0

    @staticmethod
    def open(path):
        """Open a file descriptor for a directory path using read-only mode. We keep a copy of the 
        directory path within the object for future reference. The object created will keep a file
        descriptor opened for the corresponding directory until close or destructor is called"""
        fd = -1
        try:
            fd = unistd.opendir(path)
            fd = Directory(fd)
            fd.path = path
        except:
            if fd > -1:
                os.close(fd)
            raise
        return fd

    def readdir(self):
        """Return a list of files and subdirectories contained in the current directory"""
        return unistd.readdir(self.fd)

class Socket(FD):
    """File represents a Socket's file descriptor."""
    pass


class BlockDev(FD):
    """File represents a Block Device's file descriptor."""
    pass


class CharDev(FD):
    """File represents a Character Device's file descriptor."""
    pass


class FIFO(FD):
    """File represents a FIFO's file descriptor."""
    pass
