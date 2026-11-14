import { Component, proxy, signal } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useCommand } from "@web/core/commands/command_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownGroup } from "@web/core/dropdown/dropdown_group";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user, userBus } from "@web/core/user";
import { useBus, useService } from "@web/core/utils/hooks";
import { CompanySelector } from "@web/webclient/switch_company_menu/company_selector";
import { SwitchCompanyItem } from "@web/webclient/switch_company_menu/switch_company_item";

function getCompany(cid) {
    return user.allowedCompaniesWithAncestors.find((c) => c.id === cid);
}

export class SwitchCompanyMenu extends Component {
    static template = "web.SwitchCompanyMenu";
    static components = { Dropdown, DropdownItem, DropdownGroup, SwitchCompanyItem, CheckBox };
    static CompanySelector = CompanySelector;

    searchInputRef = signal.ref();

    setup() {
        this.dropdown = useDropdownState();
        this.user = user;
        const actionService = useService("action");

        this.companySelector = proxy(
            new this.constructor.CompanySelector(actionService, this.dropdown)
        );

        this.state = proxy({});
        this.resetState();

        useHotkey("control+enter", () => this.confirm(), {
            bypassEditableProtection: true,
            isAvailable: () => this.companySelector.hasSelectionChanged,
        });

        useCommand(_t("Switch Company"), () => this.dropdown.open(), { hotkey: "alt+shift+u" });
        useBus(userBus, "ACTIVE_COMPANIES_CHANGED", () => {
            this.companySelector.reset();
        });

        this.containerRef = signal.ref();
        this.navigationOptions = {
            shouldFocusChildInput: false,
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
        return user.allowedCompaniesWithAncestors.length > 9;
    }

    get visibleCompanies() {
        return this.state.visibleCompanies;
    }

    get hasSelectedCompanies() {
        return this.visibleCompanies.some((c) =>
            this.companySelector.isCompanySelected(c.company.id)
        );
    }

    get isAllCompaniesSelected() {
        return (
            this.visibleCompanies.length > 0 &&
            this.visibleCompanies.every((c) => this.companySelector.isCompanySelected(c.company.id))
        );
    }

    get isIndeterminate() {
        return this.hasSelectedCompanies && !this.isAllCompaniesSelected;
    }

    get checkboxTitleLabel() {
        return this.hasSelectedCompanies ? _t("Deselect all") : _t("Select all");
    }

    computeVisibleCompanies() {
        const companies = [];

        const addCompany = (company, level = 0) => {
            if (this.matchSearch(company.name)) {
                companies.push({ company, level });
            }

            if (company.child_ids) {
                for (const companyId of company.child_ids) {
                    addCompany(getCompany(companyId), level + 1);
                }
            }
        };

        user.allowedCompaniesWithAncestors
            .filter((c) => !c.parent_id)
            .sort((c1, c2) => c1.sequence - c2.sequence)
            .forEach((c) => addCompany(c));

        return companies;
    }

    resetState() {
        this.state.searchFilter = "";
        this.state.visibleCompanies = this.computeVisibleCompanies();
    }

    onSearch(ev) {
        this.state.searchFilter = ev.target.value;
        this.state.visibleCompanies = this.computeVisibleCompanies();
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
            if (this.searchInputRef()) {
                this.searchInputRef().focus();
            }

            if (this.containerRef()) {
                // Fixes the container width so it doesn't change when searching.
                const currentWidth = this.containerRef().getBoundingClientRect().width;
                this.containerRef().style.width = currentWidth + "px";
            }
        } else {
            this.resetState();
        }
    }

    confirm() {
        this.dropdown.close();
        this.companySelector.apply();
    }

    selectAll() {
        const companyIds = this.visibleCompanies.map((entry) => entry.company.id);
        this.companySelector.selectAll(companyIds);
    }

    get isSingleCompany() {
        return user.allowedCompaniesWithAncestors.length === 1;
    }
}

export const systrayItem = {
    Component: SwitchCompanyMenu,
};

registry.category("systray").add("SwitchCompanyMenu", systrayItem, { sequence: 1 });
