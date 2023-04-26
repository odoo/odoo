/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";

import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * Combined Action menus (or Action/Print bar, previously called 'Sidebar')
 *
 * This is a variation of the ActionMenus, combined into a single DropDown.
 *
 * The side bar is the group of dropdown menus located on the left side of the
 * control panel. Its role is to display a list of items depending on the view
 * type and selected records and to execute a set of actions on active records.
 * It is made out of 2 dropdown: Print and Action.
 *
 * @extends Component
 */
export class CogMenu extends Component {
    static template = "web.CogMenu";
    static components = {
        Dropdown,
    };
    static props = {
        slots: { type: Object, optional: true },
    };

    get hasItems() {
        return this.cogItems.length || !!this.props.slots?.default;
    }

    get cogItems() {
        const registryMenus = [];
        for (const item of cogMenuRegistry.getAll()) {
            if ("isDisplayed" in item ? item.isDisplayed(this.env) : true) {
                registryMenus.push({
                    Component: item.Component,
                    groupNumber: item.groupNumber,
                    key: item.Component.name,
                });
            }
        }
        return registryMenus;
    }
}
