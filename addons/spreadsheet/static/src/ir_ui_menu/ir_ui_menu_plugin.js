import { OdooCorePlugin } from "@spreadsheet/plugins";

export class IrMenuPlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ (["getIrMenu"]);
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
