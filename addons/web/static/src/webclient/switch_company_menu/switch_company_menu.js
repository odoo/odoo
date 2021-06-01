/** @odoo-module **/

import { useService } from "../../core/service_hook";
import { registry } from "../../core/registry";

export class SwitchCompanyMenu extends owl.Component {
    static isDisplayed(env) {
        const { availableCompanies } = env.services.company;
        return Object.keys(availableCompanies).length > 1 && !env.isSmall;
    }

    setup() {
        this.companyService = useService("company");
        this.currentCompany = this.companyService.currentCompany;
    }

    toggleCompany(companyId) {
        this.companyService.setCompanies("toggle", companyId);
    }

    logIntoCompany(companyId) {
        this.companyService.setCompanies("loginto", companyId);
    }
}
SwitchCompanyMenu.template = "web.SwitchCompanyMenu";

registry.category("systray").add("SwitchCompanyMenu", SwitchCompanyMenu, { sequence: 1 });
