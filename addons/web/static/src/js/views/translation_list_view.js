odoo.define('web.TranslationListView', function (require) {
"use strict";

/**
 * This file defines the TranslateListView, an extension of the ListView that
 * is used by the TranslateField in Form views.
 */
var ListController = require('web.ListController');
var ListRenderer = require('web.ListRenderer');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');
var core = require('web.core');

var _t = core._t;

var TranslateListController = ListController.extend({
    buttons_template: 'TranslationListView.buttons',
    /**
     * @override
     */
    renderButtons: function () {
        this._super.apply(this, arguments);
        if (this.$buttons) {
            this.$buttons.find('.o_list_button_save').text(_t('Confirm'));
            this.$buttons.on('click', '.o_list_button_cancel', this._onCancel.bind(this));
        }
    },
    /**
     * this method calls when we click on cancel button
     *
     * @private
     */
    _onCancel: function (ev) {
        this._callButtonAction({'special':'cancel'},this.renderer.state);
    },
    /**
     * @override
     */
    _onSaveLine: function (ev) {
        this._super.apply(this, arguments);
        this._callButtonAction({'special':'cancel'},this.renderer.state);
    },
});

var TranslateListRenderer = ListRenderer.extend({
    /**
     * @override
     * @private
     * @returns {jQueryElement} a <td> element
     */
    _renderBodyCell: function (record, node, colIndex, options) {
        var $td = this._super.apply(this, arguments);
        if (options.mode  === 'readonly' && !record.data.value && node.attrs.name === "value"){
            $td.text(record.data.source);
        }
        return $td;
    },
});

var TranslateListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: TranslateListController,
        Renderer: TranslateListRenderer,
    }),
});

viewRegistry.add('translate_field_tree', TranslateListView);
});
