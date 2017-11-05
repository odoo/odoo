odoo.define('web.SwitchCompanyMenu', function(require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var _t = core._t;

var SwitchCompanyMenu = Widget.extend({
    template: 'SwitchCompanyMenu',
    willStart: function() {
        this.isMobile = config.device.isMobile;
        if (!session.user_companies) {
            return $.Deferred().reject();
        }
        return this._super();
    },
    start: function() {
        var self = this;
        this.$el.on('click', '.dropdown-menu li a[data-menu]', _.debounce(function(ev) {
            ev.preventDefault();
            var company_id = $(ev.currentTarget).data('company-id');
            self._rpc({
                    model: 'res.users',
                    method: 'write',
                    args: [[session.uid], {'company_id': company_id}],
                })
                .then(function() {
                    location.reload();
                });
        }, 1500, true));

        var companies_list = '';
        if (this.isMobile) {
            companies_list = '<li class="bg-info">' + _t('Tap on the list to change company') + '</li>';
        }
        else {
            self.$('.oe_topbar_name').text(session.user_companies.current_company[1]);
        }
        _.each(session.user_companies.allowed_companies, function(company) {
            var a = '';
            if (company[0] === session.user_companies.current_company[0]) {
                a = '<i class="fa fa-check mr8"></i>';
            } else {
                a = '<span class="mr24"/>';
            }
            companies_list += '<li><a href="#" data-menu="company" data-company-id="' + company[0] + '">' + a + company[1] + '</a></li>';
        });
        self.$('.dropdown-menu').html(companies_list);
        return this._super();
    },
});

SystrayMenu.Items.push(SwitchCompanyMenu);

return SwitchCompanyMenu;

});
