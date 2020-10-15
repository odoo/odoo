odoo.define('stock.InventoryValidationController', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');

var _t = core._t;
var qweb = core.qweb;

var InventoryValidationController = ListController.extend({
    events: _.extend({
        'click .o_button_validate_inventory': '_onValidateInventory'
    }, ListController.prototype.events),
    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        this.context = renderer.state.getContext();
        this.inventory_id = this.context.default_inventory_id || this.context.active_id;
        return this._super.apply(this, arguments);
    },

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @override
     */
    renderButtons: function () {
        // Temp fix to prevent rendering the buttons twice in a target new
        if (!this.$buttons) {
            this._super.apply(this, arguments);
            var $renderedValidationButton = $(qweb.render('InventoryLines.Buttons'));
            this.$buttons.prepend($renderedValidationButton);
        }
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handler called when user click on validation button in inventory lines
     * view. Makes an rpc to try to validate the inventory, then will go back on
     * the inventory view form if it was validated.
     * This method could also open a wizard in case something was missing.
     *
     * @private
     */
    _onValidateInventory: function () {
        var self = this;
        var prom = Promise.resolve();
        var recordID = this.renderer.getEditableRecordID();
        if (recordID) {
            // If user's editing a record, we wait to save it before to try to
            // validate the inventory.
            prom = this.saveRecord(recordID);
        }

        prom.then(function () {
            var rpc = Promise.resolve();
            if (self.context && self.context.button_validate_picking_ids) {
                // Clean context to remove default inventory values during move and move lines
                // creation.
                var context = Object.keys(self.context || {})
                    .filter(key => ! (key.startsWith('default_')))
                    .reduce((obj, key) => {
                      obj[key] = self.context[key];
                      return obj;
                    }, {});
                rpc = self._rpc({
                    model: 'stock.picking',
                    method: 'button_validate',
                    args: [self.context.button_validate_picking_ids],
                    context: _.extend({}, context , {skip_zqc: true})
                });
            } else {
                rpc = self._rpc({
                    model: 'stock.inventory',
                    method: 'action_validate',
                    args: [self.inventory_id],
                    context: self.context
                });
            }
            rpc.then(function (res) {
                var exitCallback = function (infos) {
                    // In case we discarded a wizard, we do nothing to stay on
                    // the same view...
                    if (infos && infos.special) {
                        return;
                    }
                    // ... but in any other cases, we go back on the inventory form.
                    self.do_notify(
                        false,
                        _t("The inventory has been validated"));

                    self.trigger_up('history_back');
                };

                if (_.isObject(res)) {
                    self.do_action(res, { on_close: exitCallback });
                } else {
                    return exitCallback();
                }
            });
        });
    }
});

return InventoryValidationController;

});
