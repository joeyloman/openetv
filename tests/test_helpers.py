from openetv_libs import vlc
from openetv_libs import helpers
import tempfile
import logging
import os


class TestHelpers(object):
    @classmethod
    def setup_class(cls):
        cls.pidfile = tempfile.mkstemp()[1]
        with open(cls.pidfile, 'w') as f:
            f.write('15')

    @classmethod
    def delete_class(cls):
        try:
            os.remove(cls.pidfile)
        except OSError:
            pass

    def test_open_file_read_fail(self):
        try:
            helpers.open_file('/nonexistant', 'r', 'error message')
        except IOError as err:
            assert err.extra_info == 'error message'

    def test_open_file_write_fail(self):
        try:
            helpers.open_file('/nonexistant', 'w', 'error message')
        except IOError as err:
            assert err.extra_info == 'error message'

    def test_open_file_write_succeed(self):
        fname = tempfile.mkstemp()[1]
        try:
            with helpers.open_file(fname, 'w', 'error message') as f:
                f.write('test')
            with open(fname, 'r') as f:
                assert f.read() == 'test'
        finally:
            os.remove(fname)

    def test_open_file_read_succeed(self):
        fname = tempfile.mkstemp()[1]
        with open(fname, 'w') as f:
            f.write('test')
        try:
            with helpers.open_file(fname, 'r', 'error message') as f:
                assert f.read() == 'test'
        finally:
            os.remove(fname)

    def test_get_pid(self):
        pid = vlc.get_vlc_pid(self.pidfile, logging)
        assert int(pid) == 15

    def test_remove_pid(self):
        vlc.remove_vlc_pid(self.pidfile)
        assert os.path.exists(self.pidfile) == False

    def test_write_pid(self):
        pfile = tempfile.mkstemp()[1]
        vlc.write_vlc_pid(pfile, 15)
        try:
            with open(pfile, 'r') as f:
                assert f.read() == '15'
        finally:
            os.remove(pfile)


