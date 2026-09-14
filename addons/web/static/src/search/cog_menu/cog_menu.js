// @ts-check
/** @odoo-module native */

import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import {
    COG_GROUP,
    COG_MENU_REGISTRY_VALIDATION,
} from "@web/search/cog_menu/cog_menu_group";
import { getDisplayedRegistryItems } from "@web/search/utils/misc";

const cogMenuRegistry = registry.category("cogMenu");

cogMenuRegistry.addValidation(COG_MENU_REGISTRY_VALIDATION);

const PRINT_ITEM = Object.freeze({
    key: "print",
    groupNumber: COG_GROUP.PRINT,
    isPrint: true,
});

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

    /** @type {any[]} */
    registryItems;

    setup() {
        super.setup();
        onWillStart(async () => {
            this.registryItems = await this._registryItems();
        });
        onWillUpdateProps(async () => {
            this.registryItems = await this._registryItems();
        });
    }

    /** @returns {boolean} */
    get hasItems() {
        return Boolean(this.cogItems.length || this.props.slots?.default);
    }

    /** @returns {Promise<Array<{Component: import("@odoo/owl").ComponentConstructor, groupNumber: number, key: string}>>} */
    _registryItems() {
        return getDisplayedRegistryItems(
            cogMenuRegistry,
            /** @type {import("@web/env").OdooEnv} */ (this.env),
        );
    }

    /**
     * @returns {Array<
     * | {Component: import("@odoo/owl").ComponentConstructor, groupNumber: number, key: string}
     * | {key: string, groupNumber: number, description?: string, action?: any, callback?: Function}
     * | {key: string, groupNumber: number, isPrint: true}
     * >}
     */
    get cogItems() {
        return [
            ...this.registryItems,
            ...(this.actionItems ?? []),
            ...(this.props.items.print?.length ? [PRINT_ITEM] : []),
        ].toSorted(
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
