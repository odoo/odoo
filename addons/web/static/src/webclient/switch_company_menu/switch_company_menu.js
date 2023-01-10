/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { symmetricalDifference } from "@web/core/utils/arrays";

const { Component, hooks } = owl;
const { useState } = hooks;

export class SwitchCompanyMenu extends Component {
    setup() {
        this.companyService = useService("company");
        this.currentCompany = this.companyService.currentCompany;
        this.state = useState({ companiesToToggle: [] });
    }

    toggleCompany(companyId) {
        this.state.companiesToToggle = symmetricalDifference(this.state.companiesToToggle, [
            companyId,
        ]);
        browser.clearTimeout(this.toggleTimer);
        this.toggleTimer = browser.setTimeout(() => {
            this.companyService.setCompanies("toggle", ...this.state.companiesToToggle);
        }, this.constructor.toggleDelay);
    }

    logIntoCompany(companyId) {
        browser.clearTimeout(this.toggleTimer);
        this.companyService.setCompanies("loginto", companyId);
    }

    get selectedCompanies() {
        return symmetricalDifference(
            this.companyService.allowedCompanyIds,
            this.state.companiesToToggle
        );
    }
}
SwitchCompanyMenu.template = "web.SwitchCompanyMenu";
SwitchCompanyMenu.toggleDelay = 1000;

export const systrayItem = {
    Component: SwitchCompanyMenu,
    isDisplayed(env) {
        const { availableCompanies } = env.services.company;
        return Object.keys(availableCompanies).length > 1;
    },
};

registry.category("systray").add("SwitchCompanyMenu", systrayItem, { sequence: 1 });
