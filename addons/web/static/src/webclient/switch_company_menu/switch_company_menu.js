import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownGroup } from "@web/core/dropdown/dropdown_group";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";

import { Component, useChildSubEnv, useRef, useState } from "@odoo/owl";
import { useCommand } from "@web/core/commands/command_hook";
import { _t } from "@web/core/l10n/translation";
import { symmetricalDifference } from "@web/core/utils/arrays";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { SwitchCompanyItem } from "@web/webclient/switch_company_menu/switch_company_item";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class CompanySelector {
    constructor(companyService, dropdownState) {
        this.companyService = companyService;
        this.dropdownState = dropdownState;
        this.selectedCompaniesIds = companyService.activeCompanyIds.slice();
    }

    get hasSelectionChanged() {
        return (
            symmetricalDifference(this.selectedCompaniesIds, this.companyService.activeCompanyIds)
                .length > 0
        );
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
        } else if (mode === "loginto") {
            if (this._isSingleCompanyMode()) {
                this.selectedCompaniesIds.splice(0, this.selectedCompaniesIds.length);
            }
            this._selectCompany(companyId, true);
            this.apply();

            this.dropdownState.close?.();
        }
    }

    apply() {
        this.companyService.setCompanies(this.selectedCompaniesIds, false);
    }

    reset() {
        this.selectedCompaniesIds = this.companyService.activeCompanyIds.slice();
    }

    selectAll() {
        if (this.selectedCompaniesIds.length > 0) {
            this.selectedCompaniesIds.splice(0, this.selectedCompaniesIds.length);
        } else {
            const newIds = Object.values(this.companyService.allowedCompanies).map((c) => c.id);
            this.selectedCompaniesIds.splice(0, this.selectedCompaniesIds.length, ...newIds);
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
        return this.companyService.getCompany(companyId).child_ids || [];
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
        if (rootCompany && rootCompany.child_ids) {
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

export class SwitchCompanyMenu extends Component {
    static template = "web.SwitchCompanyMenu";
    static components = { Dropdown, DropdownItem, DropdownGroup, SwitchCompanyItem };
    static props = {};
    static CompanySelector = CompanySelector;

    setup() {
        this.dropdown = useDropdownState();
        this.companyService = useService("company");

        this.companySelector = useState(
            new this.constructor.CompanySelector(this.companyService, this.dropdown)
        );
        useChildSubEnv({ companySelector: this.companySelector });

        this.searchInputRef = useRef("inputRef");
        this.state = useState({});
        this.resetState();

        useHotkey("control+enter", () => this.confirm(), {
            bypassEditableProtection: true,
            isAvailable: () => this.companySelector.hasSelectionChanged,
        });

        useCommand(_t("Switch Company"), () => this.dropdown.open(), { hotkey: "alt+shift+u" });

        this.containerRef = useChildRef();
        this.navigationOptions = {
            hotkeys: {
                space: (navigator) => {
                    const navItem = navigator.activeItem;
                    if (!navItem) {
                        return;
                    }
                    if (navItem.el.classList.contains("o_switch_company_item")) {
                        const companyId = parseInt(navItem.el.dataset.companyId);
                        this.companySelector.switchCompany("toggle", companyId);
                    }
                },
                enter: (navigator) => {
                    const navItem = navigator.activeItem;
                    if (!navItem) {
                        return;
                    }
                    if (navItem.el.classList.contains("o_switch_company_item")) {
                        const companyId = parseInt(navItem.el.dataset.companyId);
                        this.companySelector.switchCompany("loginto", companyId);
                        this.dropdown.close();
                    } else {
                        navItem.select();
                    }
                },
            },
        };
    }

    get hasLotsOfCompanies() {
        return Object.values(this.companyService.allowedCompaniesWithAncestors).length > 9;
    }

    get companiesEntries() {
        const companies = [];

        const addCompany = (company, level = 0) => {
            if (this.matchSearch(company.name)) {
                companies.push({ company, level });
            }

            if (company.child_ids) {
                for (const companyId of company.child_ids) {
                    addCompany(this.companyService.getCompany(companyId), level + 1);
                }
            }
        };

        Object.values(this.companyService.allowedCompaniesWithAncestors)
            .filter((c) => !c.parent_id)
            .sort((c1, c2) => c1.sequence - c2.sequence)
            .forEach((c) => addCompany(c));

        return companies;
    }

    get selectAllClass() {
        if (
            this.companySelector.selectedCompaniesIds.length >=
            Object.values(this.companyService.allowedCompanies).length
        ) {
            return "btn-link text-primary";
        } else {
            return "btn-link text-secondary";
        }
    }

    get selectAllIcon() {
        if (
            this.companySelector.selectedCompaniesIds.length >=
            Object.values(this.companyService.allowedCompanies).length
        ) {
            return "fa-check-square text-primary";
        } else if (this.companySelector.selectedCompaniesIds.length > 0) {
            return "fa-minus-square-o";
        } else {
            return "fa-square-o";
        }
    }

    resetState() {
        this.state.searchFilter = "";
        this.state.showFilter = this.hasLotsOfCompanies;
    }

    onSearch(ev) {
        this.state.searchFilter = ev.target.value;
        this.state.showFilter = true;
    }

    matchSearch(companyName) {
        if (!this.state.searchFilter) {
            return true;
        }

        const name = companyName.toLocaleLowerCase().replace(/\s/g, "");
        const filter = this.state.searchFilter.toLocaleLowerCase().replace(/\s/g, "");
        return name.includes(filter);
    }

    handleDropdownChange(isOpen) {
        if (isOpen) {
            if (this.searchInputRef.el) {
                this.searchInputRef.el.focus();
            }

            if (this.containerRef.el) {
                // Fixes the container width so it doesn't change when searching.
                const currentWidth = this.containerRef.el.getBoundingClientRect().width;
                this.containerRef.el.style.width = currentWidth + "px";
            }
        } else {
            this.resetState();
        }
    }

    confirm() {
        this.dropdown.close();
        this.companySelector.apply();
    }

    get isSingleCompany() {
        return Object.values(this.companyService.allowedCompaniesWithAncestors ?? {}).length === 1;
    }
}

export const systrayItem = {
    Component: SwitchCompanyMenu,
};

registry.category("systray").add("SwitchCompanyMenu", systrayItem, { sequence: 1 });
