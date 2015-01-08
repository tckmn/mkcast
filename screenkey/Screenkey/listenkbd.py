# Copyright (c) 2010 Pablo Seminario <pabluk@gmail.com>
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

import threading
import time
import sys
import subprocess
import modmap
import gtk

from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq

MODE_RAW = 0
MODE_NORMAL = 1

REPLACE_KEYS = {
    'XK_Escape':_('Esc '),
    'XK_Tab':u'\u21B9 ',
    'XK_Return':u'\u23CE ',
    'XK_Space':u' ',
    'XK_Caps_Lock':_('Caps '),
    'XK_F1':u'F1 ',
    'XK_F2':u'F2 ',
    'XK_F3':u'F3 ',
    'XK_F4':u'F4 ',
    'XK_F5':u'F5 ',
    'XK_F6':u'F6 ',
    'XK_F7':u'F7 ',
    'XK_F8':u'F8 ',
    'XK_F9':u'F9 ',
    'XK_F10':u'F10 ',
    'XK_F11':u'F11 ',
    'XK_F12':u'F12 ',
    'XK_Home':_('Home '),
    'XK_Up':u'\u2191',
    'XK_Page_Up':_('PgUp '),
    'XK_Left':u'\u2190',
    'XK_Right':u'\u2192',
    'XK_End':_('End '),
    'XK_Down':u'\u2193',
    'XK_Next':_('PgDn '),
    'XK_Insert':_('Ins '),
    'XK_Delete':_('Del '),
    'XK_KP_Home':u'(7)',
    'XK_KP_Up':u'(8)',
    'XK_KP_Prior':u'(9)',
    'XK_KP_Left':u'(4)',
    'XK_KP_Right':u'(6)',
    'XK_KP_End':u'(1)',
    'XK_KP_Down':u'(2)',
    'XK_KP_Page_Down':u'(3)',
    'XK_KP_Begin':u'(5)',
    'XK_KP_Insert':u'(0)',
    'XK_KP_Delete':u'(.)',
    'XK_KP_Add':u'(+)',
    'XK_KP_Subtract':u'(-)',
    'XK_KP_Multiply':u'(*)',
    'XK_KP_Divide':u'(/)',
    'XK_Num_Lock':u'NumLock ',
    'XK_KP_Enter':u'\u23CE ',
}

class ListenKbd(threading.Thread):

    def __init__(self, label, logger, mode):
        threading.Thread.__init__(self)
        self.mode = mode
        self.logger = logger
        self.label = label
        self.text = ""
        self.command = None
        self.shift = None
        self.cmd_keys = {
            'shift': False,
            'ctrl': False,
            'alt': False,
            'capslock': False,
            'meta': False,
            'super':False
            }

        self.logger.debug("Thread created")
        self.keymap = modmap.get_keymap_table()
        self.modifiers = modmap.get_modifier_map()

        self.local_dpy = display.Display()
        self.record_dpy = display.Display()

        if not self.record_dpy.has_extension("RECORD"):
            self.logger.error("RECORD extension not found.")
            print "RECORD extension not found"
            sys.exit(1)

        self.ctx = self.record_dpy.record_create_context(
                0,
                [record.AllClients],
                [{
                        'core_requests': (0, 0),
                        'core_replies': (0, 0),
                        'ext_requests': (0, 0, 0, 0),
                        'ext_replies': (0, 0, 0, 0),
                        'delivered_events': (0, 0),
                        'device_events': (X.KeyPress, X.KeyRelease),
                        'errors': (0, 0),
                        'client_started': False,
                        'client_died': False,
                }])

    def run(self):
        self.logger.debug("Thread started.")
        self.record_dpy.record_enable_context(self.ctx, self.key_press)

    def lookup_keysym(self, keysym):
        for name in dir(XK):
            if name[:3] == "XK_" and getattr(XK, name) == keysym:
                return name[3:]
        return ""

    def replace_key(self, key, keysym):
        for name in dir(XK):
            if name[:3] == "XK_" and getattr(XK, name) == keysym:
                if name in REPLACE_KEYS:
                    return REPLACE_KEYS[name]

    def update_text(self, string=None):
        gtk.gdk.threads_enter()
        if not string is None:
            self.text = "%s%s" % (self.label.get_text(), string)
            self.label.set_text(self.text)
        else:
            self.label.set_text("")
        gtk.gdk.threads_leave()
        self.label.emit("text-changed")

    def key_press(self, reply):

        # FIXME:
        # This is not the most efficient way to detect the
        # use of sudo/gksudo but it works.
        sudo_is_running = subprocess.call(['ps', '-C', 'sudo'],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not sudo_is_running:
            return

        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            self.logger.warning(
                "* received swapped protocol data, cowardly ignored"
            )
            return
        if not len(reply.data) or ord(reply.data[0]) < 2:
            # not an event
            return
        data = reply.data
        key = None
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data,
                                    self.record_dpy.display, None, None)
            if event.type in [X.KeyPress, X.KeyRelease]:
                if self.mode == MODE_NORMAL:
                    key = self.key_normal_mode(event)
                if self.mode == MODE_RAW:
                    key = self.key_raw_mode(event)
                if not key:
                    return
        self.update_text(key)

    def key_normal_mode(self, event):
        key = ''
        mod = ''
        keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)

        if event.detail in self.keymap:
            key_normal, key_shift, key_dead, key_deadshift = \
                                            self.keymap[event.detail]
            self.logger.debug("Key %s(keycode) %s. Symbols %s" %
                (event.detail,
                 event.type == X.KeyPress and "pressed" or "released",
                 self.keymap[event.detail])
                )
        else:
            self.logger.debug('No mapping for scan_code %d' % event.detail)
            return


        # Alt key
        if event.detail in self.modifiers['mod1']:
            if event.type == X.KeyPress:
                self.cmd_keys['alt'] = True
            else:
                self.cmd_keys['alt'] = False
            return
        # Meta key
        # Fixme: it must use self.modifiers['mod5']
        #        but doesn't work
        if event.detail == 108:
            if event.type == X.KeyPress:
                self.cmd_keys['meta'] = True
            else:
                self.cmd_keys['meta'] = False
            return
        # Super key
        if event.detail in self.modifiers['mod4']:
            if event.type == X.KeyPress:
                self.cmd_keys['super'] = True
            else:
                self.cmd_keys['super'] = False
            return
        # Ctrl keys
        elif event.detail in self.modifiers['control']:
            if event.type == X.KeyPress:
                self.cmd_keys['ctrl'] = True
            else:
                self.cmd_keys['ctrl'] = False
            return
        # Shift keys
        elif event.detail in self.modifiers['shift']:
            if event.type == X.KeyPress:
                self.cmd_keys['shift'] = True
            else:
                self.cmd_keys['shift'] = False
            return
        # Capslock key
        elif event.detail in self.modifiers['lock']:
            if event.type == X.KeyPress:
                if self.cmd_keys['capslock']:
                    self.cmd_keys['capslock'] = False
                else:
                    self.cmd_keys['capslock'] = True
            return
        # Backspace key
        elif event.detail == 22 and event.type == X.KeyPress:
            gtk.gdk.threads_enter()
            if len(self.label.get_text()) > 0:
                self.label.set_text(
                    unicode(self.label.get_text(), 'utf-8')[:-1]
                )
                key = ""
                gtk.gdk.threads_leave()
            else:
                gtk.gdk.threads_leave()
                return
        else:
            if event.type == X.KeyPress:
                key = key_normal
                if self.cmd_keys['ctrl']:
                    mod = mod + _("Ctrl+")
                if self.cmd_keys['alt']:
                    mod = mod + _("Alt+")
                if self.cmd_keys['super']:
                    mod = mod + _("Super+")

                if self.cmd_keys['shift']:
                    key = key_shift
                if self.cmd_keys['capslock'] \
                    and ord(key_normal) in range(97,123):
                    key = key_shift
                if self.cmd_keys['meta']:
                    key = key_dead
                if self.cmd_keys['shift'] and self.cmd_keys['meta']:
                    key = key_deadshift

                string = self.replace_key(key, keysym)
                if string:
                    key = string

                if mod != '':
                    key = "%s%s " % (mod, key)
                else:
                    key = "%s%s" % (mod, key)
            else:
                return

        return key

    def key_raw_mode(self, event):
        key = ''
        if event.type == X.KeyPress:
            keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
            key = self.lookup_keysym(keysym)
        else:
            return
        return key

    def stop(self):
        self.local_dpy.record_disable_context(self.ctx)
        self.local_dpy.flush()
        self.record_dpy.record_free_context(self.ctx)
        self.logger.debug("Thread stopped.")

