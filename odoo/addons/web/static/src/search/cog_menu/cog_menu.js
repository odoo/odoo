/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { ActionMenus } from "@web/search/action_menus/action_menus";

import { onWillStart, onWillUpdateProps } from "@odoo/owl";

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
 * @extends ActionMenus
 */
export class CogMenu extends ActionMenus {
    static template = "web.CogMenu";
    static components = {
        ...ActionMenus.components,
        Dropdown,
    };
    static props = {
        ...ActionMenus.props,
        getActiveIds: { type: ActionMenus.props.getActiveIds, optional: true },
        context: { type: ActionMenus.props.context, optional: true },
        resModel: { type: ActionMenus.props.resModel, optional: true },
        items: { ...ActionMenus.props.items, optional: true },
    };
    static defaultProps = {
        ...ActionMenus.defaultProps,
        items: {},
    };

    setup() {
        super.setup();
        onWillStart(async () => {
            this.registryItems = await this._registryItems();
        });
        onWillUpdateProps(async () => {
            this.registryItems = await this._registryItems();
        });
    }

    get hasItems() {
        return this.cogItems.length || this.printItems.length;
    }

    async _registryItems() {
        const items = [];
        for (const item of cogMenuRegistry.getAll()) {
            if ("isDisplayed" in item ? await item.isDisplayed(this.env) : true) {
                items.push({
                    Component: item.Component,
                    groupNumber: item.groupNumber,
                    key: item.Component.name,
                });
            }
        }
        return items;
    }

    get cogItems() {
        return [...this.actionItems, ...this.registryItems].sort((item1, item2) => {
            const grp = (item1.groupNumber || 0) - (item2.groupNumber || 0);
            if (grp !== 0) {
                return grp;
            }
            return (item1.sequence || 0) - (item2.sequence || 0);
        });
    }
}
