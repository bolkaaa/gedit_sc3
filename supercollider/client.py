# -*- coding: utf-8 -*-
# Copyright 2009-2011 Artem Popov and contributors (see AUTHORS)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import time


class SCClient(object):

    def __init__(self):
        self._client = None

    def start(self):
        if self.running():
            return
        self._client = subprocess.Popen(
                ["sclang", "-i", "sced"],
                bufsize=0,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=True)
        self.stdout = self._client.stdout
        self.stdin = self._client.stdin

    def stop(self):
        if self.running():
            self.stdin.close()
            self._client.wait()
            self._client = None

    def running(self):
        return (self._client is not None) and (self._client.poll() is None)

    def evaluate(self, code, silent=False):
        self.stdin.write(bytes(code, 'utf-8'))
        if silent:
            self.stdin.write(bytes("\x1b", 'utf-8'))
        else:
            self.stdin.write(bytes("\x0c", 'utf-8'))
        self.stdin.flush()

    def toggle_recording(self, record):
        if record:
            self.evaluate("s.prepareForRecord;", silent=True)
            time.sleep(0.1)
            self.evaluate("s.record;", silent=True)
        else:
            self.evaluate("s.stopRecording;", silent=True)

    def stop_sound(self):
        self.evaluate("thisProcess.stop;", silent=True)
