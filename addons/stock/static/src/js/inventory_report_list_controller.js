odoo.define('stock.InventoryReportListController', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');

var qweb = core.qweb;


var InventoryReportListController = ListController.extend({

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @override
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        var $buttonToDate = $(qweb.render('InventoryReport.Buttons'));
        $buttonToDate.on('click', this._onOpenWizard.bind(this));

        $buttonToDate.prependTo($node.find('.o_list_buttons'));
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
        this.do_action({
            res_model: 'stock.quantity.history',
            views: [[false, 'form']],
            target: 'new',
            type: 'ir.actions.act_window',
            context: {
                active_model: this.modelName,
            }
        });
    },
});

return InventoryReportListController;

});
