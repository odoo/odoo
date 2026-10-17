import { router } from "@web/core/browser/router";
import { user } from "@web/core/user";
import { symmetricalDifference } from "@web/core/utils/arrays";

function getCompany(cid) {
    return user.allowedCompaniesWithAncestors.find((c) => c.id === cid);
}

export class CompanySelector {
    constructor(actionService, dropdownState) {
        this.actionService = actionService;
        this.dropdownState = dropdownState;
        this.selectedCompaniesIds = user.activeCompanies.map((c) => c.id);
    }

    get hasSelectionChanged() {
        return (
            symmetricalDifference(
                this.selectedCompaniesIds,
                user.activeCompanies.map((c) => c.id)
            ).length > 0
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
                controller.props.resId
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
                const index = this.selectedCompaniesIds.findIndex((c) => c === companyId);
                this.selectedCompaniesIds.splice(index, 1);
                this.selectedCompaniesIds.unshift(companyId);
            }
        }

        this._getBranches(companyId).forEach((companyId) => this._selectCompany(companyId));
    }

    _deselectCompany(companyId) {
        if (this.selectedCompaniesIds.includes(companyId)) {
            this.selectedCompaniesIds.splice(this.selectedCompaniesIds.indexOf(companyId), 1);
        }
        this._getBranches(companyId).forEach((companyId) => this._deselectCompany(companyId));
    }

    _getBranches(companyId) {
        return getCompany(companyId).child_ids || [];
    }

    _isCompanyAllowed(companyId) {
        return user.allowedCompanies.some((c) => c.id == companyId);
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
