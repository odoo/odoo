// @ts-check

/** @module @web/search/cog_menu/cog_menu - Combined cog dropdown merging Action, Print, and registry-based menu items */

import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ActionMenus } from "@web/search/action_menus/action_menus";

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
// @ts-expect-error - static props/defaultProps shapes differ from parent (OWL pattern)
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
        slots: { type: Object, optional: true },
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

    /** @returns {boolean} whether there are any cog or print items to display */
    get hasItems() {
        return this.cogItems.length || this.props.items.print?.length;
    }

    /**
     * Collect visible items from the cogMenu registry.
     * @returns {Promise<Array<{Component: typeof Component, groupNumber: number, key: string}>>}
     */
    async _registryItems() {
        const registryItems = cogMenuRegistry.getAll();
        const areDisplayed = await Promise.all(
            registryItems.map((item) =>
                "isDisplayed" in item ? item.isDisplayed(this.env) : true,
            ),
        );
        const items = [];
        for (let i = 0; i < registryItems.length; i++) {
            if (areDisplayed[i]) {
                const item = registryItems[i];
                items.push({
                    Component: item.Component,
                    groupNumber: item.groupNumber,
                    key: item.Component.name,
                });
            }
        }
        return items;
    }

    /** @returns {Array<{Component: typeof Component, groupNumber: number, key: string}>} all cog items sorted by group */
    get cogItems() {
        return [...this.registryItems, ...this.actionItems].toSorted(
            (item1, item2) => (item1.groupNumber || 0) - (item2.groupNumber || 0),
        );
    }

    /**
     * @param {{ description: string }} item
     * @returns {string}
     */
    getPrintItemAriaLabel(item) {
        return _t("Print report: %s", item.description);
    }
}
