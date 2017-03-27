odoo.define('web.OrgChart', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var form_common = require('web.form_common');

var QWeb = core.qweb;
var _t = core._t;

var FieldOrgChart = form_common.AbstractField.extend({

    events: {
        "click .o_employee_redirect": "on_employee_redirect",
        "click .o_employee_sub_redirect": "on_employee_sub_redirect",
    },

    init: function () {
        this._super.apply(this, arguments);
    },

    start: function () {
        this.reinit();
        return this._super();
    },

    reinit: function () {
        this.emp_data = {
            managers: [],
            children: [],
        };
    },

    set_value: function (_value) {
        this.reinit();
        this._super(_value);
    },

    render_value: function () {
        if (! this.view.datarecord.id) {
            return this.$el.html(QWeb.render("hr_org_chart", {widget: this}));
        }

        var self = this;
        this.get_org_chart_data(this.view.datarecord.id).then(function () {
            self.$el.html(QWeb.render("hr_org_chart", {widget: self}));
        }).then(function () {
            self.$el.find('[data-toggle="popover"]').each(function () {
                $(this).popover({
                    html: true,
                    title: function() {
                        var $title = $(QWeb.render('hr_orgchart_emp_popover_title', {employee: {
                            name: $(this).data('emp-name'),
                            id: $(this).data('emp-id'),
                        }}));
                        $title.on('click', '.o_employee_redirect', function(event) {
                            self.on_employee_redirect(event);
                        });
                        return $title;
                    },
                    container: 'body',
                    placement: 'left',
                    trigger: 'focus',
                    content: function() {
                        var $content = $(QWeb.render('hr_orgchart_emp_popover_content', {employee: {
                            id: $(this).data('emp-id'),
                            name: $(this).data('emp-name'),
                            direct_sub_count: parseInt($(this).data('emp-dir-subs')),
                            indirect_sub_count: parseInt($(this).data('emp-ind-subs')),
                        }}));
                        $content.on('click', '.o_employee_sub_redirect', function(event) {
                            self.on_employee_sub_redirect(event);
                        });
                        return $content;
                    },
                    template: $(QWeb.render('hr_orgchart_emp_popover', {})),
                });
            });
        });
    },

    get_org_chart_data: function (employee_id) {
        var self = this;
        return ajax.jsonRpc('/hr/get_org_chart', 'call', {
            employee_id: employee_id,
        }).then(function (data) {
            self.emp_data = data;
        });
    },

    on_employee_redirect: function (event) {
        event.preventDefault();
        var employee_id = parseInt($(event.currentTarget).data('employee-id'));
        return this.do_action({
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
            res_model: 'hr.employee',
            res_id: employee_id,
        });
    },

    on_employee_sub_redirect: function (event) {
        event.preventDefault();
        var employee_id = parseInt($(event.currentTarget).data('employee-id'));
        var employee_name = $(event.currentTarget).data('employee-name');
        var type = $(event.currentTarget).data('type') || 'direct';
        var domain = [['parent_id', '=', employee_id]];
        var name = _.str.sprintf(_t("Direct Subordinates of %s"), employee_name);
        if (type === 'total') {
            domain = ['&', ['parent_id', 'child_of', employee_id], ['id', '!=', employee_id]];
            name = _.str.sprintf(_t("Subordinates of %s"), employee_name);
        }
        else if (type === 'indirect') {
            domain = ['&', '&', ['parent_id', 'child_of', employee_id], ['parent_id', '!=', employee_id], ['id', '!=', employee_id]];
            name = _.str.sprintf(_t("Indirect Subordinates of %s"), employee_name);
        }
        if (employee_id) {
            return this.do_action({
                name: name,
                type: 'ir.actions.act_window',
                view_type: 'tree',
                view_mode: 'kanban,tree,form',
                views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
                target: 'current',
                res_model: 'hr.employee',
                domain: domain,
            });
        }
    },

});

core.form_widget_registry.add('hr_org_chart', FieldOrgChart);


return FieldOrgChart;
});
