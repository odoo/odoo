import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SwitchCompanyItem extends Component {
    static template = "web.SwitchCompanyItem";
    static components = { DropdownItem, SwitchCompanyItem };
    static props = {
        company: {},
        level: { type: Number },
    };

    setup() {
        this.companyService = useService("company");
        this.companySelector = useState(this.env.companySelector);
    }

    get isCompanySelected() {
        return this.companySelector.isCompanySelected(this.props.company.id);
    }

    get isCompanyAllowed() {
        return this.props.company.id in this.companyService.allowedCompanies;
    }

    get isCurrent() {
        return this.props.company.id === this.companyService.currentCompany.id;
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
