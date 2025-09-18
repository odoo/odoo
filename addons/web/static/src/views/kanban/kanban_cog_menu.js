// @ts-check

/** @module @web/views/kanban/kanban_cog_menu - Kanban cog menu that hides registry items during multi-select operations */

/**
 * Kanban-specific cog menu that hides registry items when records are selected.
 *
 * Extends the standard CogMenu to suppress action menu entries during
 * multi-select operations, keeping only the selection-specific actions visible.
 */
import { CogMenu } from "@web/search/cog_menu/cog_menu";
export class KanbanCogMenu extends CogMenu {
    static template = "web.KanbanCogMenu";
    static props = {
        ...CogMenu.props,
        hasSelectedRecords: { type: Number, optional: true },
    };
    _registryItems() {
        return /** @type {any} */ (
            this.props.hasSelectedRecords ? [] : super._registryItems()
        );
    }
}
