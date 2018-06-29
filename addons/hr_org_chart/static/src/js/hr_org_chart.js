odoo.define('web.OrgChart', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var concurrency = require('web.concurrency');
var core = require('web.core');
var field_registry = require('web.field_registry');

var QWeb = core.qweb;
var _t = core._t;

var FieldOrgChart = AbstractField.extend({

    events: {
        "click .o_employee_redirect": "_onEmployeeRedirect",
        "click .o_employee_sub_redirect": "_onEmployeeSubRedirect",
    },
    /**
     * @constructor
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.dm = new concurrency.DropMisordered();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the chart data through a rpc call.
     *
     * @private
     * @param {integer} employee_id
     * @returns {Deferred}
     */
    _getOrgData: function (employee_id) {
        var self = this;
        return this.dm.add(this._rpc({
            route: '/hr/get_org_chart',
            params: {
                employee_id: employee_id,
            },
        })).then(function (data) {
            self.orgData = data;
        });
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        if (!this.recordData.id) {
            return this.$el.html(QWeb.render("hr_org_chart", {
                managers: [],
                children: [],
            }));
        }

        var self = this;
        return this._getOrgData(this.recordData.id).then(function () {
            self.$el.html(QWeb.render("hr_org_chart", self.orgData));
            self.$('[data-toggle="popover"]').each(function () {
                $(this).popover({
                    html: true,
                    title: function () {
                        var $title = $(QWeb.render('hr_orgchart_emp_popover_title', {
                            employee: {
                                name: $(this).data('emp-name'),
                                id: $(this).data('emp-id'),
                            },
                        }));
                        $title.on('click',
                            '.o_employee_redirect', _.bind(self._onEmployeeRedirect, self));
                        return $title;
                    },
                    container: 'body',
                    placement: 'left',
                    trigger: 'focus',
                    content: function () {
                        var $content = $(QWeb.render('hr_orgchart_emp_popover_content', {
                            employee: {
                                id: $(this).data('emp-id'),
                                name: $(this).data('emp-name'),
                                direct_sub_count: parseInt($(this).data('emp-dir-subs')),
                                indirect_sub_count: parseInt($(this).data('emp-ind-subs')),
                            },
                        }));
                        $content.on('click',
                            '.o_employee_sub_redirect', _.bind(self._onEmployeeSubRedirect, self));
                        return $content;
                    },
                    template: $(QWeb.render('hr_orgchart_emp_popover', {})),
                });
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Redirect to the employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Deferred} action loaded
     */
    _onEmployeeRedirect: function (event) {
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
    /**
     * Redirect to the sub employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Deferred} action loaded
     */
    _onEmployeeSubRedirect: function (event) {
        event.preventDefault();
        var employee_id = parseInt($(event.currentTarget).data('employee-id'));
        var employee_name = $(event.currentTarget).data('employee-name');
        var type = $(event.currentTarget).data('type') || 'direct';
        var domain = [['parent_id', '=', employee_id]];
        var name = _.str.sprintf(_t("Direct Subordinates of %s"), employee_name);
        if (type === 'total') {
            domain = ['&', ['parent_id', 'child_of', employee_id], ['id', '!=', employee_id]];
            name = _.str.sprintf(_t("Subordinates of %s"), employee_name);
        } else if (type === 'indirect') {
            domain = ['&', '&',
                ['parent_id', 'child_of', employee_id],
                ['parent_id', '!=', employee_id],
                ['id', '!=', employee_id]
            ];
            name = _.str.sprintf(_t("Indirect Subordinates of %s"), employee_name);
        }
        if (employee_id) {
            return this.do_action({
                name: name,
                type: 'ir.actions.act_window',
                view_mode: 'kanban,list,form',
                views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                target: 'current',
                res_model: 'hr.employee',
                domain: domain,
            });
        }
    },
});

field_registry.add('hr_org_chart', FieldOrgChart);

return FieldOrgChart;

});
