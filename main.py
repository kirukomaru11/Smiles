#!/usr/bin/python3
import gi, os, shutil, marshal
for a, b in (("Gtk", "4.0"), ("Adw", "1"), ("Gly", "2"), ("GlyGtk4", "2"), ("AppStream", "1.0")): gi.require_version(a, b)
from gi.repository import AppStream, Gio, GLib, Gtk, Adw, Gdk, Gly, GlyGtk4
from MasonryBox import MasonryBox
from PaintableColorThief import palette
from TagRow import TagRow
com = (m := AppStream.Metadata(), m.parse_file(Gio.File.new_for_path(os.path.join(GLib.get_system_data_dirs()[0], "metainfo", "io.github.kirukomaru11.Smiles.metainfo.xml")), 1), m.get_component())[-1]
Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(os.path.join(GLib.get_system_data_dirs()[0], com.props.id))
(s := Gtk.CssProvider.new(), s.load_from_path(os.path.join(GLib.get_system_data_dirs()[0], com.props.id, "style.css")), Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), s, 800))
app = Adw.Application(application_id=com.props.id)
app.register()
(app.run(), exit()) if app.props.is_remote else None
app.modifying = False
file_launcher, uri_launcher = Gtk.FileLauncher.new(), Gtk.UriLauncher.new()
Action = lambda n, s, c: (a := Gio.SimpleAction.new(n, None), app.add_action(a), app.set_accels_for_action(f"app.{n}", s), a.connect("activate", c))
shortcuts, about = Adw.ShortcutsDialog(), Adw.AboutDialog(application_icon=f"{com.props.id}-symbolic", application_name=com.props.name, developer_name=com.get_developer().get_name(), issue_url=tuple(com.props.urls.values())[0], website=tuple(com.props.urls.values())[-1], license_type=7, version=com.get_releases_plain().get_entries()[0].get_version(), release_notes=com.get_releases_plain().get_entries()[0].get_description())
Action("about", (), lambda *_: about.present(app.props.active_window))
Action("shortcuts", ("<primary>question",), lambda *_: shortcuts.present(app.props.active_window))
section = Adw.ShortcutsSection(title="General")
for t, a in (("Keyboard Shortcuts", "<primary>question"), ("Toggle Hidden", "<primary>h"), ("Search", "<primary>f"), ("Fullscreen", "F11"),("Open Current Folder", "<primary>o"), ("Paste Image/File/Folder", "<primary>v")): section.add(Adw.ShortcutsItem(title=t, accelerator=a))
shortcuts.add(section)
def Button(t="button", callback=None, icon_name="", bindings=(), **kargs):
    bt = Gtk.MenuButton if t == "menu" else Gtk.ToggleButton if t == "toggle" else Gtk.Button
    bt = bt(icon_name=icon_name + "-symbolic" if icon_name else "", **kargs)
    if callback: bt.connect("clicked" if t == "button" else "notify::active", callback)
    for b in bindings:
        source = b[0] if b[0] else bt
        source.bind_property(b[1], b[2] if b[2] else bt, b[3], b[4] if len(b) >= 5 and b[4] else 0 | 2, b[5] if len(b) >= 6 else None)
    return bt
def set_colors(file):
    if not app.props.active_window: return
    if hasattr(file, "colors") and app.lookup_action("colors").props.state:
        style = Gtk.CssProvider()
        GLib.idle_add(style.load_from_string, ":root {" + "".join(tuple(f"--color-{i + 1}: rgb{color};" for i, color in enumerate(file.colors))) + "}")
        GLib.idle_add(Gtk.StyleContext.add_provider_for_display, *(app.props.active_window.props.display, style, 700))
        GLib.idle_add(app.props.active_window.add_css_class, "colored")
    else:
        GLib.idle_add(app.props.active_window.remove_css_class, "colored")
def set_file(file):
    app.modifying = True
    app.file = file
    delete_dialog.props.heading = f"Delete {app.file.get_basename() if app.file else ''}"
    file_launcher.props.file = app.file
    edit.props.title = app.file.get_basename() if app.file else ""
    for r, i, p in properties[1:]:
        r.props.visible = r.props.name in app.data[0][app_data.get_relative_path(app.file)] if app_data.get_relative_path(app.file) in app.data[0] else False
        if r.props.visible:
            s = app.data[0][app_data.get_relative_path(app.file)][r.props.name] if r.props.name in app.data[0][app_data.get_relative_path(app.file)] else getattr(i.props, i.p, s)
            if isinstance(s, int) and isinstance(i, Gtk.Calendar):
                s = GLib.DateTime.new_from_unix_utc(s)
            setattr(i.props, i.p, s)
    path.props.text = app.file.get_basename() if app.file else ""
    GLib.idle_add(set_colors, app.file)
    app.modifying = False
def entry_video(widget):
    m = Gtk.MediaFile.new_for_file(widget.file)
    m.props.volume = 0
    m.props.loop = m.props.playing = True
    widget.props.child.props.paintable = m
def load_picture(task, widget, d, c):
    f = widget.file if Gio.content_type_guess(widget.file.get_basename())[0].startswith("image") else cache_dir.get_child(app_data.get_relative_path(widget.file).replace(GLib.DIR_SEPARATOR_S, "_") + ".webp")
    if not os.path.exists(f.peek_path()): Gio.Subprocess.new(("ffmpeg", "-v", "quiet", "-i", widget.file.peek_path(), "-vf", r"thumbnail,scale=if(gte(iw\,ih)\,min(720\,iw)\,-2):if(lt(iw\,ih)\,min(720\,ih)\,-2)", "-frames:v", "1", f.peek_path()), 0).wait()
    if Gio.content_type_guess(f.get_basename())[0].startswith("image"):
        try:
            image = Gly.Loader.new(f).load()
        except Exception as e:
            print(f"{f.get_path()} error: ", e)
            return entry_video(widget)
    else: return entry_video(widget)
    widget.height = image.get_height() / image.get_width()
    frame = image.next_frame()
    t = GlyGtk4.frame_get_texture(frame)
    widget.file.colors = palette(t)
    if frame.get_delay() > 0: return entry_video(widget)
    widget.props.child.props.paintable = t
def entry_enter(e, *_, load=False):
    entry = e.props.widget
    if not Gio.content_type_guess(entry.file.get_basename())[0].startswith("image"):
        if (isinstance(entry.props.child, Gtk.Picture) and not hasattr(entry, "video")) and (load or app.lookup_action("hover").props.state):
            entry.video = Gtk.MediaFile.new_for_file(entry.file)
            entry.event.bind_property("contains-pointer", entry.video, "volume", 0 | 2, lambda b, v: 1 if v else 0)
            entry.video.bind_property("playing", entry.video, "volume", 0 | 2, lambda b, v: 1 if v else 0)
            entry.video.s = entry.video.connect("invalidate-contents", lambda p, pi: (p.disconnect(p.s), GLib.idle_add(pi.set_paintable, p)), entry.props.child)
            entry.video.props.loop = entry.video.props.playing = True
    GLib.idle_add(set_colors, entry.file)
def do_search(*_):
    if app.modifying: return
    catalog.page, catalog.end = 0, False
    catalog.remove_all()
    for i in overlays: i.set_visible(False)
    fs = (i for i in app.all_files if app_data.get_relative_path(i) in app.data[0])
    if not fs: return overlays[0].set_visible(True)
    catalog.c, t = [], search.props.text.lower()
    for f in fs:
        o = app.data[0][app_data.get_relative_path(f)]
        if o["hidden"] and not app.lookup_action("hidden").props.state or (t and not t in f"{f.peek_path()} {o['tags']} {o['url']}".lower()): continue
        catalog.c.append(f)
    if not catalog.c: return overlays[1].set_visible(True)
    s, k = app.lookup_action("sort").props.state.get_string().strip("'"), lambda c: GLib.random_int()
    if "Alphabetical" in s:
        k = lambda e: GLib.utf8_collate_key_for_filename(e.peek_path(), -1)
    elif "Date" in s:
        k = lambda e: app.data[0][app_data.get_relative_path(e)]["date"]
    catalog.c.sort(key=k, reverse="Descending" in s)
    catalog_load_more(catalog.props.child, 3)
def catalog_load_more(sw, p):
    m = sw.props.parent
    if p == 3 and not m.end:
        m.end = True
        m.page += 1
        pages = tuple(m.c[i:i + 30] for i in range(0, len(m.c), 30))
        if not m.page > len(pages):
            for file in pages[m.page - 1]:
                if file.peek_path() in m.h:
                    entry = m.h[file.peek_path()]
                else:
                    entry = Gtk.Overlay(child=Gtk.Picture())
                    entry.props.child.props.paintable = Adw.SpinnerPaintable.new(entry.props.child)
                    entry.file = file
                    Gio.Task.new(entry).run_in_thread(load_picture)
                    entry.event = Gtk.EventControllerMotion()
                    entry.event.connect("enter", entry_enter)
                    entry.add_controller(entry.event)
                    entry.add_overlay(Gtk.Revealer(child=Button(css_classes=("osd", "circular"), tooltip_text="More", icon_name="view-more", callback=lambda b: (set_file(b.get_ancestor(Gtk.Overlay).file), edit.present(app.props.active_window))), transition_type=1, halign=2, valign=1))
                    entry.event.bind_property("contains-pointer", entry.get_last_child(), "reveal-child", 0 | 2)
                    drag_source = Gtk.DragSource(actions=Gdk.DragAction.COPY, content=Gdk.ContentProvider.new_for_value(Gdk.FileList.new_from_list((entry.file,))))
                    drag_source.connect("drag-begin", lambda e, d: Gtk.DragIcon.get_for_drag(d).set_child(Adw.Clamp(maximum_size=250, orientation=1, child=Adw.Clamp(maximum_size=250, child=Gtk.Picture(paintable=e.props.widget.props.child.props.paintable)))))
                    entry.add_controller(drag_source)
                    m.h[file.peek_path()] = entry
                GLib.idle_add(m.add, entry)
            m.end = False
def catalog_activate(m, c, b):
    if b == 3:
        entry_enter(c.event, load=True)
        if hasattr(c, "video"): c.video.seek(0)
        return
    set_file(c.file)
    if app.data[0][app_data.get_relative_path(app.file)]["url"] and app.lookup_action("launch-urls").props.state:
        uri_launcher.set_uri(app.data[0][app_data.get_relative_path(app.file)]["url"])
        uri_launcher.launch()
    else:
        file_launcher.set_file(app.file)
        if b == 1: file_launcher.launch()
        else: file_launcher.open_containing_folder()
catalog = MasonryBox(activate=catalog_activate)
catalog.h = {}
catalog.props.child.connect("edge-reached", catalog_load_more)

overlay = Gtk.Overlay(child=catalog)
for t, i in (("Add an Entry", "document-new"), ("No Results", "edit-find")): overlay.add_overlay(Adw.StatusPage(icon_name=i + "-symbolic", title=t, visible=False))
overlays = tuple(i for i in overlay if isinstance(i, Adw.StatusPage))
search = Gtk.SearchEntry(placeholder_text="Search", hexpand=True)
search.connect("stop-search", lambda *_: search_bar.set_search_mode(False))
search.connect("search-changed", do_search)
toolbar, header = Adw.ToolbarView(content=overlay), Adw.HeaderBar()
search_bar = Gtk.SearchBar(child=Adw.Clamp(maximum_size=300, child=search), key_capture_widget=toolbar)
search_bar.connect_entry(search)
Action("search", ("<primary>f",), lambda *_: search_bar.set_search_mode(not search_bar.props.search_mode_enabled))
for i in (header, search_bar): toolbar.add_top_bar(i)

menus = tuple(Gio.Menu.new() for _ in range(6))
sorts = ("Random", "Alphabetical Ascending", "Alphabetical Descending", "Date Ascending", "Date Descending")
for i in sorts: menus[4].append(i, f"app.sort::{i}")
menus[4].name = "Sort"
for n, i in enumerate(((("Fullscreen", "fullscreen"), ("Open Current Folder", "open-folder"),),
                    menus[4],
                    (("Hover to Play", "hover"), ("Show Hidden", "hidden"), ("Launch URLs", "launch-urls"), ("Entry Color Theming", "colors"), ("Clear Unused", "clear-unused")),
                    (("Keyboard Shortcuts", "shortcuts"), (f"About {about.props.application_name}", "about")),)):
    if isinstance(i, Gio.Menu):
        menus[n].append_submenu(i.name, i)
    else:
        for t, a in i: menus[n].append(t, "app." + a)
for i in menus[:4]: (i.freeze(), menus[5].append_section(None, i))
menus[5].freeze()

Action("fullscreen", ("F11",), lambda *_: toolbar.set_reveal_top_bars(not toolbar.props.reveal_top_bars))
for i in (Button(t="menu", icon_name="open-menu", tooltip_text="Menu", menu_model=menus[5]), Button(t="toggle", icon_name="edit-find", tooltip_text="Search", bindings=((None, "active", search_bar, "search-mode-enabled", 0 | 1 | 2),))): header.pack_end(i)
header.pack_start(Button(icon_name="list-add", tooltip_text="Add", callback=lambda *_: Gtk.FileDialog(filters=file_filter).open_multiple(app.props.active_window, None, lambda d, r: add(d.open_multiple_finish(r)))))

toast_overlay = Adw.ToastOverlay(child=toolbar)
controller_key, t_drop = Gtk.EventControllerKey(), Gtk.DropTarget(preload=True, actions=1, formats=Gdk.ContentFormats.parse("GdkTexture GdkFileList"))
def add(v):
    if isinstance(v, Gdk.Texture): v.save_to_png(app_data.peek_path() + GLib.DIR_SEPARATOR_S + f"{GLib.DateTime.new_now_utc().to_unix_usec()}.png")
    elif isinstance(v, Gdk.FileList) or isinstance(v, Gio.ListStore):
        for file in v:
            if file.has_prefix(app_data): continue
            f, n = app_data.get_child(file.get_basename()), 1
            while os.path.exists(f.peek_path()):
                n += 1
                f = app_data.get_child(f"{file.get_basename()} {n}")
            shutil.copytree(file.peek_path(), f.peek_path()) if os.path.isdir(file.peek_path()) else file.copy(f, 0)
def key_pressed(e, kv, kc, s):
    if kv == 118 and s == 4:
        c = app.props.active_window.props.display.get_clipboard()
        if c.props.formats.contain_gtype(Gdk.Texture):
            c.read_texture_async(None, lambda cl, r: add(cl.read_texture_finish(r)))
            return True
        elif c.props.formats.contain_gtype(Gdk.FileList):
            c.read_value_async(Gdk.FileList, 0, None, lambda cl, r: add(cl.read_value_finish(r)))
            return True
controller_key.connect("key-pressed", key_pressed)
t_drop.connect("drop", lambda d, v, *_: add(v))
for i in (controller_key, t_drop): toast_overlay.add_controller(i)
file_filter = Gio.ListStore.new(Gtk.FileFilter)
for n, t in (("All Supported Types", ("image/*", "video/*")), ("Comic Book Archive", ("application/vnd.comicbook+zip",)), ("Image", ("image/*",)), ("Video", ("video/*",))): file_filter.append(Gtk.FileFilter(name=n, mime_types=t))

delete_dialog = Adw.AlertDialog(default_response="cancel")
delete_dialog.connect("response", lambda d, r: (app.file.delete(), edit.close()) if r == "delete" else None)
for i in ("cancel", "delete"): delete_dialog.add_response(i, i.title())
delete_dialog.set_response_appearance("delete", 2)

edit, edit_page, edit_group = Adw.PreferencesDialog(follows_content_size=True), Adw.PreferencesPage(icon_name="document-edit-symbolic", title="Edit"), Adw.PreferencesGroup()
edit.bind_property("css-classes", edit, "width-request", 0, lambda b, v: 430 if "floating" in v else -1)
edit.add(edit_page)
edit.props.visible_page.add(edit_group)
path, url = Adw.EntryRow(title="Name", show_apply_button=True), Adw.EntryRow(title="URL", name="url")
tags = TagRow(name="tags")
date = Gtk.Calendar(name="date")
date.r = Adw.ActionRow(title=date.props.name.title(), name=date.props.name, css_classes=("property",), subtitle_selectable=True)
date.bind_property("date", date.r, "subtitle", 0 | 2, lambda b, v: v.to_local().format("%x"))
date.r.add_suffix(Button(t="menu", css_classes=("flat",), icon_name="month", popover=Gtk.Popover(child=date), valign=3, tooltip_text="Pick a Date"))
hidden = Adw.SwitchRow(title="Hidden", name="hidden")
def edit_changed(*_):
    if app.modifying: return
    for r, i, p in properties[1:]:
        if r.props.visible:
            if r.props.name in app.data[0][app_data.get_relative_path(app.file)]:
                v = getattr(i.props, i.p)
                app.data[0][app_data.get_relative_path(app.file)][r.props.name] = v if not isinstance(v, GLib.DateTime) else v.to_utc().to_unix()
    if path.props.text != app.file.get_basename():
        f = app.file.get_parent().get_child(path.props.text)
        if os.path.exists(f.peek_path()): return edit.add_toast(Adw.Toast(title=f"{f.get_basename()} already exists"))
        app.file.move(f, 0)
        edit.close()
properties = ((path, path, ("text", "apply")),
             (url, url, ("text", "changed")),
             (hidden, hidden, ("active", "notify::active")),
             (date.r, date, ("date", "notify::date")),
             (tags, tags, ("tags", "notify::tags")),)
for r, i, p in properties:
    i.p = p[0]
    i.connect(p[1], edit_changed)
    edit_group.add(r)
delete_button = Adw.ButtonRow(css_classes=("button", "activatable", "destructive-action"), title="Delete")
delete_button.connect("activated", lambda *_: delete_dialog.present(app.props.active_window))
edit_group.add(delete_button)
Action("open-folder", ("<primary>o",), lambda *_: (file_launcher.set_file(app_data), file_launcher.launch()))
cache_dir, app_data = tuple(Gio.File.new_for_path(os.path.join(i, about.props.application_name.lower())) for i in (GLib.get_user_cache_dir(), GLib.get_user_data_dir()))
for i in (cache_dir, app_data):
    if not os.path.exists(i.peek_path()): i.make_directory()
app.all_files, data_file = [], app_data.get_child(about.props.application_name)
app.data = marshal.loads(app_data.get_child(about.props.application_name).load_contents()[1]) if os.path.exists(data_file.peek_path()) else ({}, {})
for n, v in (("default-width", 600), ("default-height", 600), ("maximized", False), ("colors", True), ("launch-urls", True), ("clear-unused", False), ("hidden", False), ("hover", False), ("sort", sorts[0])): app.data[-1].setdefault(n, v)
for i in tuple(app.data[-1])[3:9]: app.add_action(Gio.SimpleAction.new_stateful(i, None, GLib.Variant("b", app.data[-1][i])))
app.add_action(Gio.SimpleAction.new_stateful("sort", GLib.VariantType("s"), GLib.Variant("s", app.data[-1]["sort"])))
app.set_accels_for_action("app.hidden", ["<primary>h"])
for i in ("hidden", "sort"): app.lookup_action(i).connect("notify::state", do_search)
app.connect("activate", lambda a: a.props.active_window.present() if a.props.active_window else (w := Adw.ApplicationWindow(application=a, content=toast_overlay, title=about.props.application_name, default_width=app.data[-1]["default-width"], default_height=app.data[-1]["default-height"], maximized=app.data[-1]["maximized"]), w.present())[-1])
app.connect("window-removed", lambda a, w: tuple(app.data[-1].update({i: getattr(w.props, i)}) for i in app.data[-1] if hasattr(w.props, i)))
def changed(m, f, o, e, s=False):
    if app.modifying or f.get_basename().startswith(".goutputstream") or e == 9 and (o and o.has_prefix(app_data)): return
    if f.has_prefix(app_data) and (o and o.has_prefix(app_data)):
        e = 8
    if e == 8:
        for i in tuple(i for i in app.all_files if i.equal(f) or i.has_prefix(f)):
            nf = o if i.equal(f) else o.get_child(f.get_relative_path(i))
            if not app_data.get_relative_path(i) in app.data[0]: continue
            app.data[0][app_data.get_relative_path(nf)] = app.data[0].pop(app_data.get_relative_path(i))
        if e == 8:
            changed(m, f, None, 10, True)
            changed(m, o, None, 9, True)
    if f and e in (10, 2):
        for i in tuple(i for i in app.all_files if i.equal(f) or i.has_prefix(f)):
            if hasattr(i, "m"): i.m.cancel()
            app.all_files.remove(i)
    if f and e in (9, 3):
        if not tuple(i for i in app.all_files if i.equal(f)): f_info(tuple(i for i in app.all_files if f.has_parent(i))[0], l=(f.get_basename(),))
    if e in (2, 3, 8, 9, 10) and not s and app.props.active_window: GLib.idle_add(do_search)
def f_info(d, l=False):
    if not hasattr(d, "m"):
        d.m = d.monitor(Gio.FileMonitorFlags.WATCH_MOVES)
        d.m.connect("changed", changed)
    li = l if l else os.listdir(d.peek_path())
    for i in sorted(li, key=lambda i: GLib.utf8_collate_key_for_filename(i, -1)):
        f = d.get_child(i)
        if os.path.isdir(f.peek_path()):
            f_info(f)
        app.all_files.append(f)
        if not Gio.content_type_guess(i)[0].startswith(("video", "image")):
            continue
        if not app_data.get_relative_path(f) in app.data[0]:
            app.data[0][app_data.get_relative_path(f)] = {"date": int(os.path.getmtime(f.peek_path())), "hidden": False, "url": "", "tags": []}
            toast_overlay.add_toast(Adw.Toast(timeout=2, title=f"{f.get_basename()} added"))
    app.all_files.append(d)
f_info(app_data)
do_search()
def shutdown(*_):
    if app.lookup_action("clear-unused").props.state:
        for i in tuple(i for i in app.data[0]):
            if not os.path.exists(app_data.get_child(i).peek_path()): del app.data[0][i]
        for f in os.listdir(cache_dir.peek_path()):
            if not tuple(i for i in app.all_files if f"{app_data.get_relative_path(i)}".replace(GLib.DIR_SEPARATOR_S, "_") + ".webp" == f): cache_dir.get_child(f).delete()
    for i in app.data[-1]:
        if app.lookup_action(i):
            s = app.lookup_action(i).props.state
            app.data[-1][i] = s.get_boolean() if not i == "sort" else s.get_string()
    data_file.replace_contents(marshal.dumps(app.data), None, True, 0)
app.connect("shutdown", shutdown)
app.run()
