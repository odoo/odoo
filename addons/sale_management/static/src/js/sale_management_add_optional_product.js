odoo.define('sale_management.add_optional_product', function (require) {
'use strict';

var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');
var core = require('web.core');
var _t = core._t;

/**
 * This widget is very specific to the sale_order form's
 * optional products feature.
 *
 * Its purpose is to be able to switch back to the "Order Lines"
 * tab after the user adds a product in the "Optional Products" tab.
 */
var AddOptionalProductButton = Widget.extend({
    tagName: 'button',
    className: 'btn btn-link o_icon_button o_list_button',
    events: {
        'click': '_onClick',
    },

    /**
     *
     * @override
     */
    init: function (parent, record, node) {
        this.record = record;
        this.node = node;
        this._super.apply(this, arguments);
    },

    /**
     * Adds the icon tag inside the button.
     *
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (!self.record.res_id) {
                self.$el.addClass('disabled');
            }

            self.$el.append($('<i/>', {
                class: 'fa fa-fw o_button_icon fa-shopping-cart',
                title: _t('Add to order lines')
            }));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Acts like a regular button of type "object" but
     * also switches the tab back to Order Lines (first one).
     *
     * Note that we use a global selector to switch the tab as this widget is a child
     * of the sale_order form and the form component doesn't provide a way to switch its tabs.
     *
     * (This could cause issues if we have several tab containers in the sale order form since
     * the selector will switch all of them.)
     *
     * @param {MouseEvent} ev
     */
    _onClick: function (ev) {
        if (!this.record.res_id) {
            return;
        }

        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('button_clicked', {
            attrs: _.extend({}, this.node.attrs, {
                name: 'button_add_to_order',
                type: 'object'
            }),
            record: this.record,
            on_success: function () {
                $('.nav-tabs a:first').tab('show');
            }
        });
    }
});

widgetRegistry.add('add_optional_product_button', AddOptionalProductButton);

return AddOptionalProductButton;

});
