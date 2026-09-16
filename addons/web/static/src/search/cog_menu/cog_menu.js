import { asyncComputed, onWillStart, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ActionMenus, actionMenusProps } from "@web/search/action_menus/action_menus";

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

    // Views that fill the cog with items of their own keep those apart from
    // the print ones.
    printItemsSeparator = false;

    setup() {
        super.setup();
        this.uiService = useService("ui");
        this.registryItems = asyncComputed(async () => this._registryItems(), { initial: [] });
        onWillStart(() => this.registryItems.currentPromise());
        // Inlined in an already open menu on small screens: there is no
        // toggler left to load the print items on, so load them upfront. A
        // failure there -- offline, or a report the server will not list --
        // costs the print items, never the rest of the menu.
        onWillStart(async () => {
            if (this.uiService.isSmall) {
                try {
                    await this.loadPrintItems();
                } catch (error) {
                    // `loadPrintItems` only assigns once it has them all, so
                    // there is nothing to undo here, only a reason to give.
                    console.warn("Could not load the print items of the cog menu", error);
                }
            }
        });
    }

    get hasItems() {
        return this.cogItems.length || this.props.items.print?.length;
    }

    async _registryItems() {
        const registryItems = cogMenuRegistry.getAll();
        // An item that cannot tell whether it applies is not shown; it does
        // not get to take the menu it belongs to down with it.
        const areDisplayed = await Promise.all(
            registryItems.map(async (item) => {
                if (!("isDisplayed" in item)) {
                    return true;
                }
                try {
                    return await item.isDisplayed(this.env);
                } catch (error) {
                    console.warn(
                        `Cog item "${item.Component?.name}" could not tell whether it applies`,
                        error
                    );
                    return false;
                }
            })
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
        return [...this.registryItems(), ...this.actionItems].sort(
            (item1, item2) => (item1.groupNumber || 0) - (item2.groupNumber || 0)
        );
    }

    hasGroupIcons(groupNumber) {
        return this.cogItems.some((item) => item.groupNumber === groupNumber && item.icon);
    }

    getPrintItemAriaLabel(item) {
        return _t("Print report: %s", item.description);
    }
}
