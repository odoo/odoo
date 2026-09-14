// @ts-check
/** @odoo-module native */

import { CogMenu } from "@web/search/cog_menu/cog_menu";

export class MultiRecordCogMenu extends CogMenu {
    static props = {
        ...CogMenu.props,
        hasSelectedRecords: { type: [Boolean, Number], optional: true },
    };

    /**
     * @override
     * @returns {any}
     */
    _registryItems() {
        return this.props.hasSelectedRecords ? [] : super._registryItems();
    }
}
