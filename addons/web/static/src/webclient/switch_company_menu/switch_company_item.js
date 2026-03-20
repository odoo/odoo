import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component, useState } from "@odoo/owl";
import { user } from "@web/core/user";

export class SwitchCompanyItem extends Component {
    static template = "web.SwitchCompanyItem";
    static components = { DropdownItem, SwitchCompanyItem };
    static props = {
        company: {},
        level: { type: Number },
    };

    setup() {
        this.companySelector = useState(this.env.companySelector);
    }

    get isCompanySelected() {
        return this.companySelector.isCompanySelected(this.props.company.id);
    }

    get isCompanyAllowed() {
        return user.allowedCompanies.map((c) => c.id).includes(this.props.company.id);
    }

    get isCurrent() {
        return this.props.company.id === user.activeCompany.id;
    }

    logIntoCompany() {
        if (this.isCompanyAllowed) {
            this.companySelector.switchCompany("loginto", this.props.company.id);
        }
    }

    toggleCompany() {
        if (this.isCompanyAllowed) {
            this.companySelector.switchCompany("toggle", this.props.company.id);
        }
    }
}
