import { _contextualized_t } from "@web/core/l10n/translation";
const _t = _contextualized_t("web");
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownGroup } from "@web/core/dropdown/dropdown_group";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";

import { Component } from "@odoo/owl";
import { imageUrl } from "@web/core/utils/urls";

const userMenuRegistry = registry.category("user_menuitems");

export class UserMenu extends Component {
    static template = "web.UserMenu";
    static components = { DropdownGroup, Dropdown, DropdownItem, CheckBox };
    static props = {};

    setup() {
        this.userName = user.name;
        this.dbName = session.db;
        this.myString = _t("Disabled");
        const { partnerId, writeDate } = user;
        this.source = imageUrl("res.partner", partnerId, "avatar_128", { unique: writeDate });
    }

    getElements() {
        const sortedItems = userMenuRegistry
            .getAll()
            .map((element) => element(this.env))
            .filter((element) => (element.show ? element.show() : true))
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
