odoo.define('hr.suggestions', function (require) {
"use strict";

var mail = require('mail.mail');
var core = require('web.core');
var data = require('web.data');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var removed_suggested_employee = [];

var Employees = Widget.extend({
    events: {
        'click .oe_suggestion_remove.oe_suggestion_employee': 'stop_employee_suggestion',
        'click .oe_suggestion_remove_item.oe_suggestion_employee': 'remove_employee_suggestion',
        'click .oe_suggestion_follow': 'follow_employee',
    },

    init: function () {
        this._super(this, arguments);
        this.hr_employee = new data.DataSetSearch(this, 'hr.employee');
        this.res_users = new data.DataSetSearch(this, 'res.users');
        this.employees = [];
    },

    start: function () {
        this._super.apply(this, arguments);
        return this.fetch_suggested_employee();
    },

    fetch_suggested_employee: function () {
        var self = this;
        var employee = self.hr_employee.call('get_suggested_thread', {'removed_suggested_threads': removed_suggested_employee}).then(function (res) {
            _(res).each(function (result) {
                result['image']=self.session.url('/web/binary/image', {model: 'hr.employee', field: 'image_small', id: result.id});
            });
            self.employees = res;
        });
        return $.when(employee).done(this.proxy('display_suggested_employees'));
    },

    display_suggested_employees: function () {
        var suggested_employees = this.$('.oe_sidebar_suggestion.oe_suggestion_employee');
        if (suggested_employees) {
            suggested_employees.remove();
        }
        if (this.employees.length === 0) {
            return this.$el.empty();
        }
        return this.$el.empty().html(QWeb.render('hr.suggestions.employees', {'widget': this}));
    },

    follow_employee: function (event) {
        var self = this;
        var employee_id = parseInt($(event.currentTarget).attr('id'), 10);
        return this.hr_employee.call('message_subscribe_users', [[employee_id], [this.session.uid], undefined]).then(function(res) {
            self.fetch_suggested_employee();
        });
    },

    remove_employee_suggestion: function (event) {
        removed_suggested_employee.push($(event.currentTarget).attr('id'));
        return this.fetch_suggested_employee();
    },

    stop_employee_suggestion: function (event) {
        var self = this;
        return this.res_users.call('stop_showing_employees_suggestions', [this.session.uid]).then(function(res) {
            self.$(".oe_sidebar_suggestion.oe_suggestion_employee").hide();
        });
    }
});

mail.Sidebar.include({
    start: function () {
        this._super.apply(this, arguments);
        var sug_employees = new Employees(this);
        return sug_employees.appendTo(this.$('.oe_suggestions_employees'));
    },
});

});
