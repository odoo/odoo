odoo.define('sale_timesheet.sale_project_kanban_controller', function (require) {
"use strict";

var core = require('web.core');
var ProjectKanbanController = require('project.project_kanban');
var session = require('web.session');

var QWeb = core.qweb;

var SaleProjectKanbanController = ProjectKanbanController.include({
    events: _.extend({}, ProjectKanbanController.prototype.events, {
        'click .o_create_sale_order': '_onCreateSaleOrder'
    }),

    /**
     * @override
     */
    willStart: async function () {
        const _super = this._super.bind(this);
        await this._showCreateSOButton();
        return _super(...arguments);
    },

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
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {jQuery} [$node]
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        this.$saleButtons = $(QWeb.render('SaleProjectKanbanView.buttons'));
        var state = this.model.get(this.handle, {raw: true});
        var createHidden = this.is_action_enabled('group_create') && state.isGroupedByM2ONoColumn || !this.showCreateSaleOrder;
        this.$saleButtons.toggleClass('o_hidden', createHidden);
        this.$saleButtons.appendTo(this.$buttons);

    },

    /**
     * @override
     */
    updateButtons: async function () {
        if (!this.$buttons) {
            return;
        }
        this._super.apply(this, arguments);

        await this._showCreateSOButton();
        var state = this.model.get(this.handle, {raw: true});
        var createHidden = this.is_action_enabled('group_create') && state.isGroupedByM2ONoColumn || !this.showCreateSaleOrder;
        this.$buttons.find('.o_create_sale_order').toggleClass('o_hidden', createHidden);
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
