odoo.define('web.SwitchCompanyMenu', function(require) {
    "use strict";

    var Model = require('web.Model');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    
    var SwitchCompanyMenu = Widget.extend({
        template: 'SwitchCompanyMenu',
        willStart: function(){
            var self = this;
            var def = $.Deferred();
            new Model("res.users").call("read_companies").then(function(res) {
                if (res){
                    self.all_allowed_companies = res.all_allowed_companies;
                    self.current_company = res.current_company;
                    def.resolve();
                } else {
                    def.reject();
                }
            }).fail(function(){
                def.reject();
            });
            return $.when(this._super(), def);
        },
        start: function() {
            var self = this;

            this.$el.on('click', '.dropdown-menu li a[data-menu]', function(ev) {
                ev.preventDefault();
                var company_id = $(ev.currentTarget).data('company-id');
                new Model('res.users').call('write', [[session.uid], {'company_id': company_id}]).then(function() {
                    location.reload();
                });
            });

            self.$('.oe_topbar_name').text(self.current_company[1]);

            var companies_list = '';
            _.each(self.all_allowed_companies, function(company) {
                var a = '';
                if(company[0] == self.current_company[0]) {
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
