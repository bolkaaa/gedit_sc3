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

from gi.repository import GObject, Gedit, Gio, Gtk

from .client import SCClient
from .helpers import find_block, is_block_beginning
from .logger import LogBottomPanel, LogPipe

SC_CODE_BUFFER_READ = 'Buffer.read(s, "{}");\n\t'
SC_CODE_POST = 'postln("{}");'

ACTIONS = [
    ('on_sc_evaluate', '<Control>e'),
    ('on_sc_evaluate_rec', '<Control>r'),
    ('on_sc_kill', '<Control>Escape'),
    ('on_sc_load_soundfile', '<Control>b'),
    ('on_sc_load_rec_soundfile', '<Control><Alt>b')
]


class ScedAppActivatable(GObject.Object, Gedit.AppActivatable):
    app = GObject.property(type=Gedit.App)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        for action, key in ACTIONS:
            self.app.set_accels_for_action('win.' + action, (key, None))

    def do_deactivate(self):
        for action, key in ACTIONS:
            self.app.remove_accelerator("win." + action, None)


class ScedWindowActivatable(GObject.Object, Gedit.WindowActivatable):

    __gtype_name__ = "ScedWindowActivatable"
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self._sc_activated = False
        self._sc_recording = False

    def do_activate(self):
        pass

    def do_deactivate(self):
        pass

    def do_update_state(self):
        if not self._sc_activated:
            if any(doc for doc in self.window.get_documents()
                   if doc.get_uri_for_display().endswith(('.scd', '.sc'))):
                self._enable_scmode()

    def _bind_actions(self):
        for action, key in ACTIONS:
            ga = Gio.SimpleAction(name=action)
            ga.connect('activate', getattr(self, action))
            self.window.add_action(ga)

    def _sc_quit(self):
        self._sc_activated = False
        self._lang.stop()
        self._pipe.stop()
        self._log_panel.destroy()

    def _enable_scmode(self):
        bottom_panel = self.window.get_bottom_panel()
        if not self._sc_activated:
            self._sc_activated = True
            self._lang = SCClient()
            self._lang.start()
            self._log_panel = LogBottomPanel()
            self._log_panel.show_all()
            self._pipe = LogPipe(self._lang.stdout, self._log_panel)
            bottom_panel.show()
            bottom_panel.add_titled(
                self._log_panel,
                'GeditSuperColliderConsolePanel',
                'SuperCollider'
            )
            self._bind_actions()
        else:
            self._sc_quit()

    def _post(self, text):
        self._lang.evaluate(SC_CODE_POST.format(text), silent=True)

    def on_sc_evaluate(self, action, data):
        doc = self.window.get_active_document()
        try:
            i1, i2 = doc.get_selection_bounds()
        except ValueError:
            i1 = doc.get_iter_at_mark(doc.get_insert())
            i1.set_line_offset(0)
            i2 = i1.copy()
            i2.forward_to_line_end()
            if is_block_beginning(doc.get_text(i1, i2, False)):
                try:
                    i1, i2 = find_block(doc, i1)
                except RuntimeError:
                    return
                doc.select_range(i1, i2)

        text = doc.get_text(i1, i2, False)
        self._lang.evaluate(text)

    def on_sc_evaluate_rec(self, action, data):
        if not self._sc_recording:
            self._lang.toggle_recording(True)
            self._sc_recording = True
        else:
            self._post('WARNING: you are already recording!')
        self.on_sc_evaluate(action, data)

    def on_sc_load_rec_soundfile(self, action, data):
        if self._pipe._rec_file:
            doc = self.window.get_active_document()
            doc.insert_at_cursor(
                SC_CODE_BUFFER_READ.format(self._pipe._rec_file)
            )
        else:
            self._post('WARNING: none recording has been done yet!')

    def on_sc_load_soundfile(self, action, data):
        dialog = Gtk.FileChooserDialog(
            "Please choose a file",
            self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_size(800, 400)
        dialog.set_select_multiple(True)
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Audio Files (wav or aiff)")
        filter_text.add_mime_type("audio/x-aiff")
        filter_text.add_mime_type("audio/x-wav")
        dialog.add_filter(filter_text)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            for uri in dialog.get_filenames():
                doc = self.window.get_active_document()
                doc.insert_at_cursor(SC_CODE_BUFFER_READ.format(uri))
        dialog.destroy()

    def on_sc_kill(self, action, data):
        if self._sc_recording:
            self._lang.toggle_recording(False)
            self._sc_recording = False
        self._lang.evaluate("thisProcess.stop;", silent=True)
