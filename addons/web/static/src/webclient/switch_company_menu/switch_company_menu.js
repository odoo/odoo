// @ts-check

/** @module @web/webclient/switch_company_menu/switch_company_menu - Company switcher systray dropdown with multi-select, search, and access-rights verification */

import { Component, useChildSubEnv, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownGroup } from "@web/components/dropdown/dropdown_group";
import { useDropdownState } from "@web/components/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { router } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { symmetricalDifference } from "@web/core/utils/collections/arrays";
import { useBus, useChildRef, useService } from "@web/core/utils/hooks";
import { useCommand } from "@web/services/commands/command_hook";
import { useHotkey } from "@web/services/hotkeys/hotkey_hook";
import { user, userBus } from "@web/services/user";
import { SwitchCompanyItem } from "@web/webclient/switch_company_menu/switch_company_item";

/**
 * @param {number} cid - company ID
 * @returns {Object | undefined} the company descriptor from user.allowedCompaniesWithAncestors
 */
function getCompany(cid) {
    return user.allowedCompaniesWithAncestors.find((c) => c.id === cid);
}

/**
 * Manages the selection state for company switching.
 *
 * Tracks which companies are selected/deselected, handles single-company
 * vs. multi-company mode detection, and applies changes via the router.
 */
class CompanySelector {
    constructor(actionService, dropdownState) {
        this.actionService = actionService;
        this.dropdownState = dropdownState;
        this.selectedCompaniesIds = user.activeCompanies.map((c) => c.id);
    }

    get hasSelectionChanged() {
        return (
            symmetricalDifference(
                this.selectedCompaniesIds,
                user.activeCompanies.map((c) => c.id),
            ).length > 0
        );
    }

    isCompanySelected(companyId) {
        return this.selectedCompaniesIds.includes(companyId);
    }

    /**
     * @param {"toggle"|"loginto"} mode
     * @param {number} companyId
     */
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

    async apply() {
        user.activateCompanies(this.selectedCompaniesIds, {
            includeChildCompanies: false,
            reload: false,
        });

        const controller = this.actionService.currentController;
        const state = {};
        const options = { reload: true };
        if (controller?.props.resId && controller?.props.resModel) {
            const hasReadRights = await user.checkAccessRight(
                controller.props.resModel,
                "read",
                controller.props.resId,
            );

            if (!hasReadRights) {
                options.replace = true;
                state.actionStack = router.current.actionStack.slice(0, -1);
            }
        }

        router.pushState(state, options);
    }

    reset() {
        this.selectedCompaniesIds = user.activeCompanies.map((c) => c.id);
    }

    selectAll(companyIds) {
        let shouldSelectAll = true;

        // If any company is selected, just unselect all
        for (let i = this.selectedCompaniesIds.length - 1; i >= 0; i--) {
            if (companyIds.includes(this.selectedCompaniesIds[i])) {
                this.selectedCompaniesIds.splice(i, 1);
                shouldSelectAll = false;
            }
        }

        // If no company is selected, select all
        if (shouldSelectAll) {
            for (const companyId of companyIds) {
                if (!this.selectedCompaniesIds.includes(companyId)) {
                    this.selectedCompaniesIds.push(companyId);
                }
            }
        }
    }

    _selectCompany(companyId, unshift = false) {
        if (this._isCompanyAllowed(companyId)) {
            if (!this.selectedCompaniesIds.includes(companyId)) {
                if (unshift) {
                    this.selectedCompaniesIds.unshift(companyId);
                } else {
                    this.selectedCompaniesIds.push(companyId);
                }
            } else if (unshift) {
                const index = this.selectedCompaniesIds.findIndex(
                    (c) => c === companyId,
                );
                this.selectedCompaniesIds.splice(index, 1);
                this.selectedCompaniesIds.unshift(companyId);
            }
        }

        this._getBranches(companyId).forEach((companyId) =>
            this._selectCompany(companyId),
        );
    }

    _deselectCompany(companyId) {
        if (this.selectedCompaniesIds.includes(companyId)) {
            this.selectedCompaniesIds.splice(
                this.selectedCompaniesIds.indexOf(companyId),
                1,
            );
        }
        this._getBranches(companyId).forEach((companyId) =>
            this._deselectCompany(companyId),
        );
    }

    _getBranches(companyId) {
        return getCompany(companyId).child_ids || [];
    }

    _isCompanyAllowed(companyId) {
        return user.allowedCompanies.some((c) => c.id === companyId);
    }

    _isSingleCompanyMode() {
        if (this.selectedCompaniesIds.length === 1) {
            return true;
        }

        const getActiveCompany = (companyId) => {
            const isActive = this.selectedCompaniesIds.includes(companyId);
            return isActive ? getCompany(companyId) : null;
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

/**
 * Systray dropdown for switching between companies in a multi-company environment.
 *
 * Supports search filtering, keyboard navigation, select-all, and applies
 * company changes via the router (with access-rights verification).
 */
export class SwitchCompanyMenu extends Component {
    static template = "web.SwitchCompanyMenu";
    static components = {
        Dropdown,
        DropdownItem,
        DropdownGroup,
        SwitchCompanyItem,
    };
    static props = {};
    static CompanySelector = CompanySelector;

    setup() {
        this.dropdown = useDropdownState();
        this.user = user;
        const actionService = useService("action");

        this.companySelector = useState(
            new /** @type {any} */ (this.constructor).CompanySelector(
                actionService,
                this.dropdown,
            ),
        );
        useChildSubEnv({ companySelector: this.companySelector });

        this.searchInputRef = useRef("inputRef");
        this.state = useState(
            /** @type {{ searchFilter: string, showFilter: boolean, visibleCompanies: any[] }} */ ({}),
        );
        this.resetState();

        useHotkey("control+enter", () => this.confirm(), {
            bypassEditableProtection: true,
            isAvailable: () => this.companySelector.hasSelectionChanged,
        });

        useCommand(_t("Switch Company"), () => this.dropdown.open(), {
            hotkey: "alt+shift+u",
        });
        useBus(userBus, "ACTIVE_COMPANIES_CHANGED", () => {
            this.companySelector.reset();
        });

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
        return user.allowedCompaniesWithAncestors.length > 9;
    }

    get visibleCompanies() {
        return this.state.visibleCompanies;
    }

    get hasSelectedCompanies() {
        return this.visibleCompanies.some((c) =>
            this.companySelector.isCompanySelected(c.company.id),
        );
    }

    get selectAllClass() {
        if (
            this.visibleCompanies.every((c) =>
                this.companySelector.isCompanySelected(c.company.id),
            )
        ) {
            return "btn-link text-primary";
        } else {
            return "btn-link text-secondary";
        }
    }

    get selectAllIcon() {
        if (
            this.visibleCompanies.every((c) =>
                this.companySelector.isCompanySelected(c.company.id),
            )
        ) {
            return "fa-check-square text-primary";
        } else if (
            this.visibleCompanies.some((c) =>
                this.companySelector.isCompanySelected(c.company.id),
            )
        ) {
            return "fa-minus-square-o";
        } else {
            return "fa-square-o";
        }
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
        this.state.showFilter = this.hasLotsOfCompanies;
        this.state.visibleCompanies = this.computeVisibleCompanies();
    }

    onSearch(ev) {
        this.state.searchFilter = ev.target.value;
        this.state.showFilter = true;
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
            if (this.searchInputRef.el) {
                this.searchInputRef.el.focus();
            }

            if (/** @type {any} */ (this.containerRef).el) {
                // Fixes the container width so it doesn't change when searching.
                const currentWidth = /** @type {any} */ (
                    this.containerRef
                ).el.getBoundingClientRect().width;
                /** @type {any} */ (this.containerRef).el.style.width =
                    `${currentWidth}px`;
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
