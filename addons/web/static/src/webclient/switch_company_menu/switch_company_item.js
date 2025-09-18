// @ts-check

/** @module @web/webclient/switch_company_menu/switch_company_item - Single company row in the switch-company dropdown with toggle and log-into actions */

import { Component, useState } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { user } from "@web/services/user";

/** Single company row in the switch-company dropdown (checkbox + log-into). */
export class SwitchCompanyItem extends Component {
    static template = "web.SwitchCompanyItem";
    static components = { DropdownItem, SwitchCompanyItem };
    static props = {
        company: {},
        level: { type: Number },
    };

    /** Initialize reactive company selector state from env. */
    setup() {
        this.companySelector = useState(this.env.companySelector);
    }

    /** @returns {boolean} Whether this company is currently selected (checked). */
    get isCompanySelected() {
        return this.companySelector.isCompanySelected(this.props.company.id);
    }

    /** @returns {boolean} Whether the user is allowed to access this company. */
    get isCompanyAllowed() {
        return user.allowedCompanies.map((c) => c.id).includes(this.props.company.id);
    }

    /** @returns {boolean} Whether this company is the currently active one. */
    get isCurrent() {
        return this.props.company.id === user.activeCompany.id;
    }

    /** Switch to this company as the sole active company. */
    logIntoCompany() {
        if (this.isCompanyAllowed) {
            this.companySelector.switchCompany("loginto", this.props.company.id);
        }
    }

    /** Toggle this company in/out of the multi-company selection. */
    toggleCompany() {
        if (this.isCompanyAllowed) {
            this.companySelector.switchCompany("toggle", this.props.company.id);
        }
    }
}
