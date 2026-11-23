/** @odoo-module */
import * as spreadsheet from "@odoo/o-spreadsheet";
const { CorePlugin } = spreadsheet;

export class IrMenuPlugin extends CorePlugin {
    constructor(config) {
        super(config);
        this.env = config.custom.env;
    }

    /**
     * Get an ir menu from an id or an xml id
     * @param {number | string} menuId
     * @returns {object | undefined}
     */
    getIrMenu(menuId) {
        let menu = this.env.services.menu.getMenu(menuId);
        if (!menu) {
            menu = this.env.services.menu.getAll().find((menu) => menu.xmlid === menuId);
        }
        return menu;
    }
}
IrMenuPlugin.getters = ["getIrMenu"];
