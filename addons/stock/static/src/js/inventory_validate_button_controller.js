odoo.define('stock.InventoryValidationController', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');

var qweb = core.qweb;

var InventoryValidationController = ListController.extend({

    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        var context = renderer.state.getContext();
        this.inventory_id = context.active_id;
        return this._super.apply(this, arguments);
    },

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @override
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        var $validationButton = $(qweb.render('InventoryLines.Buttons'));
        $validationButton.on('click', this._onValidateInventory.bind(this));
        $validationButton.appendTo($node.find('.o_list_buttons'));
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handler called when user click on validation button in inventory lines
     * view. Will validate inventory, then will open it.
     */
    _onValidateInventory: function () {
        var self = this;
        this._rpc({
            model: 'stock.inventory.line',
            method: 'action_validate_inventory',
            args: [this.inventory_id]
        }).then(function (response) {
            if (response.state && response.state === 'ok') {
                self.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'stock.inventory',
                    res_id: self.inventory_id,
                    views: [[false, 'form']],
                    target: 'current'
                });
            }
        });
    },
});

return InventoryValidationController;

});
