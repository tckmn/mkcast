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

import os
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import glib
import pango
import pickle
from threading import Timer

from Screenkey import APP_NAME, APP_DESC, APP_URL, VERSION, AUTHOR
from listenkbd import ListenKbd

POS_TOP = 0
POS_CENTER = 1
POS_BOTTOM = 2

SIZE_LARGE = 0
SIZE_MEDIUM = 1
SIZE_SMALL = 2

MODE_RAW = 0
MODE_NORMAL = 1

class Screenkey(gtk.Window):

    POSITIONS = {
        POS_TOP:_('Top'),
        POS_CENTER:_('Center'),
        POS_BOTTOM:_('Bottom'),
    }
    SIZES = {
        SIZE_LARGE:_('Large'),
        SIZE_MEDIUM:_('Medium'),
        SIZE_SMALL:_('Small'),
    }
    MODES = {
        MODE_RAW:_('Raw'),
        MODE_NORMAL:_('Normal'),
    }

    STATE_FILE = os.path.join(glib.get_user_cache_dir(), 
                              'screenkey.dat')

    def __init__(self, logger, nodetach):
        gtk.Window.__init__(self)

        self.timer = None
        self.logger = logger

        self.options = self.load_state()
        if not self.options:
            with open(os.path.join(os.path.dirname(__file__), '..', '..', 'screenkey.conf')) as f:
                self.options = eval(f.read())

        if not nodetach:
            self.logger.debug("Detach from the parent.")
            self.drop_tty()

        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_decorated(False)
        self.stick()
        self.set_property('accept-focus', False)
        self.set_property('focus-on-map', False)
        self.set_position(gtk.WIN_POS_CENTER)
        bgcolor = gtk.gdk.color_parse(self.options['bgcolor'])
        self.modify_bg(gtk.STATE_NORMAL, bgcolor)
        self.set_opacity(self.options['opacity'])

        gobject.signal_new("text-changed", gtk.Label, 
                        gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
        self.label = gtk.Label()
        self.label.set_justify(gtk.JUSTIFY_RIGHT)
        self.label.set_ellipsize(pango.ELLIPSIZE_START)
        self.label.connect("text-changed", self.on_label_change)
        self.label.show()
        self.add(self.label)

        self.screen_width = gtk.gdk.screen_width()   
        self.screen_height = gtk.gdk.screen_height() 
        self.set_window_size(self.options['size'])

        self.set_gravity(gtk.gdk.GRAVITY_CENTER)
        self.set_xy_position(self.options['position'])

        self.listenkbd = ListenKbd(self.label, logger=self.logger, 
                                   mode=self.options['mode'])
        self.listenkbd.start()


        menu = gtk.Menu()

        show_item = gtk.CheckMenuItem(_("Show keys"))
        show_item.set_active(True)
        show_item.connect("toggled", self.on_show_keys)
        show_item.show()
        menu.append(show_item)

        preferences_item = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        preferences_item.connect("activate", self.on_preferences_dialog)
        preferences_item.show()
        menu.append(preferences_item)


        about_item = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        about_item.connect("activate", self.on_about_dialog)
        about_item.show()
        menu.append(about_item)

        separator_item = gtk.SeparatorMenuItem()
        separator_item.show()
        menu.append(separator_item)

        image = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        image.connect("activate", self.quit)
        image.show()
        menu.append(image)
        menu.show()

        try:
            import appindicator
            self.systray = appindicator.Indicator(APP_NAME, 
                           'indicator-messages', 
                            appindicator.CATEGORY_APPLICATION_STATUS)
            self.systray.set_status(appindicator.STATUS_ACTIVE)
            self.systray.set_attention_icon("indicator-messages-new")
            self.systray.set_icon(
                    "preferences-desktop-keyboard-shortcuts")
            self.systray.set_menu(menu)
            self.logger.debug("Using AppIndicator.")
        except(ImportError):
            self.systray = gtk.StatusIcon()
            self.systray.set_from_icon_name(
                    "preferences-desktop-keyboard-shortcuts")
            self.systray.connect("popup-menu", 
                    self.on_statusicon_popup, menu)
            self.logger.debug("Using StatusIcon.")


        self.connect("delete-event", self.quit)

    def quit(self, widget, data=None):
        self.listenkbd.stop()
        gtk.main_quit()

    def load_state(self):
        """Load stored options"""
        options = None
        try:
            f = open(self.STATE_FILE, 'r')
            try:
                options = pickle.load(f)
                self.logger.debug("Options loaded.")
            except:
                f.close()
        except IOError:
            self.logger.debug("file %s does not exists." % 
                              self.STATE_FILE)
        return options

    def store_state(self, options):
        """Store options"""
        try:
            f = open(self.STATE_FILE, 'w')
            try:
                pickle.dump(options, f)
                self.logger.debug("Options saved.")
            except:
                f.close()
        except IOError:
            self.logger.debug("Cannot open %s." % self.STATE_FILE)

    def set_window_size(self, setting):
        """Set window and label size."""
        window_width = self.screen_width
        window_height = -1

        window_height = setting * self.screen_height / 100

        attr = pango.AttrList()
        attr.change(pango.AttrSize((
                    50 * window_height / 100) * 1000, 0, -1))
        attr.change(pango.AttrFamily(self.options['font'], 0, -1))
        attr.change(pango.AttrWeight(pango.WEIGHT_BOLD, 0, -1))
        attr.change(pango.AttrForeground(*self.options['color']))

        self.label.set_attributes(attr)
        self.resize(window_width, window_height)

    def set_xy_position(self, setting):
        """Set window position."""
        window_width, window_height = self.get_size()
        PADDING_MULT = 1.2
        if setting == POS_TOP:
            self.move(0, int(window_height * PADDING_MULT))
        if setting == POS_CENTER:
            self.move(0, self.screen_height / 2)
        if setting == POS_BOTTOM:
            self.move(0, self.screen_height - int(window_height * PADDING_MULT))

    def on_statusicon_popup(self, widget, button, timestamp, data=None):
        if button == 3:
            if data:
                data.show()
                data.popup(None, None, gtk.status_icon_position_menu, 
                           3, timestamp, widget)

    def on_label_change(self, widget, data=None):
        if not self.get_property('visible'):
            gtk.gdk.threads_enter()
            self.set_xy_position(self.options['position'])
            self.stick()
            self.show()
            gtk.gdk.threads_leave()
        if self.timer:
            self.timer.cancel()

        self.timer = Timer(self.options['timeout'], self.on_timeout)
        self.timer.start()

    def on_timeout(self):
        gtk.gdk.threads_enter()
        self.hide()
        self.label.set_text("")
        gtk.gdk.threads_leave()

    def on_change_mode(self, mode):
        self.listenkbd.stop()
        self.listenkbd = ListenKbd(self.label, logger=self.logger, 
                                   mode=mode)
        self.listenkbd.start()

    def on_show_keys(self, widget, data=None):
        if widget.get_active():
            self.logger.debug("Screenkey enabled.")
            self.listenkbd = ListenKbd(self.label, logger=self.logger, 
                                       mode=self.options['mode'])
            self.listenkbd.start()
        else:
            self.logger.debug("Screenkey disabled.")
            self.listenkbd.stop()

    def on_preferences_dialog(self, widget, data=None):
        prefs = gtk.Dialog(APP_NAME, None, 
                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                    (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        def on_sb_time_changed(widget, data=None):
            self.options['timeout'] = widget.get_value()
            self.logger.debug("Timeout value changed.")

        def on_cbox_sizes_changed(widget, data=None):
            index = widget.get_active()
            if index >= 0:
                self.options['size'] = index
                self.set_window_size(self.options['size'])
                self.logger.debug("Window size changed.")

        def on_cbox_modes_changed(widget, data=None):
            index = widget.get_active()
            if index >= 0:
                self.options['mode'] = index
                self.on_change_mode(self.options['mode'])
                self.logger.debug("Key mode changed.")

        def on_cbox_changed(widget, data=None):
            index = widget.get_active()
            name = widget.get_name()
            if index >= 0:
                self.options[name] = index
                self.logger.debug("Window position changed.")

        frm_main = gtk.Frame(_("Preferences"))
        frm_main.set_border_width(6)
        vbox_main = gtk.VBox()

        frm_time = gtk.Frame(_("<b>Time</b>"))
        frm_time.set_border_width(4)
        frm_time.get_label_widget().set_use_markup(True)
        frm_time.set_shadow_type(gtk.SHADOW_NONE)
        hbox_time = gtk.HBox()
        lbl_time1 = gtk.Label(_("Display for"))
        lbl_time2 = gtk.Label(_("seconds"))
        sb_time = gtk.SpinButton(digits=1)
        sb_time.set_increments(0.5, 1.0)
        sb_time.set_range(0.5, 10.0)
        sb_time.set_numeric(True)
        sb_time.set_update_policy(gtk.UPDATE_IF_VALID)
        sb_time.set_value(self.options['timeout'])
        sb_time.connect("value-changed", on_sb_time_changed)
        hbox_time.pack_start(lbl_time1, expand=False, 
                             fill=False, padding=6)
        hbox_time.pack_start(sb_time, expand=False, 
                             fill=False, padding=4)
        hbox_time.pack_start(lbl_time2, expand=False, 
                             fill=False, padding=4)
        frm_time.add(hbox_time)
        frm_time.show_all()

        frm_aspect = gtk.Frame(_("<b>Aspect</b>"))
        frm_aspect.set_border_width(4)
        frm_aspect.get_label_widget().set_use_markup(True)
        frm_aspect.set_shadow_type(gtk.SHADOW_NONE)
        vbox_aspect = gtk.VBox(spacing=6)

        hbox1_aspect = gtk.HBox()

        lbl_positions = gtk.Label(_("Position"))
        cbox_positions = gtk.combo_box_new_text()
        cbox_positions.set_name('position')
        for key, value in self.POSITIONS.items():
            cbox_positions.insert_text(key, value)
        cbox_positions.set_active(self.options['position'])
        cbox_positions.connect("changed", on_cbox_changed)

        hbox1_aspect.pack_start(lbl_positions, expand=False, 
                                fill=False, padding=6)
        hbox1_aspect.pack_start(cbox_positions, expand=False, 
                                fill=False, padding=4)

        hbox2_aspect = gtk.HBox()

        lbl_sizes = gtk.Label(_("Size"))
        cbox_sizes = gtk.combo_box_new_text()
        cbox_sizes.set_name('size')
        for key, value in self.SIZES.items():
            cbox_sizes.insert_text(key, value)
        cbox_sizes.set_active(self.options['size'])
        cbox_sizes.connect("changed", on_cbox_sizes_changed)

        hbox2_aspect.pack_start(lbl_sizes, expand=False, 
                                fill=False, padding=6)
        hbox2_aspect.pack_start(cbox_sizes, expand=False, 
                                fill=False, padding=4)

        vbox_aspect.pack_start(hbox1_aspect)
        vbox_aspect.pack_start(hbox2_aspect)
        frm_aspect.add(vbox_aspect)

        frm_kbd = gtk.Frame(_("<b>Keys</b>"))
        frm_kbd.set_border_width(4)
        frm_kbd.get_label_widget().set_use_markup(True)
        frm_kbd.set_shadow_type(gtk.SHADOW_NONE)
        hbox_kbd = gtk.HBox()
        lbl_kbd = gtk.Label(_("Mode"))
        cbox_modes = gtk.combo_box_new_text()
        cbox_modes.set_name('mode')
        for key, value in self.MODES.items():
            cbox_modes.insert_text(key, value)
        cbox_modes.set_active(self.options['mode'])
        cbox_modes.connect("changed", on_cbox_modes_changed)
        hbox_kbd.pack_start(lbl_kbd, expand=False, 
                            fill=False, padding=6)
        hbox_kbd.pack_start(cbox_modes, expand=False, 
                            fill=False, padding=4)
        frm_kbd.add(hbox_kbd)

        vbox_main.pack_start(frm_time, False, False, 6)
        vbox_main.pack_start(frm_aspect, False, False, 6)
        vbox_main.pack_start(frm_kbd, False, False, 6)
        frm_main.add(vbox_main)

        prefs.vbox.pack_start(frm_main)
        prefs.set_destroy_with_parent(True)
        prefs.set_resizable(False)
        prefs.set_has_separator(False)
        prefs.set_default_response(gtk.RESPONSE_CLOSE)
        prefs.vbox.show_all()
        response = prefs.run()
        if response:
            self.store_state(self.options)
        prefs.destroy()

    def on_about_dialog(self, widget, data=None):
        about = gtk.AboutDialog()
        about.set_program_name(APP_NAME)
        about.set_version(VERSION)
        about.set_copyright(u"2010 \u00a9 %s" % AUTHOR)
        about.set_comments(APP_DESC)
        about.set_documenters(
                [u"Jos\xe9 Mar\xeda Quiroga <pepelandia@gmail.com>"]
        )
        about.set_website(APP_URL)
        about.set_icon_name('preferences-desktop-keyboard-shortcuts')
        about.set_logo_icon_name(
                'preferences-desktop-keyboard-shortcuts'
        )
        about.run()
        about.destroy()

    def drop_tty(self):
        # We fork and setsid so that we drop the controlling
        # tty.
        if os.fork() != 0:
            os._exit(0)

        os.setsid()

