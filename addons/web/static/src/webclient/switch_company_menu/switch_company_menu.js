/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

import { Component, useState, reactive } from "@odoo/owl";

const store = reactive({
    toggleTimer: null,
    nextAvailableCompanies: [],
});


export class SwitchCompanyItem extends Component {
    setup() {
        this.companyService = useService("company");
        this.store = useState(store);
    }

    get selectedCompanies() {
        this.store.nextAvailableCompanies;  // check if the state changed
        return this.companyService.nextAvailableCompanies;
    }

    logIntoCompany(companyId) {
        this.companyService.setCompanies("loginto", companyId);
        browser.clearTimeout(this.store.toggleTimer);
        this.companyService.logNextCompanies();
    }

    toggleCompany(companyId) {
        this.companyService.setCompanies("toggle", companyId);
        // trigger state change
        this.store.nextAvailableCompanies = this.companyService.nextAvailableCompanies.slice();

        browser.clearTimeout(this.store.toggleTimer);
        this.store.toggleTimer = browser.setTimeout(() => {
            this.companyService.logNextCompanies();
        }, this.constructor.toggleDelay);
    }
}
SwitchCompanyItem.template = 'web.SwitchCompanyItem';
SwitchCompanyItem.components = { DropdownItem, SwitchCompanyItem };
SwitchCompanyItem.props = {
    company: {},
    level: {type: Number},
};
SwitchCompanyItem.toggleDelay = 1000;


export class SwitchCompanyMenu extends Component {
    setup() {
        this.companyService = useService("company");
        this.store = useState(store);
        this.store.nextAvailableCompanies = [];
    }
}
SwitchCompanyMenu.template = "web.SwitchCompanyMenu";
SwitchCompanyMenu.components = { Dropdown, DropdownItem, SwitchCompanyItem };
SwitchCompanyMenu.props = {};

export const systrayItem = {
    Component: SwitchCompanyMenu,
    isDisplayed(env) {
        const { availableCompanies } = env.services.company;
        return Object.keys(availableCompanies).length > 1;
    },
};

registry.category("systray").add("SwitchCompanyMenu", systrayItem, { sequence: 1 });
