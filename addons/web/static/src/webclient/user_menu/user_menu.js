/** @odoo-module **/

import { browser } from "../../core/browser/browser";
import { DropdownItem } from "../../core/dropdown/dropdown_item";
import { useService } from "../../core/service_hook";
import { registry } from "../../core/registry";

const { Component, hooks } = owl;

const userMenuRegistry = registry.category("user_menuitems");

class UserMenuItem extends DropdownItem {
    setup() {
        super.setup();
        hooks.onMounted(() => {
            if (this.props.payload.id) {
                this.el.dataset.menu = this.props.payload.id;
            }
        });
    }
}

export class UserMenu extends Component {
    static isDisplayed(env) {
        return !env.isSmall;
    }

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

    onClickOnTagA(ev) {
        if (!ev.ctrlKey) {
            ev.preventDefault();
        }
    }
}
UserMenu.template = "web.UserMenu";
UserMenu.components = { UserMenuItem };

registry.category("systray").add("web.user_menu", UserMenu, { sequence: 0 });
