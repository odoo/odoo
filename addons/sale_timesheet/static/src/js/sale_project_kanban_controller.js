odoo.define('sale_timesheet.sale_project_kanban_controller', function (require) {
"use strict";

var core = require('web.core');
var ProjectKanbanController = require('project.project_kanban');
var session = require('web.session');

var QWeb = core.qweb;

// YTI TODO : Master remove file

var SaleProjectKanbanController = ProjectKanbanController.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _showCreateSOButton: async function () {
        var self = this;
        this.activeProjectIds = this.initialState.context.active_ids;

        if (!this.activeProjectIds || this.activeProjectIds.length !== 1) {
            this.showCreateSaleOrder = false;
            return;
        }
        var canCreateSO = await session.user_has_group('sales_team.group_sale_salesman');
        if (canCreateSO) {
            await this._rpc({
                model: 'project.project',
                method: 'search_count',
                args: [[
                    ["id", "in", this.activeProjectIds],
                    ["bill_type", "=", "customer_project"],
                    ["sale_order_id", "=", false],
                    ["allow_billable", "=", true],
                    ["allow_timesheets", "=", true],
                ]],
            }).then(function (projectCount) {
                self.showCreateSaleOrder = projectCount !== 0;
            });
        } else {
            this.showCreateSaleOrder = false;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCreateSaleOrder: function (ev) {
        ev.preventDefault();
        this.do_action('sale_timesheet.project_project_action_multi_create_sale_order', {
            additional_context: {
                'active_id': this.activeProjectIds && this.activeProjectIds[0],
                'active_model': "project.project",
            },
            on_close: async () => await this.reload()
        });
    },
});

return SaleProjectKanbanController;

});
