odoo.define('base_accounting_kit.account_asset', function(require) {
"use strict";

/**
 * The purpose of this widget is to shows a toggle button on depreciation and
 * installment lines for posted/unposted line. When clicked, it calls the method
 * create_move on the object account.asset.depreciation.line.
 * Note that this widget can only work on the account.asset.depreciation.line
 * model as some of its fields are harcoded.
 */

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var registry = require('web.field_registry');

var _t = core._t;

var AccountAssetWidget = AbstractField.extend({
    events: _.extend({}, AbstractField.prototype.events, {
        'click': '_onClick',
    }),
    description: "",

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isSet: function () {
        return true; // it should always be displayed, whatever its value
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        var className = '';
        var disabled = true;
        var title;
        if (this.recordData.move_posted_check) {
            className = 'o_is_posted';
            title = _t('Posted');
        } else if (this.recordData.move_check) {
            className = 'o_unposted';
            title = _t('Accounting entries waiting for manual verification');
        } else {
            disabled = false;
            title = _t('Unposted');
        }
        var $button = $('<button/>', {
            type: 'button',
            title: title,
            disabled: disabled,
        }).addClass('btn btn-sm btn-link fa fa-circle o_deprec_lines_toggler ' + className);
        this.$el.html($button);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClick: function (event) {
        event.stopPropagation();
        this.trigger_up('button_clicked', {
            attrs: {
                name: 'create_move',
                type: 'object',
            },
            record: this.record,
        });
    },
});

registry.add("deprec_lines_toggler", AccountAssetWidget);

});
