// @ts-check

/** @module @web/views/list/list_cog_menu - List-view cog menu that hides registry items when records are selected */

/**
 * List-view variant of CogMenu that hides registry items when records are selected.
 *
 * When one or more records are selected, the cog menu only shows the action
 * menus (print, action) and suppresses the registry-sourced items (e.g. export).
 */
import { CogMenu } from "@web/search/cog_menu/cog_menu";
export class ListCogMenu extends CogMenu {
    static template = "web.ListCogMenu";
    static props = {
        ...CogMenu.props,
        hasSelectedRecords: { type: Number, optional: true },
    };
    /** @override @returns {any} */
    _registryItems() {
        return this.props.hasSelectedRecords ? [] : super._registryItems();
    }
}
