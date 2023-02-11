/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useEffect, useService } from "@web/core/utils/hooks";

const { Component } = owl;

const userMenuRegistry = registry.category("user_menuitems");

class UserMenuItem extends DropdownItem {
    setup() {
        super.setup();
        useEffect(
            () => {
                if (this.props.payload.id) {
                    this.el.dataset.menu = this.props.payload.id;
                }
            },
            () => []
        );
    }
}

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

    onDropdownItemSelected(ev) {
        ev.detail.payload.callback();
    }
}
UserMenu.template = "web.UserMenu";
UserMenu.components = { UserMenuItem };

export const systrayItem = {
    Component: UserMenu,
};
registry.category("systray").add("web.user_menu", systrayItem, { sequence: 0 });
