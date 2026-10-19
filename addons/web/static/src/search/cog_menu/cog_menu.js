import { computed, t, usePlugin, useScope } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { zip } from "@web/core/utils/arrays";
import { useAsyncComputed } from "@web/core/utils/hooks";
import { ActionMenus, actionMenusProps } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

export const cogMenuProps = {
    ...actionMenusProps,
    getActiveIds: t.function().optional(),
    hasSelectedRecords: t.number().optional(),
    context: t.object().optional(),
    resModel: t.string().optional(),
    slots: t.object().optional(),
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

    scope = useScope();
    uiService = usePlugin(UIPlugin);

    cogItems = computed(() =>
        this.registryItems()
            .concat(this.actionItems())
            .sort((item1, item2) => (item1.groupNumber || 0) - (item2.groupNumber || 0))
    );
    registryItems = useAsyncComputed(
        async () => (this.props.hasSelectedRecords ? [] : this.getRegistryItems()),
        { initial: [] }
    );

    get hasItems() {
        return this.cogItems().length || this.props.items.print?.length;
    }

    async getRegistryItems() {
        const registryItems = cogMenuRegistry.getAll();
        const areDisplayed = await Promise.all(
            registryItems.map(
                (item) => !("isDisplayed" in item) || this.scope.run(item.isDisplayed)
            )
        );
        const items = [];
        for (const [item, isDisplayed] of zip(registryItems, areDisplayed)) {
            if (isDisplayed) {
                items.push({
                    Component: item.Component,
                    groupNumber: item.groupNumber,
                    key: item.Component.name,
                });
            }
        }
        return items;
    }

    hasGroupIcons(groupNumber) {
        return this.cogItems().some((item) => item.groupNumber === groupNumber && item.icon);
    }

    getPrintItemAriaLabel(item) {
        return _t("Print report: %s", item.description);
    }
}
