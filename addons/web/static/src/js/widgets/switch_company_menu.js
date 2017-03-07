odoo.define('web.SwitchCompanyMenu', function(require) {
"use strict";

var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var SwitchCompanyMenu = Widget.extend({
    template: 'SwitchCompanyMenu',
    willStart: function() {
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
            self._rpc('res.users', 'write')
                .args([[session.uid], {'company_id': company_id}])
                .exec()
                .then(function() {
                    location.reload();
                });
        }, 1500, true));

        self.$('.oe_topbar_name').text(session.user_companies.current_company[1]);

        var companies_list = '';
        _.each(session.user_companies.allowed_companies, function(company) {
            var a = '';
            if (company[0] === session.user_companies.current_company[0]) {
                a = '<i class="fa fa-check o_current_company"></i>';
            } else {
                a = '<span class="o_company"/>';
            }
            companies_list += '<li><a href="#" data-menu="company" data-company-id="' + company[0] + '">' + a + company[1] + '</a></li>';
        });
        self.$('.dropdown-menu').html(companies_list);
        return this._super();
    },
});

SystrayMenu.Items.push(SwitchCompanyMenu);

});
