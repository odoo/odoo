odoo.define('stock.InventoryReportListController', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');

var qweb = core.qweb;


var InventoryReportListController = ListController.extend({

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    init: function (parent, model, renderer, params) {
        this.context = renderer.state.getContext();
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        if (this.context.no_at_date) {
            return;
        }
        var $buttonToDate = $(qweb.render('InventoryReport.Buttons'));
        $buttonToDate.on('click', this._onOpenWizard.bind(this));
        this.$buttons.prepend($buttonToDate);
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handler called when the user clicked on the 'Inventory at Date' button.
     * Opens wizard to display, at choice, the products inventory or a computed
     * inventory at a given date.
     */
    _onOpenWizard: function () {
        var state = this.model.get(this.handle, {raw: true});
        var stateContext = state.getContext();
        var context = {
            active_model: this.modelName,
        };
        if (stateContext.default_product_id) {
            context.product_id = stateContext.default_product_id;
        } else if (stateContext.product_tmpl_id) {
            context.product_tmpl_id = stateContext.product_tmpl_id;
        }
        this.do_action({
            res_model: 'stock.quantity.history',
            views: [[false, 'form']],
            target: 'new',
            type: 'ir.actions.act_window',
            context: context,
        });
    },
});

return InventoryReportListController;

});
