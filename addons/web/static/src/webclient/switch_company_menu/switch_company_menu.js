/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { symmetricalDifference } from "@web/core/utils/arrays";

import { Component, useState, reactive } from "@odoo/owl";

const store = reactive({
    companiesToToggle: [],
    toggleTimer: null,
});


export class SwitchCompanyItem extends Component {
    setup() {
        this.companyService = useService("company");
        this.store = useState(store);
    }

    logIntoCompany(companyId) {
        browser.clearTimeout(this.store.toggleTimer);
        this.companyService.setCompanies("loginto", companyId);
    }

    get selectedCompanies() {
        return symmetricalDifference(
            this.companyService.allowedCompanyIds,
            this.store.companiesToToggle,
        );
    }

    toggleCompany(companyId) {
        this.store.companiesToToggle = symmetricalDifference(this.store.companiesToToggle, [
            companyId, ...this.companyService.getChildrenToToggle(companyId)
        ]);
        browser.clearTimeout(this.store.toggleTimer);
        this.store.toggleTimer = browser.setTimeout(() => {
            this.companyService.setCompanies("toggle", ...this.store.companiesToToggle);
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
        this.store.companiesToToggle = [];
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
