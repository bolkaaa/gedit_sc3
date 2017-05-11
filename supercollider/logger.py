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

import re
from gi.repository import GObject, Gtk, Pango

SC_MSG_ERROR = b'ERROR'
SC_MSG_WARNING = b'WARNING'
SC_MSG_FAILURE = b'FAILURE'
SC_MSG_WELCOME = b'Welcome to SuperCollider'
SC_MSG_RECORDING = b'Recording: '


class LogBottomPanel(Gtk.ScrolledWindow):
    def __init__(self, namespace={}):
        Gtk.ScrolledWindow.__init__(self)
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.set_border_width(0)
        self.view = Gtk.TextView()
        self.view.set_property('can-focus', True)
        self.view.modify_font(Pango.FontDescription("Monospace"))
        self.view.set_editable(False)
        self.view.set_wrap_mode(True)
        self.view.set_left_margin(1)
        self.view.set_right_margin(1)
        self.view.set_size_request(0, 0)
        self.buffer = self.view.get_buffer()
        self.add(self.view)
        self.view.show()


class LogPipe(object):

    def __init__(self, pipe, panel_view):
        self._rec_file = None
        self._panel_view = panel_view
        tag_table = panel_view.buffer.get_tag_table()
        self._tag = Gtk.TextTag()
        self._good_tag = GObject.new(
            Gtk.TextTag,
            weight=Pango.Weight.BOLD,
            foreground="darkgreen",
            paragraph_background="lightgreen"
        )
        self._bad_tag = GObject.new(
            Gtk.TextTag,
            weight=Pango.Weight.BOLD,
            foreground="darkred",
            paragraph_background="pink"
        )
        self._ugly_tag = GObject.new(
            Gtk.TextTag,
            foreground="red"
        )
        self._rec_tag = GObject.new(
            Gtk.TextTag,
            weight=Pango.Weight.BOLD,
            foreground="white",
            paragraph_background="orange"
        )
        tag_table.add(self._tag)
        tag_table.add(self._good_tag)
        tag_table.add(self._bad_tag)
        tag_table.add(self._ugly_tag)
        tag_table.add(self._rec_tag)

        self._watch_id = GObject.io_add_watch(
            pipe,
            GObject.IO_IN |
            GObject.IO_PRI |
            GObject.IO_ERR |
            GObject.IO_HUP,
            self._on_output
        )

    def _on_output(self, source, condition):
        s = source.readline()
        if s == '':
            self._append_to_buffer("EOF")
            return False
        self._append_to_buffer(bytes(s))
        if condition & GObject.IO_ERR:
            s = source.read()
            self._append_to_buffer(bytes(s))
            return False
        elif condition & GObject.IO_HUP:
            s = source.read()
            self._append_to_buffer(bytes(s))
            return False
        elif condition != 1:
            return False
        return True

    def _append_to_buffer(self, text):
        buffer = self._panel_view.buffer

        if text.startswith(SC_MSG_ERROR):
            tags = self._bad_tag
        elif text.startswith(SC_MSG_WARNING) \
                or text.startswith(SC_MSG_FAILURE):
            tags = self._ugly_tag
        elif text.startswith(SC_MSG_WELCOME):
            tags = self._good_tag
        elif text.startswith(SC_MSG_RECORDING):
            tags = self._rec_tag
            m = re.match(b'Recording: ([^&]*)', text)
            self._rec_file = m.group(1).decode('UTF-8').rstrip()
        else:
            tags = self._tag

        buffer.insert_with_tags(
            buffer.get_end_iter(),
            text.decode('UTF-8').rstrip(),
            tags
        )

        buffer.insert(buffer.get_end_iter(), "\n")
        buffer.place_cursor(buffer.get_end_iter())
        self._panel_view.view.scroll_mark_onscreen(buffer.get_insert())

    def stop(self):
        GObject.source_remove(self._watch_id)
