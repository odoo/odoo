/** @odoo-module  **/

import { ComponentAdapter } from "web.OwlCompatibility";
import * as legacySystrayMenu from "web.SystrayMenu";
import { registry } from "../core/registry";

const { Component, tags } = owl;
const systrayRegistry = registry.category("systray");

class SystrayItemAdapter extends ComponentAdapter {
    constructor() {
        super(...arguments);
        this.env = Component.env;
    }
}

// registers the legacy systray menu items from the legacy systray registry
// to the wowl one, but wrapped into Owl components
const legacySystrayMenuItems = legacySystrayMenu.Items;
const convertedItems = [];
let id = 1;

const legacySystrayItemTemplate = tags.xml`<SystrayItemAdapter Component="Widget" />`;

function addSystrayItem(Widget) {
    const name = `_legacy_systray_item_${id++}`;

    class SystrayItem extends Component {
        constructor() {
            super(...arguments);
            this.Widget = Widget;
        }
    }
    SystrayItem.template = legacySystrayItemTemplate;
    SystrayItem.components = { SystrayItemAdapter };

    systrayRegistry.add(name, { Component: SystrayItem }, { sequence: Widget.prototype.sequence });

    convertedItems.push(Widget);
}

legacySystrayMenuItems.forEach(addSystrayItem);
const push = legacySystrayMenuItems.push.bind(legacySystrayMenuItems);
legacySystrayMenuItems.push = function (Widget) {
    push(Widget);
    addSystrayItem(Widget);
};
const splice = legacySystrayMenuItems.splice.bind(legacySystrayMenuItems);
legacySystrayMenuItems.splice = function () {
    splice(...arguments);
    legacySystrayMenuItems.forEach((Widget) => {
        if (!convertedItems.includes(Widget)) {
            addSystrayItem(Widget);
        }
    });
};
