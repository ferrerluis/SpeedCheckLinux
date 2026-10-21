// SPDX-License-Identifier: MIT
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class SpeedCheckPanel extends Extension {
    enable() {
        this._icons = new Map();
        this._idle = 0;
        this._clock = Main.panel.statusArea.dateMenu.container;
        this._originalParent = this._clock.get_parent();
        this._originalIndex = this._originalParent.get_children().indexOf(this._clock);
        this._movedClock = this._originalParent !== Main.panel._leftBox;
        if (this._movedClock) {
            this._originalParent.remove_child(this._clock);
            Main.panel._leftBox.insert_child_at_index(this._clock, 1);
        }
        // With no centered clock, use the remaining width for the right side.
        // GNOME's default half-width cap would still ellipsize the speed text.
        this._injections = new InjectionManager();
        this._injections.overrideMethod(Object.getPrototypeOf(Main.panel), 'vfunc_allocate',
            original => function (box) {
                original.call(this, box);
                if (this !== Main.panel || this._centerBox.get_n_children() !== 0)
                    return;
                const width = box.x2 - box.x1;
                const [, leftWidth] = this._leftBox.get_preferred_width(-1);
                const [, naturalWidth] = this._rightBox.get_preferred_width(-1);
                const rightWidth = Math.min(naturalWidth, Math.max(0, width - leftWidth - 8));
                const rtl = this.get_text_direction() === Clutter.TextDirection.RTL;
                const allocation = new Clutter.ActorBox();
                allocation.x1 = rtl ? 0 : width - rightWidth;
                allocation.x2 = allocation.x1 + rightWidth;
                allocation.y1 = 0;
                allocation.y2 = box.y2 - box.y1;
                this._rightBox.allocate(allocation);
            });
        this._signals = [Main.panel._leftBox, Main.panel._centerBox, Main.panel._rightBox]
            .map(box => [box, box.connect('child-added', () => this._queueUpdate())]);
        this._hideSpeedCheckIcon();
        Main.panel.queue_relayout();
    }

    _queueUpdate() {
        if (this._idle)
            return;
        this._idle = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._idle = 0;
            this._hideSpeedCheckIcon();
            return GLib.SOURCE_REMOVE;
        });
    }

    _hideSpeedCheckIcon() {
        for (const item of Object.values(Main.panel.statusArea)) {
            if (item._indicator?.id !== 'speedcheck-linux' || !item._icon)
                continue;
            const icon = item._icon;
            if (this._icons.has(icon))
                continue;
            const saved = {visible: icon.visible};
            this._icons.set(icon, saved);
            saved.destroyId = icon.connect('destroy', () => this._icons.delete(icon));
            saved.visibleId = icon.connect('notify::visible', () => {
                if (icon.visible)
                    icon.hide();
            });
            icon.hide();
        }
    }

    disable() {
        if (this._idle)
            GLib.Source.remove(this._idle);
        this._idle = 0;
        for (const [box, id] of this._signals)
            box.disconnect(id);
        this._injections.clear();
        for (const [icon, saved] of this._icons) {
            icon.disconnect(saved.destroyId);
            icon.disconnect(saved.visibleId);
            icon.visible = saved.visible;
        }
        this._icons.clear();
        if (this._movedClock && this._clock.get_parent() === Main.panel._leftBox) {
            Main.panel._leftBox.remove_child(this._clock);
            this._originalParent.insert_child_at_index(this._clock, this._originalIndex);
        }
        this._clock = null;
        this._originalParent = null;
        Main.panel.queue_relayout();
    }
}
