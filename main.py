#!/usr/bin/python3
from shutil import copytree

from AppUtils import *

style = """
masonrybox revealer button { margin: 6px; }

sheet,
toastoverlay {
  transition-property: background;
  transition-duration: 250ms;
  transition-timing-function: ease;
}
.colored {
  --scrollbar-outline-color: rgb(0 0 0 / 25%);
  --accent-color: var(--color-1);
  --accent-bg-color: var(--color-1);
  --popover-bg-color: color-mix(in srgb, var(--color-2), var(--window-bg-color) 60%);
  --card-bg-color: rgb(255 255 255 / 4%);
}
.colored sheet,
.colored toastoverlay {
  background: linear-gradient(to bottom right, color-mix(in srgb, var(--color-1) 45%, transparent), transparent),
    linear-gradient(to bottom left, color-mix(in srgb, var(--color-2) 45%, transparent), transparent),
    linear-gradient( to top, color-mix(in srgb, var(--color-3) 45%, transparent), transparent),
    var(--window-bg-color);
}
"""

sorts = ("Random", "Alphabetical Ascending", "Alphabetical Descending", "Date Ascending", "Date Descending")
date_sort = lambda e: app.data["Entries"][app.data_folder.get_relative_path(e)]["Date"]

def shutdown(*_):
    if app.lookup_action("clear-unused").get_state().unpack():
        for i in tuple(i for i in app.data["Entries"]):
            if not os.path.exists(app.data_folder.get_child(i).peek_path()):
                print("Removing", i)
                del app.data["Entries"][i]
        for f in os.listdir(cache_dir.peek_path()):
            if not tuple(i for i in app.all_files if f"{app.data_folder.get_relative_path(i)}".replace(GLib.DIR_SEPARATOR_S, "_") + ".webp" == f): cache_dir.get_child(f).delete()
    data_save()
    app.thread.shutdown(wait=True, cancel_futures=True)

app = App(shortcuts={"General": (("Fullscreen", "app.fullscreen"), ("Search", "app.search"), ("Open Current Folder", "app.open"), ("Paste Image/Files/Folder", "<primary>v"), ("Toggle Hidden", "app.hidden"), ("Keyboard Shortcuts", "app.shortcuts"))},
          shutdown=shutdown,
          application_id="io.github.kirukomaru11.Smiles",
          style=style,
          data={
            "Window": { "default-height": 600, "default-width": 600, "maximized": False },
            "View": { "show-hidden": False, "hover": True, "sort": sorts[0], "colors": True },
            "General": { "launch-urls": False, "clear-unused": False },
            "Entries": {}
          })
app.all_files, app.modifying = [], False
Action("open-folder", lambda *_: launch(app.data_folder), "<primary>o")
cache_dir = Gio.File.new_for_path(os.path.join(GLib.get_user_cache_dir(), app.name.lower()))
app.finish_func = lambda p, pp: setattr(p.file, "colors", palette(pp, distance=60, black_white=100))

def set_file(file):
    app.modifying = True
    app.file = file
    delete_dialog.set_heading(f"Delete {app.file.get_basename()}")
    edit.set_title(app.file.get_basename())
    for o, p in properties:
        o.get_ancestor(Gtk.ListBoxRow).set_visible(o.get_ancestor(Gtk.ListBoxRow).get_title() in app.data["Entries"][app.data_folder.get_relative_path(app.file)] if app.data_folder.get_relative_path(app.file) in app.data["Entries"] else False)
        if o.get_ancestor(Gtk.ListBoxRow).get_visible():
            v = app.data["Entries"][app.data_folder.get_relative_path(app.file)][o.get_ancestor(Gtk.ListBoxRow).get_title()]
            o.set_property(p, GLib.DateTime.new_from_unix_utc(v).to_local() if isinstance(o, Gtk.Calendar) else v)
    GLib.idle_add(set_colors, *(file, True))
    app.modifying = False
def entry_enter(e, *_, load=False):
    entry = e.get_widget()
    if Gio.content_type_guess(entry.file.get_basename())[0].startswith("video"):
        if not hasattr(entry, "media") and (load or app.lookup_action("hover").get_state().unpack()):
            entry.media = Gtk.MediaFile.new_for_file(entry.file)
            entry.media.sig = entry.media.connect("invalidate-contents", lambda p, pic: (p.disconnect(p.sig), pic.set_paintable(p)), entry)
            entry.media.bind_property("playing", entry.media, "volume", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE, lambda b, v: 1 if v else 0)
            entry.media.set_properties(loop=True, playing=True)
            entry.event.bind_property("contains-pointer", entry.media, "volume", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE , lambda b, v: 1 if v else 0)
    GLib.idle_add(set_colors, *(entry.file, True))

def do_search(*_):
    if app.modifying: return
    catalog.page, catalog.end = 0, False
    masonrybox_remove_all(catalog)
    catalog.get_next_sibling().set_visible(False)
    fs = tuple(i for i in app.all_files if app.data_folder.get_relative_path(i) in app.data["Entries"])
    if not fs: return catalog.get_next_sibling().set_properties(title="Add an Entry", icon_name="document-new-symbolic", visible=True)
    catalog.c, t = [], search.get_text().lower()
    for f in fs:
        o = app.data["Entries"][app.data_folder.get_relative_path(f)]
        if o["Hidden"] and not app.lookup_action("show-hidden").get_state().unpack() or (t and not t in f"{f.peek_path()} {o['Tags']} {o['URL']}".lower()): continue
        catalog.c.append(f)
    if not catalog.c: return catalog.get_next_sibling().set_properties(title="No Results", icon_name="edit-find-symbolic", visible=True)
    s = app.lookup_action("sort").get_state().unpack()
    catalog.c.sort(key=alphabetical_sort if "Alphabetical" in s else date_sort if "Date" in s else random_sort, reverse="Descending" in s)
    catalog_load_more(catalog.get_child(), Gtk.PositionType.BOTTOM)
def load_thumbnail(source, result, data):
    app.thread.submit(load_media, data[0], data[1], None)
def catalog_load_more(scrolledwindow, position):
    if position == Gtk.PositionType.BOTTOM and not catalog.end:
        catalog.end = True
        catalog.page += 1
        pages = tuple(catalog.c[i:i + 30] for i in range(0, len(catalog.c), 30))
        if not catalog.page > len(pages):
            for file in pages[catalog.page - 1]:
                if file.peek_path() in catalog.h: GLib.idle_add(masonrybox_add, *(catalog, catalog.h[file.peek_path()]))
                else:
                    f = file if Gio.content_type_guess(file.get_basename())[0].startswith("image") else cache_dir.get_child(app.data_folder.get_relative_path(file).replace(GLib.DIR_SEPARATOR_S, "_") + ".webp")
                    if os.path.exists(f.peek_path()):
                        entry = Media(f.get_uri(), controls=False)
                    else:
                        entry = Gtk.Picture()
                        generate_thumbnail(file, f, load_thumbnail, (entry, f))
                    entry.file = file
                    catalog.h[file.peek_path()] = entry
                    GLib.idle_add(masonrybox_add, *(catalog, entry))
                    entry.event = Gtk.EventControllerMotion()
                    entry.event.connect("enter", entry_enter)
                    GLib.idle_add(entry.add_controller, entry.event)
                    drag_source = Gtk.DragSource(actions=Gdk.DragAction.COPY, content=Gdk.ContentProvider.new_for_value(Gdk.FileList.new_from_list((entry.file,))))
                    drag_source.connect("drag-begin", lambda e, d: Gtk.DragIcon.get_for_drag(d).set_child(Adw.Clamp(maximum_size=250, orientation=Gtk.Orientation.VERTICAL, child=Adw.Clamp(maximum_size=250, child=Gtk.Picture(css_classes=("card",), paintable=e.get_widget().get_paintable())))))
                    GLib.idle_add(entry.add_controller, drag_source)
                    event = Gtk.GestureLongPress()
                    event.connect("pressed", lambda e, *_: (set_file(e.get_widget().file), edit.present(app.window)))
                    GLib.idle_add(entry.add_controller, event)
            catalog.end = False
def catalog_activate(m, c, b):
    if b == 3:
        entry_enter(c.event, load=True)
        if hasattr(c.get_paintable(), "seek"): c.get_paintable().seek(0)
        return
    if edit.get_mapped(): return
    set_file(c.file)
    u = app.data["Entries"][app.data_folder.get_relative_path(app.file)]["URL"]
    launch(u if u and app.lookup_action("launch-urls").get_state().unpack() else c.file)
catalog = MasonryBox(activate=catalog_activate)
catalog.h = {}
catalog.get_child().connect("edge-reached", catalog_load_more)

for i in ("View", "General"):
    for it in app.data[i]:
        a = Action(it, callback=do_search if it in ("sort", "show-hidden") else None, stateful=app.data[i][it])
        a.path = i
        app.persist.append(a)

app.set_accels_for_action("app.show-hidden", ("<primary>h",))

search = Gtk.SearchEntry(placeholder_text="Search", hexpand=True)
search.connect("stop-search", lambda *_: search_bar.set_search_mode(False))
search.connect("search-changed", do_search)
toolbar, header = Adw.ToolbarView(content=Gtk.Overlay(child=catalog)), Adw.HeaderBar()
app.window.get_content().set_child(toolbar)
toolbar.get_content().add_overlay(Adw.StatusPage())
search_bar = Gtk.SearchBar(child=Adw.Clamp(maximum_size=300, child=search), key_capture_widget=toolbar)
search_bar.connect_entry(search)
Action("search", lambda *_: search_bar.set_search_mode(not search_bar.get_search_mode_enabled()), "<primary>f")
for i in (header, search_bar): toolbar.add_top_bar(i)

menu = Menu((("Fullscreen", "fullscreen"), ("Open Current Folder", "open-folder")), ("Sort", ("sort", sorts)), (("Hover to Play", "hover"), ("Show Hidden", "show-hidden"), ("Launch URLs", "launch-urls"), ("Entry Color Theming", "colors"), ("Clear Unused", "clear-unused")), app.default_menu)

Action("fullscreen", lambda *_: toolbar.set_reveal_top_bars(not toolbar.get_reveal_top_bars()), "F11")
for i in (Button(t=Gtk.MenuButton, icon_name="open-menu", tooltip_text="Menu", menu_model=menu), Button(t=Gtk.ToggleButton, icon_name="edit-find", tooltip_text="Search", bindings=((None, "active", search_bar, "search-mode-enabled", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE),))): header.pack_end(i)
header.pack_start(Button(icon_name="list-add", tooltip_text="Add", callback=lambda *_: Gtk.FileDialog(filters=file_filter).open_multiple(app.window, None, lambda d, r: add(d.open_multiple_finish(r)))))

drop = Gtk.DropTarget(preload=True, actions=Gdk.DragAction.COPY, formats=Gdk.ContentFormats.parse("GdkTexture GdkFileList"))
drop.connect("drop", lambda d, v, *_: add(v))
toolbar.add_controller(drop)
def paste(*_):
    c = app.window.get_display().get_clipboard()
    if c.get_formats().contain_gtype(Gdk.Texture):
        c.read_texture_async(None, lambda cl, r: add(cl.read_texture_finish(r)))
        return True
    elif c.get_formats().contain_gtype(Gdk.FileList):
        c.read_value_async(Gdk.FileList, 0, None, lambda cl, r: add(cl.read_value_finish(r)))
        return True
toolbar.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<primary>v"), Gtk.CallbackAction.new(paste)))
def add(v):
    if isinstance(v, Gdk.Texture): v.save_to_png(app.data_folder.peek_path() + GLib.DIR_SEPARATOR_S + f"{GLib.DateTime.new_now_utc().to_unix_usec()}.png")
    elif isinstance(v, Gdk.FileList) or isinstance(v, Gio.ListStore):
        for file in v:
            if file.has_prefix(app.data_folder): continue
            f, n = app.data_folder.get_child(file.get_basename()), 1
            while os.path.exists(f.peek_path()):
                n += 1
                f = app.data_folder.get_child(f"{file.get_basename()} {n}")
            copytree(file.peek_path(), f.peek_path()) if os.path.isdir(file.peek_path()) else file.copy(f, Gio.FileCopyFlags.NONE)

file_filter = Gio.ListStore.new(Gtk.FileFilter)
for n, t in (("All Supported Types", ("image/*", "video/*")), ("Image", ("image/*",)), ("Video", ("video/*",))): file_filter.append(Gtk.FileFilter(name=n, mime_types=t))

delete_dialog = Adw.AlertDialog(default_response="cancel")
delete_dialog.connect("response", lambda d, r: (app.file.delete(), edit.close()) if r == "confirm" else None)
for i in ("cancel", "confirm"): delete_dialog.add_response(i, i.title())
delete_dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)

edit, edit_page, edit_group = Adw.PreferencesDialog(follows_content_size=True), Adw.PreferencesPage(), Adw.PreferencesGroup()
edit.bind_property("css-classes", edit, "width-request", GObject.BindingFlags.DEFAULT, lambda b, v: 430 if "floating" in v else -1)
edit.add(edit_page)
edit.get_visible_page().add(edit_group)
path, url = Adw.EntryRow(title="Name", show_apply_button=True), Adw.EntryRow(title="URL")
edit.bind_property("title", path, "text", GObject.BindingFlags.DEFAULT)
tags = TagRow(title="Tags")
date = DateRow(title="Date")
hidden = Adw.SwitchRow(title="Hidden")
def edit_changed(*_):
    if app.modifying: return
    for o, p in properties:
        if o.get_ancestor(Gtk.ListBoxRow).get_visible():
            if o.get_ancestor(Gtk.ListBoxRow).get_title() in app.data["Entries"][app.data_folder.get_relative_path(app.file)]:
                v = o.get_property(p)
                app.data["Entries"][app.data_folder.get_relative_path(app.file)][o.get_ancestor(Gtk.ListBoxRow).get_title()] = v if not isinstance(v, GLib.DateTime) else v.to_utc().to_unix()
    if path.get_text() != app.file.get_basename():
        f = app.file.get_parent().get_child(path.get_text())
        if os.path.exists(f.peek_path()): return Toast(f"{f.get_basename()} already exists")
        app.file.move(f, Gio.FileCopyFlags.NONE)
        edit.close()
path.connect("apply", edit_changed)
edit_group.add(path)
properties = ((url, "text"),
             (date.calendar, "date"),
             (hidden, "active"),
             (tags, "tags"),)
for o, p in properties:
    o.connect(f"notify::{p}", edit_changed)
    edit_group.add(o.get_ancestor(Gtk.ListBoxRow))
delete_button = Adw.ButtonRow(css_classes=("button", "activatable", "destructive-action"), title="Delete")
delete_button.connect("activated", lambda *_: delete_dialog.present(app.window))
edit_group.add(delete_button)

def changed(m, f, o, e, s=False):
    if app.modifying or f.get_basename().startswith(".goutputstream") or e == Gio.FileMonitorEvent.MOVED_IN and (o and o.has_prefix(app.data_folder)): return
    if f.has_prefix(app.data_folder) and (o and o.has_prefix(app.data_folder)):
        e = Gio.FileMonitorEvent.RENAMED
    if e == Gio.FileMonitorEvent.RENAMED:
        for i in tuple(i for i in app.all_files if i.equal(f) or i.has_prefix(f)):
            nf = o if i.equal(f) else o.get_child(f.get_relative_path(i))
            if not app.data_folder.get_relative_path(i) in app.data["Entries"]: continue
            app.data["Entries"][app.data_folder.get_relative_path(nf)] = app.data["Entries"].pop(app.data_folder.get_relative_path(i))
        if e == Gio.FileMonitorEvent.RENAMED:
            changed(m, f, None, Gio.FileMonitorEvent.MOVED_OUT, True)
            changed(m, o, None, Gio.FileMonitorEvent.MOVED_IN, True)
    if f and e in (Gio.FileMonitorEvent.MOVED_OUT, Gio.FileMonitorEvent.DELETED):
        for i in tuple(i for i in app.all_files if i.equal(f) or i.has_prefix(f)):
            if hasattr(i, "m"): i.m.cancel()
            app.all_files.remove(i)
    if f and e in (Gio.FileMonitorEvent.MOVED_IN, Gio.FileMonitorEvent.CREATED):
        if not tuple(i for i in app.all_files if i.equal(f)): f_info(tuple(i for i in app.all_files if f.has_parent(i))[0])
    if not s and app.get_active_window(): GLib.idle_add(do_search)
def f_info(d):
    if not hasattr(d, "m"):
        d.m = d.monitor(Gio.FileMonitorFlags.WATCH_MOVES)
        d.m.connect("changed", changed)
    for i in sorted(os.listdir(d.peek_path()), key=alphabetical_sort):
        f = d.get_child(i)
        if os.path.isdir(f.peek_path()): f_info(f)
        if not tuple(it for it in app.all_files if it.equal(f)): app.all_files.append(f)
        if not Gio.content_type_guess(i)[0].startswith(("video", "image")):  continue
        if not app.data_folder.get_relative_path(f) in app.data["Entries"]: Toast(f"{f.get_basename()} added", timeout=2)
        app.data["Entries"].setdefault(app.data_folder.get_relative_path(f), {})
        for k, v in {"Date": int(os.path.getmtime(f.peek_path())), "Hidden": False, "URL": "", "Tags": []}.items(): app.data["Entries"][app.data_folder.get_relative_path(f)].setdefault(k, v)
    if not tuple(it for it in app.all_files if it.equal(d)): app.all_files.append(d)
f_info(app.data_folder)
GLib.idle_add(do_search)
app.run()
