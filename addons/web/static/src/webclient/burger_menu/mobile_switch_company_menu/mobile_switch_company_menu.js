// @ts-check

/** @module @web/webclient/burger_menu/mobile_switch_company_menu/mobile_switch_company_menu - Mobile company switcher with collapsible toggle for many companies */

import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";

/** Mobile variant of the company switcher with a collapsible toggle. */
export class MobileSwitchCompanyMenu extends SwitchCompanyMenu {
    static template = "web.MobileSwitchCompanyMenu";

    setup() {
        super.setup();
        /** @type {any} */ (this.state).isOpen = false;
    }

    /** @returns {boolean} whether the company list should be visible */
    get show() {
        return (
            !this.hasLotsOfCompanies || /** @type {any} */ (this.state).isOpen === true
        );
    }

    /** Toggle the company list visibility when many companies exist. */
    toggleCollapsible() {
        if (this.hasLotsOfCompanies) {
            /** @type {any} */ (this.state).isOpen = !(
                /** @type {any} */ (this.state).isOpen
            );
        }
    }
}
