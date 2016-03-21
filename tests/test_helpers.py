from openetv_libs import vlc
from openetv_libs import helpers
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


def test_open_file_read_fail():
    try:
        helpers.open_file('/nonexistant', 'r', 'error message')
    except IOError as err:
        assert err.extra_info == 'error message'


def test_open_file_write_fail():
    try:
        helpers.open_file('/nonexistant', 'w', 'error message')
    except IOError as err:
        assert err.extra_info == 'error message'


def test_open_file_write_succeed():
    fname = tempfile.mkstemp()[1]
    try:
        with helpers.open_file(fname, 'w', 'error message') as f:
            f.write('test')
        with open(fname, 'r') as f:
            assert f.read() == 'test'
    finally:
        os.remove(fname)


def test_open_file_read_succeed():
    fname = tempfile.mkstemp()[1]
    with open(fname, 'w') as f:
        f.write('test')
    try:
        with helpers.open_file(fname, 'r', 'error message') as f:
            assert f.read() == 'test'
    finally:
        os.remove(fname)


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


