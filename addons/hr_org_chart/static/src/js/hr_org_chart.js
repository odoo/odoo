odoo.define('web.OrgChart', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var concurrency = require('web.concurrency');
var core = require('web.core');
var field_registry = require('web.field_registry');
var session = require('web.session');

var QWeb = core.qweb;
var _t = core._t;

var FieldOrgChart = AbstractField.extend({

    events: {
        "click .o_employee_redirect": "_onEmployeeRedirect",
        "click .o_employee_sub_redirect": "_onEmployeeSubRedirect",
        "click .o_employee_more_managers": "_onEmployeeMoreManager"
    },
    /**
     * @constructor
     * @override
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.dm = new concurrency.DropMisordered();
        this.employee = null;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Get the chart data through a rpc call.
     *
     * @private
     * @param {integer} employee_id
     * @returns {Promise}
     */
    _getOrgData: function () {
        var self = this;
        return this.dm.add(this._rpc({
            route: '/hr/get_org_chart',
            params: {
                employee_id: this.employee,
                context: session.user_context,
            },
        })).then(function (data) {
            return data;
        });
    },
    /**
     * Get subordonates of an employee through a rpc call.
     *
     * @private
     * @param {integer} employee_id
     * @returns {Promise}
     */
    _getSubordinatesData: function (employee_id, type) {
        return this.dm.add(this._rpc({
            route: '/hr/get_subordinates',
            params: {
                employee_id: employee_id,
                subordinates_type: type,
                context: session.user_context,
            },
        }));
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
        else if (!this.employee) {
            // the widget is either dispayed in the context of a hr.employee form or a res.users form
            this.employee = this.recordData.employee_ids !== undefined ? this.recordData.employee_ids.res_ids[0] : this.recordData.id;
        }

        var self = this;
        return this._getOrgData().then(function (orgData) {
            if (_.isEmpty(orgData)) {
                orgData = {
                    managers: [],
                    children: [],
                }
            }
            orgData.view_employee_id = self.recordData.id;
            self.$el.html(QWeb.render("hr_org_chart", orgData));
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
                    container: this,
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
                    template: QWeb.render('hr_orgchart_emp_popover', {}),
                });
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onEmployeeMoreManager: function(event) {
        event.preventDefault();
        this.employee = parseInt($(event.currentTarget).data('employee-id'));
        this._render();
    },
    /**
     * Redirect to the employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    _onEmployeeRedirect: function (event) {
        var self = this;
        event.preventDefault();
        var employee_id = parseInt($(event.currentTarget).data('employee-id'));
        return this._rpc({
            model: 'hr.employee',
            method: 'get_formview_action',
            args: [employee_id],
        }).then(function(action) {
            return self.do_action(action); 
        });
    },
    /**
     * Redirect to the sub employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    _onEmployeeSubRedirect: function (event) {
        event.preventDefault();
        var employee_id = parseInt($(event.currentTarget).data('employee-id'));
        var employee_name = $(event.currentTarget).data('employee-name');
        var type = $(event.currentTarget).data('type') || 'direct';
        var self = this;
        if (employee_id) {
            this._getSubordinatesData(employee_id, type).then(function(data) {
                var domain = [['id', 'in', data]];
                return self._rpc({
                    model: 'hr.employee',
                    method: 'get_formview_action',
                    args: [employee_id],
                }).then(function(action) {
                    action = _.extend(action, {
                        'name': _t('Team'),
                        'view_mode': 'kanban,list,form',
                        'views':  [[false, 'kanban'], [false, 'list'], [false, 'form']],
                        'domain': domain,
                        'context': {
                            'default_parent_id': employee_id,
                        }
                    });
                    delete action['res_id'];
                    return self.do_action(action); 
                });
            });
        }
    },
});

field_registry.add('hr_org_chart', FieldOrgChart);

return FieldOrgChart;

});
