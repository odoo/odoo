odoo.define('purchase_requisition.purchase_requisition', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.DataModel');
var ListView = require('web.ListView');

var QWeb = core.qweb;
var _t = core._t;


var CompareListView = ListView.extend({
    render_buttons: function ($node) {
        if (!this.$buttons) {
            this.$buttons = $(QWeb.render("CompareListView.buttons", {'widget': this}));

            this.$buttons.find('.oe_generate_po').click(this.proxy('generate_purchase_order'));

            $node = $node || this.options.$buttons;
            if ($node) {
                this.$buttons.appendTo($node);
            } else {
                this.$('.oe_list_buttons').replaceWith(this.$buttons);
            }
        }
    },

    generate_purchase_order: function () {
        var self = this;
        new Model(self.dataset.model).call("generate_po",[self.dataset.context.tender_id,self.dataset.context]).then(function(result) {
            self.ViewManager.action_manager.history_back();
        });
    },
});

core.view_registry.add('tree_purchase_order_line_compare', CompareListView);

});
