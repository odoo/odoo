odoo.define("web.SwitchCompanyMenu", function (require) {
    "use strict";

    /**
     * When Odoo is configured in multi-company mode, users should obviously be able
     * to switch their interface from one company to the other.  This is the purpose
     * of this widget, by displaying a dropdown menu in the systray.
     */

    const config = require("web.config");
    const session = require("web.session");
    const SystrayMenu = require("web.SystrayMenu");

    class SwitchCompanyMenu extends owl.Component {
        /**
         * @override
         */
        constructor() {
            super(...arguments);
            this.isMobile = config.device.isMobile;
            this._onSwitchCompanyClick = _.debounce(this._onSwitchCompanyClick, 1500, true);
        }

        /**
         * @override
         */
        willStart() {
            const self = this;
            this.allowed_company_ids = String(session.user_context.allowed_company_ids)
                .split(",")
                .map(function (id) {
                    return parseInt(id);
                });
            this.user_companies = session.user_companies.allowed_companies;
            this.current_company = this.allowed_company_ids[0];
            this.current_company_name = _.find(session.user_companies.allowed_companies, function (
                company
            ) {
                return company[0] === self.current_company;
            })[1];
            return super.willStart(...arguments);
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent|KeyEvent} ev
         */
        _onSwitchCompanyClick(ev) {
            if (
                ev.type === "keydown" &&
                ev.which !== $.ui.keyCode.ENTER &&
                ev.which !== $.ui.keyCode.SPACE
            ) {
                return;
            }
            const dropdownItem = ev.currentTarget.parentElement;
            let dropdownMenu = dropdownItem.parentElement;
            const companyID = parseInt(dropdownItem.getAttribute("data-company-id"));
            let allowedCompanyIds = this.allowed_company_ids;
            if (dropdownItem.querySelector(".fa-square-o")) {
                // 1 enabled company: Stay in single company mode
                if (this.allowed_company_ids.length === 1) {
                    if (this.isMobile) {
                        dropdownMenu = dropdownMenu.parentElement;
                    }
                    dropdownMenu.querySelector(".fa-check-square").classList.add("fa-square-o");
                    dropdownMenu
                        .querySelector(".fa-check-square")
                        .classList.remove("fa-check-square");
                    dropdownItem.querySelector(".fa-square-o").classList.add("fa-check-square");
                    dropdownItem.querySelector(".fa-square-o").classList.remove("fa-square-o");
                    allowedCompanyIds = [companyID];
                } else {
                    // Multi company mode
                    allowedCompanyIds.push(companyID);
                    dropdownItem.querySelector(".fa-square-o").classList.add("fa-check-square");
                    dropdownItem.querySelector(".fa-square-o").classList.remove("fa-square-o");
                }
            }
            ev.currentTarget.setAttribute("aria-pressed", "true");
            session.setCompanies(companyID, allowedCompanyIds);
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent|KeyEvent} ev
         */
        _onToggleCompanyClick(ev) {
            if (
                ev.type === "keydown" &&
                ev.which !== $.ui.keyCode.ENTER &&
                ev.which !== $.ui.keyCode.SPACE
            ) {
                return;
            }
            const dropdownItem = ev.currentTarget.parentElement;
            const companyID = parseInt(dropdownItem.getAttribute("data-company-id"));
            const allowedCompanyIds = this.allowed_company_ids;
            const currentCompanyId = allowedCompanyIds[0];
            if (dropdownItem.querySelector(".fa-square-o")) {
                allowedCompanyIds.push(companyID);
                dropdownItem.querySelector(".fa-square-o").classList.add("fa-check-square");
                dropdownItem.querySelector(".fa-square-o").classList.remove("fa-square-o");
                ev.currentTarget.setAttribute("aria-checked", "true");
            } else {
                allowedCompanyIds.splice(allowedCompanyIds.indexOf(companyID), 1);
                dropdownItem.querySelector(".fa-check-square").classList.add("fa-square-o");
                dropdownItem.querySelector(".fa-check-square").classList.remove("fa-check-square");
                ev.currentTarget.setAttribute("aria-checked", "false");
            }
            session.setCompanies(currentCompanyId, allowedCompanyIds);
        }
    }

    SwitchCompanyMenu.template = "SwitchCompanyMenu";
    // force this item to be the first one to the left of the UserMenu in the systray
    SwitchCompanyMenu.sequence = 1;

    if (session.display_switch_company_menu) {
        SystrayMenu.Items.push(SwitchCompanyMenu);
    }

    return SwitchCompanyMenu;
});
