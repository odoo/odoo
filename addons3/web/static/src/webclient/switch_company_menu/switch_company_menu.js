/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";

import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";
import { useService } from "@web/core/utils/hooks";

class CompanySelector {
    constructor(companyService, toggleDelay) {
        this.companyService = companyService;
        this.selectedCompaniesIds = companyService.activeCompanyIds.slice();

        this._debouncedApply = debounce(() => this._apply(), toggleDelay);
    }

    isCompanySelected(companyId) {
        return this.selectedCompaniesIds.includes(companyId);
    }

    switchCompany(mode, companyId) {
        if (mode === "toggle") {
            if (this.selectedCompaniesIds.includes(companyId)) {
                this._deselectCompany(companyId);
            } else {
                this._selectCompany(companyId);
            }
            this._debouncedApply();
        } else if (mode === "loginto") {
            this.selectedCompaniesIds.splice(0, this.selectedCompaniesIds.length);
            this._selectCompany(companyId);
            this._apply();
        }
    }

    _selectCompany(companyId) {
        if (!this.selectedCompaniesIds.includes(companyId)) {
            this.selectedCompaniesIds.push(companyId);
            this._getBranches(companyId).forEach((companyId) => this._selectCompany(companyId));
        }
    }

    _deselectCompany(companyId) {
        if (this.selectedCompaniesIds.includes(companyId)) {
            this.selectedCompaniesIds.splice(this.selectedCompaniesIds.indexOf(companyId), 1);
            this._getBranches(companyId).forEach((companyId) => this._deselectCompany(companyId));
        }
    }

    _getBranches(companyId) {
        return this.companyService.getCompany(companyId).child_ids;
    }

    _apply() {
        this.companyService.setCompanies(this.selectedCompaniesIds, false);
    }
}

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

export class SwitchCompanyMenu extends Component {
    static template = "web.SwitchCompanyMenu";
    static components = { Dropdown, DropdownItem, SwitchCompanyItem };
    static props = {};
    static toggleDelay = 1000;

    setup() {
        this.companyService = useService("company");

        this.companySelector = useState(
            new CompanySelector(this.companyService, this.constructor.toggleDelay)
        );
        useChildSubEnv({ companySelector: this.companySelector });
    }
}

export const systrayItem = {
    Component: SwitchCompanyMenu,
    isDisplayed(env) {
        const { allowedCompanies } = env.services.company;
        return Object.keys(allowedCompanies).length > 1;
    },
};

registry.category("systray").add("SwitchCompanyMenu", systrayItem, { sequence: 1 });
