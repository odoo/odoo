/** @odoo-module **/
/* Copyright 2023 Camptocamp - Telmo Santos
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
import {SwitchCompanyMenu} from "@web/webclient/switch_company_menu/switch_company_menu";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";

patch(SwitchCompanyMenu.prototype, "SwitchAllCompanyMenu", {
    setup() {
        this._super(...arguments);
        this.allCompanyIds = Object.values(this.companyService.availableCompanies).map(
            (x) => x.id
        );
        this.isAllCompaniesSelected = this.allCompanyIds.every((elem) =>
            this.selectedCompanies.includes(elem)
        );
    },

    toggleSelectAllCompanies() {
        if (this.isAllCompaniesSelected) {
            // Deselect all
            this.state.companiesToToggle = this.allCompanyIds;
            this.toggleCompany(this.currentCompany.id);
            this.isAllCompaniesSelected = false;
            browser.clearTimeout(this.toggleTimer);
            this.toggleTimer = browser.setTimeout(() => {
                this.companyService.setCompanies(
                    "toggle",
                    ...this.state.companiesToToggle
                );
            }, this.constructor.toggleDelay);
        } else {
            // Select all
            this.state.companiesToToggle = [this.allCompanyIds];
            this.isAllCompaniesSelected = true;
            browser.clearTimeout(this.toggleTimer);
            this.toggleTimer = browser.setTimeout(() => {
                this.companyService.setCompanies(
                    "loginto",
                    ...this.state.companiesToToggle
                );
            }, this.constructor.toggleDelay);
        }
    },
});
