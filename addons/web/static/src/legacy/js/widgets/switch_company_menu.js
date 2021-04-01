odoo.define('web.SwitchCompanyMenu', function(require) {
"use strict";

/**
 * When Odoo is configured in multi-company mode, users should obviously be able
 * to switch their interface from one company to the other.  This is the purpose
 * of this widget, by displaying a dropdown menu in the systray.
 */

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var _t = core._t;

var SwitchCompanyMenu = Widget.extend({
    template: 'SwitchCompanyMenu',
    events: {
        'click .dropdown-item[data-menu] div.log_into': '_onSwitchCompanyClick',
        'keydown .dropdown-item[data-menu] div.log_into': '_onSwitchCompanyClick',
        'click .dropdown-item[data-menu] div.toggle_company': '_onToggleCompanyClick',
        'keydown .dropdown-item[data-menu] div.toggle_company': '_onToggleCompanyClick',
    },
    // force this item to be the first one to the left of the UserMenu in the systray
    sequence: 1,
    TOGGLE_DELAY: 1000,
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.isMobile = config.device.isMobile;
        this._onSwitchCompanyClick = _.debounce(this._onSwitchCompanyClick, 1500, true);
    },

    /**
     * @override
     */
    willStart: function () {
        this.allowed_company_ids = String(session.user_context.allowed_company_ids)
                                    .split(',')
                                    .map(function (id) {return parseInt(id);});
        this.user_companies = session.user_companies.allowed_companies;
        this.current_company = this.allowed_company_ids[0];
        this.current_company_name = session.user_companies.allowed_companies[this.current_company]['name'];
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getElements() {
        return [...this.el.querySelectorAll(".dropdown-item")];
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent|KeyEvent} ev
     */
    _onSwitchCompanyClick: function (ev) {
        if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        var dropdownItem = $(ev.currentTarget).parent();
        var dropdownMenu = dropdownItem.parent();
        var companyID = dropdownItem.data('company-id');
        var allowed_company_ids = this.allowed_company_ids;
        if (dropdownItem.find('.fa-square-o').length) {
            // 1 enabled company: Stay in single company mode
            if (this.allowed_company_ids.length === 1) {
                if (this.isMobile) {
                    dropdownMenu = dropdownMenu.parent();
                }
                dropdownMenu.find('.fa-check-square').removeClass('fa-check-square').addClass('fa-square-o');
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                allowed_company_ids = [companyID];
            } else { // Multi company mode
                allowed_company_ids.push(companyID);
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
            }
        }
        $(ev.currentTarget).attr('aria-pressed', 'true');
        session.setCompanies(companyID, allowed_company_ids);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent|KeyEvent} ev
     */
    _onToggleCompanyClick: function (ev) {
        if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        var dropdownItem = $(ev.currentTarget).parent();
        const allowedCompanyIds = this.allowed_company_ids;
        const currentCompanyId = allowedCompanyIds[0];
        if (dropdownItem.find('.fa-square-o').length) {
            dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
            $(ev.currentTarget).attr('aria-checked', 'true');
        } else {
            dropdownItem.find('.fa-check-square').addClass('fa-square-o').removeClass('fa-check-square');
            $(ev.currentTarget).attr('aria-checked', 'false');
        }
        const toggleCompany = () => {
            [...this._getElements()].forEach((item) => {
                const companyID = parseInt(item.getAttribute('data-company-id'));
                if (item.querySelector('.fa-check-square')) {
                    if (!allowedCompanyIds.includes(companyID)) {
                        allowedCompanyIds.push(companyID);
                    }
                } else if (allowedCompanyIds.includes(companyID)) {
                    allowedCompanyIds.splice(allowedCompanyIds.indexOf(companyID), 1);
                }
            });
            session.setCompanies(currentCompanyId, allowedCompanyIds);
        };
        if (this.toggleTimeout) {
            clearTimeout(this.toggleTimeout);
        }
        this.toggleTimeout = setTimeout(toggleCompany, this.TOGGLE_DELAY);
    },

});

if (session.display_switch_company_menu) {
    SystrayMenu.Items.push(SwitchCompanyMenu);
}

return SwitchCompanyMenu;

});
