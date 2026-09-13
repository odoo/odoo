// @ts-check
/** @odoo-module native */

import { Component } from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox/checkbox";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownGroup } from "@web/components/dropdown/dropdown_group";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { imageUrl } from "@web/core/utils/urls";
import { session } from "@web/session";

const log = makeLogger("web.user_menu");
const userMenuRegistry = registry.category("user_menuitems");

userMenuRegistry.addValidation((entry) => typeof entry === "function");

export class UserMenu extends Component {
    static template = "web.UserMenu";
    static components = { DropdownGroup, Dropdown, DropdownItem, CheckBox };
    static props = {};

    setup() {
        this.userName = user.name;
        this.dbName = session.db;
    }

    get source() {
        const { partnerId, writeDate } = user;
        if (!partnerId) {
            return "";
        }
        return imageUrl("res.partner", partnerId, "avatar_128", {
            unique: writeDate,
        });
    }

    /** @returns {Object[]} */
    getElements() {
        const sortedItems = userMenuRegistry
            .getEntries()
            .flatMap(([key, element]) => {
                try {
                    return [
                        {
                            ...element(
                                /** @type {import("@web/env").OdooEnv} */ (this.env),
                            ),
                            key,
                        },
                    ];
                } catch (error) {
                    log.logic("provider failed", { key, error });
                    console.warn(`User menu provider ${key} failed`, error);
                    return [];
                }
            })
            .filter((element) => !element.hide)
            .sort((x, y) => (x.sequence ?? 100) - (y.sequence ?? 100));
        return sortedItems;
    }
}

export const systrayItem = {
    Component: UserMenu,
};
registry.category("systray").add("web.user_menu", systrayItem, { sequence: 0 });
