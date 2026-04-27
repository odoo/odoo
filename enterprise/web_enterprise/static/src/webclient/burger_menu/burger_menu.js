/** @odoo-module **/
import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class EnterpriseBurgerMenu extends BurgerMenu {
    setup() {
        super.setup();
        this.hm = useService("home_menu");
    }

    get currentApp() {
        return !this.hm.hasHomeMenu && super.currentApp;
    }
}

const systrayItem = {
    Component: EnterpriseBurgerMenu,
};

registry.category("systray").add("burger_menu", systrayItem, { sequence: 0, force: true });
