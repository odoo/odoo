/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

const userMenuRegistry = registry.category("user_menuitems");

export class UserMenu extends Component {
    setup() {
        this.user = useService("user");
        const { origin } = browser.location;
        const { userId } = this.user;
        this.source = `${origin}/web/image?model=res.users&field=avatar_128&id=${userId}`;
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
UserMenu.template = "web.UserMenu";
UserMenu.components = { Dropdown, DropdownItem, CheckBox };

export const systrayItem = {
    Component: UserMenu,
};
registry.category("systray").add("web.user_menu", systrayItem, { sequence: 0 });
