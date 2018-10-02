
odoo.define('account.section_and_note_backend', function (require) {
// The goal of this file is to contain JS hacks related to allowing
// section and note on sale order and invoice.

// [UPDATED] now also allows configuring products on sale order.

"use strict";
var pyUtils = require('web.py_utils');
var core = require('web.core');
var _t = core._t;
var FieldChar = require('web.basic_fields').FieldChar;
var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var fieldRegistry = require('web.field_registry');
var FieldText = require('web.basic_fields').FieldText;
var ListRenderer = require('web.ListRenderer');

var SectionAndNoteListRenderer = ListRenderer.extend({
    /**
     * We want section and note to take the whole line (except handle and trash)
     * to look better and to hide the unnecessary fields.
     *
     * @override
     */
    _renderBodyCell: function (record, node, index, options) {
        var $cell = this._super.apply(this, arguments);

        var isSection = record.data.display_type === 'line_section';
        var isNote = record.data.display_type === 'line_note';

        if (isSection || isNote) {
            if (node.attrs.widget === "handle") {
                return $cell;
            } else if (node.attrs.name === "name") {
                var nbrColumns = this._getNumberOfCols();
                if (this.handleField) {
                    nbrColumns--;
                }
                if (this.addTrashIcon) {
                    nbrColumns--;
                }
                $cell.attr('colspan', nbrColumns);
            } else {
                return $cell.addClass('o_hidden');
            }
        }

        return $cell;
    },
    /**
     * We add the o_is_{display_type} class to allow custom behaviour both in JS and CSS.
     *
     * @override
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);

        if (record.data.display_type) {
            $row.addClass('o_is_' + record.data.display_type);
        }

        return $row;
    },
    /**
     * We want to add .o_section_and_note_list_view on the table to have stronger CSS.
     *
     * @override
     * @private
     */
    _renderView: function () {
        var def = this._super();
        this.$el.find('> table').addClass('o_section_and_note_list_view');
        return def;
    },
    /**
     * Add support for product configurator
     *
     * @override
     * @private
     */
    _onAddRecord: function (ev) {
        // we don't want the browser to navigate to a the # url
        ev.preventDefault();

        // we don't want the click to cause other effects, such as unselecting
        // the row that we are creating, because it counts as a click on a tr
        ev.stopPropagation();

        // but we do want to unselect current row
        var self = this;
        this.unselectRow().then(function () {
            var context = ev.currentTarget.dataset.context;

            var pricelistId = self._getPricelistId();
            if (context && pyUtils.py_eval(context).open_product_configurator){
                self._rpc({
                    model: 'ir.model.data',
                    method: 'xmlid_to_res_id',
                    kwargs: {xmlid: 'sale.sale_product_configurator_view_form'},
                }).then(function (res_id) {
                    self.do_action({
                        name: _t('Configure a product'),
                        type: 'ir.actions.act_window',
                        res_model: 'sale.product.configurator',
                        views: [[res_id, 'form']],
                        target: 'new',
                        context: {
                            'default_pricelist_id': pricelistId
                        }
                    }, {
                        on_close: function (products) {
                            if (products && products !== 'special'){
                                self.trigger_up('add_record', {
                                    context: self._productsToRecords(products),
                                    forceEditable: "bottom" ,
                                    allowWarning: true,
                                    onSuccess: function (){
                                        self.unselectRow();
                                    }
                                });
                            }
                        }
                    });
                });
            } else {
                self.trigger_up('add_record', {context: context && [context]}); // TODO write a test, the deferred was not considered
            }
        });
    },

    /**
     * Will try to get the pricelist_id value from the parent sale_order form
     *
     * @private
     * @returns {integer} pricelist_id's id
     */
    _getPricelistId: function () {
        var saleOrderForm = this.getParent() && this.getParent().getParent();
        var stateData = saleOrderForm && saleOrderForm.state && saleOrderForm.state.data;
        var pricelist_id = stateData.pricelist_id && stateData.pricelist_id.data && stateData.pricelist_id.data.id;

        return pricelist_id;
    },

    /**
     * Will map the products to appropriate record objects that are
     * ready for the default_get
     *
     * @private
     * @param {Array} products The products to transform into records
     */
    _productsToRecords: function (products) {
        var records = [];
        _.each(products, function (product){
            var record = {
                default_product_id: product.product_id,
                default_product_uom_qty: product.quantity
            };

            if (product.no_variant_attribute_values) {
                var default_product_no_variant_attribute_values = [];
                _.each(product.no_variant_attribute_values, function (attribute_value) {
                        default_product_no_variant_attribute_values.push(
                            [4, parseInt(attribute_value.value)]
                        );
                });
                record['default_product_no_variant_attribute_value_ids']
                    = default_product_no_variant_attribute_values;
            }

            if (product.product_custom_attribute_values) {
                var default_custom_attribute_values = [];
                _.each(product.product_custom_attribute_values, function (attribute_value) {
                    default_custom_attribute_values.push(
                            [0, 0, {
                                attribute_value_id: attribute_value.attribute_value_id,
                                custom_value: attribute_value.custom_value
                            }]
                        );
                });
                record['default_product_custom_attribute_value_ids']
                    = default_custom_attribute_values;
            }

            records.push(record);
        });

        return records;
    }
});

// We create a custom widget because this is the cleanest way to do it:
// to be sure this custom code will only impact selected fields having the widget
// and not applied to any other existing ListRenderer.
var SectionAndNoteFieldOne2Many = FieldOne2Many.extend({
    /**
     * We want to use our custom renderer for the list.
     *
     * @override
     */
    _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return SectionAndNoteListRenderer;
        }
        return this._super.apply(this, arguments);
    },
});

// This is a merge between a FieldText and a FieldChar.
// We want a FieldChar for section,
// and a FieldText for the rest (product and note).
var SectionAndNoteFieldText = function (parent, name, record, options) {
    var isSection = record.data.display_type === 'line_section';
    var Constructor = isSection ? FieldChar : FieldText;
    return new Constructor(parent, name, record, options);
};

fieldRegistry.add('section_and_note_one2many', SectionAndNoteFieldOne2Many);
fieldRegistry.add('section_and_note_text', SectionAndNoteFieldText);

});
