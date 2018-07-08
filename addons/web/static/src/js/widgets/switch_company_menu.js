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
        'click .dropdown-menu li a[data-menu]': '_onClick',
    },
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.isMobile = config.device.isMobile;
        this._onClick = _.debounce(this._onClick, 1500, true);
    },
    /**
     * @override
     */
    willStart: function () {
        return session.user_companies ? this._super() : $.Deferred().reject();
    },
    /**
     * @override
     */
    start: function () {
        var companiesList = '';
        if (this.isMobile) {
            companiesList = '<li class="bg-info">' +
                _t('Tap on the list to change company') + '</li>';
        }
        else {
            this.$('.oe_topbar_name').text(session.user_companies.current_company[1]);
        }
        _.each(session.user_companies.allowed_companies, function(company) {
            var a = '';
            if (company[0] === session.user_companies.current_company[0]) {
                a = '<i class="fa fa-check mr8"></i>';
            } else {
                a = '<span style="margin-right: 24px;"/>';
            }
            companiesList += '<li><a href="#" data-menu="company" data-company-id="' +
                            company[0] + '">' + a + company[1] + '</a></li>';
        });
        this.$('.dropdown-menu').html(companiesList);
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick: function (ev) {
        ev.preventDefault();
        var companyID = $(ev.currentTarget).data('company-id');
        this._rpc({
            model: 'res.users',
            method: 'write',
            args: [[session.uid], {'company_id': companyID}],
        })
        .then(function() {
            location.reload();
        });
    },
});

SystrayMenu.Items.push(SwitchCompanyMenu);

return SwitchCompanyMenu;

});
