/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { session } from '@web/session';

export class AccountSystrayItem extends Component {
    static template = "account.SystrayItem";
    static props = {};

    setup() {
        this.currentCompany = useService("company").currentCompany;
        this.isQuickEditModeEnabled = session.is_quick_edit_mode_enabled;
    }
}

export const systrayItem = {
    Component: AccountSystrayItem,
    isDisplayed : function(env) {
        const { allowedCompanies } = env.services.company;
        return Object.keys(allowedCompanies).length === 1;
    },
};

registry.category("systray").add("AccountSystrayItem", systrayItem, { sequence: 1 });
