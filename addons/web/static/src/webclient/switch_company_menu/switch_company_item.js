import { Component, t, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { CompanySelector } from "@web/webclient/switch_company_menu/company_selector";

export class SwitchCompanyItem extends Component {
    static template = "web.SwitchCompanyItem";
    static components = { DropdownItem, SwitchCompanyItem, CheckBox };
    props = useProps({
        company: t.any(),
        level: t.number(),
    });

    companySelector = useProps.static("selector", t.instanceOf(CompanySelector));

    get isCompanySelected() {
        return this.companySelector.isCompanySelected(this.props.company.id);
    }

    get isCompanyAllowed() {
        return user.allowedCompanies.map((c) => c.id).includes(this.props.company.id);
    }

    get isCurrent() {
        return this.props.company.id === user.activeCompany.id;
    }

    get checkboxTitle() {
        return this.isCompanySelected
            ? _t("Hide %s content.", this.props.company.name)
            : _t("Show %s content.", this.props.company.name);
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
