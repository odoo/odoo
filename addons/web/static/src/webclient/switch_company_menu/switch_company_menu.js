/** @odoo-module **/

import { useService } from "../../core/service_hook";
import { registry } from "../../core/registry";
import { browser } from "../../core/browser/browser";
import { symmetricalDifference } from "../../core/utils/arrays";

const { Component, hooks } = owl;
const { useState } = hooks;

export class SwitchCompanyMenu extends Component {
    static isDisplayed(env) {
        const { availableCompanies } = env.services.company;
        return Object.keys(availableCompanies).length > 1 && !env.isSmall;
    }

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

registry.category("systray").add("SwitchCompanyMenu", SwitchCompanyMenu, { sequence: 1 });
