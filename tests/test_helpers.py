from openetv_libs import vlc
from nose import with_setup
import tempfile
import logging
import os

pidfile = str()


def setup_pid():
    global pidfile
    pidfile = tempfile.mkstemp()[1]
    with open(pidfile, 'w') as f:
        f.write('15')


def delete_pid():
    try:
        os.remove(pidfile)
    except OSError:
        pass


@with_setup(setup=setup_pid, teardown=delete_pid)
def test_get_pid():
    pid = vlc.get_vlc_pid(pidfile, logging)
    assert int(pid) == 15


@with_setup(setup=setup_pid, teardown=delete_pid)
def test_remove_pid():
    vlc.remove_vlc_pid(pidfile)
    assert os.path.exists(pidfile) == False


def test_write_pid():
    pfile = tempfile.mkstemp()[1]
    vlc.write_vlc_pid(pfile, 15)
    try:
        with open(pfile, 'r') as f:
            assert f.read() == '15'
    finally:
        os.remove(pfile)
