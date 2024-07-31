/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";

import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";
import { useService } from "@web/core/utils/hooks";

export class CompanySelector {
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
            if (this._isSingleCompanyMode()) {
                this.selectedCompaniesIds.splice(0, this.selectedCompaniesIds.length);
            }
            this._selectCompany(companyId, true);
            this._apply();
        }
    }

    _selectCompany(companyId, unshift = false) {
        if (!this.selectedCompaniesIds.includes(companyId)) {
            if (unshift) {
                this.selectedCompaniesIds.unshift(companyId);
            } else {
                this.selectedCompaniesIds.push(companyId);
            }
        } else if (unshift) {
            const index = this.selectedCompaniesIds.findIndex((c) => c === companyId);
            this.selectedCompaniesIds.splice(index, 1);
            this.selectedCompaniesIds.unshift(companyId);
        }
        this._getBranches(companyId).forEach((companyId) => this._selectCompany(companyId));
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

    _isSingleCompanyMode() {
        if (this.selectedCompaniesIds.length === 1) {
            return true;
        }

        const getActiveCompany = (companyId) => {
            const isActive = this.selectedCompaniesIds.includes(companyId);
            return isActive ? this.companyService.getCompany(companyId) : null;
        };

        let rootCompany = undefined;
        for (const companyId of this.selectedCompaniesIds) {
            let company = getActiveCompany(companyId);

            // Find the root active parent of the company
            while (getActiveCompany(company.parent_id)) {
                company = getActiveCompany(company.parent_id);
            }

            if (rootCompany === undefined) {
                rootCompany = company;
            } else if (rootCompany !== company) {
                return false;
            }
        }

        // If some children or sub-children of the root company
        // are not active, we are in multi-company mode.
        if (rootCompany) {
            const queue = [...rootCompany.child_ids];
            while (queue.length > 0) {
                const company = getActiveCompany(queue.pop());
                if (company && company.child_ids) {
                    queue.push(...company.child_ids);
                } else if (!company) {
                    return false;
                }
            }
        }

        return true;
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
    static CompanySelector = CompanySelector;

    setup() {
        this.companyService = useService("company");

        this.companySelector = useState(
            new this.constructor.CompanySelector(this.companyService, this.constructor.toggleDelay)
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
