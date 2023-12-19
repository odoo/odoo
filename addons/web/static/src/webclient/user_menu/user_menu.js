/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";

import { Component } from "@odoo/owl";

const userMenuRegistry = registry.category("user_menuitems");

export class UserMenu extends Component {
    static template = "web.UserMenu";
    static components = { Dropdown, DropdownItem, CheckBox };
    static props = {};

    setup() {
        const { origin } = browser.location;
        this.source = `${origin}/web/image?model=res.users&field=avatar_128&id=${user.userId}`;
        this.userName = user.name;
        this.dbName = session.db;
    }

    getElements() {
        const sortedItems = userMenuRegistry
            .getAll()
            .map((element) => element(this.env))
            .sort((x, y) => {
                const xSeq = x.sequence ? x.sequence : 100;
                const ySeq = y.sequence ? y.sequence : 100;
                return xSeq - ySeq;
            });
        return sortedItems;
    }
}

export const systrayItem = {
    Component: UserMenu,
};
registry.category("systray").add("web.user_menu", systrayItem, { sequence: 0 });
