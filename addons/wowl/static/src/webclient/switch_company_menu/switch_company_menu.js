/** @odoo-module **/

import { useService } from "../../core/hooks";

export class SwitchCompanyMenu extends owl.Component {
  static isDisplayed(env) {
    const allowedCompanies = env.services.user.allowed_companies;
    return Object.keys(allowedCompanies).length > 1 && !env.isSmall;
  }

  setup() {
    this.user = useService("user");
  }

  toggleCompany(companyId) {
    this.user.setCompanies("toggle", companyId);
  }

  logIntoCompany(companyId) {
    this.user.setCompanies("loginto", companyId);
  }
}
SwitchCompanyMenu.template = "wowl.SwitchCompanyMenu";
