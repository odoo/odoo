import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { ActionMenus, actionMenusProps } from "@web/search/action_menus/action_menus";
import { _t } from "@web/core/l10n/translation";
import { onWillStart, onWillUpdateProps, t } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

export const cogMenuProps = {
    ...actionMenusProps,
    getActiveIds: t.function().optional(),
    context: t.object().optional(),
    resModel: t.string().optional(),
    items: t
        .object({
            action: t.array().optional(),
            print: t.array().optional(),
        })
        .optional({}),
    slots: t.object().optional(),
};

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
    static actionMenusProps = cogMenuProps;

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
        return this.cogItems.length || this.props.items.print?.length;
    }

    async _registryItems() {
        const registryItems = cogMenuRegistry.getAll();
        const areDisplayed = await Promise.all(
            registryItems.map((item) => ("isDisplayed" in item ? item.isDisplayed(this.env) : true))
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

    get cogItems() {
        return [...this.registryItems, ...this.actionItems].sort(
            (item1, item2) => (item1.groupNumber || 0) - (item2.groupNumber || 0)
        );
    }

    get groupsWithIcons() {
        const groups = new Set();
        for (const item of this.cogItems) {
            if (Object.prototype.hasOwnProperty.call(item, "icon")) {
                groups.add(item.groupNumber);
            }
        }
        return groups;
    }

    getPrintItemAriaLabel(item) {
        return _t("Print report: %s", item.description);
    }
}
