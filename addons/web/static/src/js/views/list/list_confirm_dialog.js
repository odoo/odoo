odoo.define('web.ListConfirmDialog', function (require) {
"use strict";

const core = require('web.core');
const Dialog = require('web.Dialog');

const _t = core._t;
const qweb = core.qweb;

/**
 * Multi edition confirmation modal for list views.
 *
 * Handles the display of the amount of changed records (+ valid ones) and
 * of the widget representing the new value.
 *
 * @class
 */
const ListConfirmDialog = Dialog.extend({

    /**
     * @constructor
     * @override
     * @param {Widget} parent
     * @param {Object} options
     * @param {Object} record edited record with updated value
     * @param {Object} changes changes registered by the list controller
     * @param {number} changes.all amount of selected records
     * @param {string} changes.field name of the field as displayed by the renderer
     * @param {string} changes.node technical name of the node
     * @param {number} changes.valid amount of valid records
     */
    init(parent, options, record, changes) {
        Object.assign(options, {
            buttons: options.buttons || [
                {
                    text: _t("Ok"),
                    classes: 'btn-primary',
                    close: true,
                    click: options.confirm_callback,
                },
                {
                    text: _t("Cancel"),
                    close: true,
                    click: options.cancel_callback,
                },
            ],
            $content: $(qweb.render('ListView.confirmModal', { changes })),
            size: options.size || 'medium',
            title: options.title || _t("Confirmation"),
            onForceClose: options.cancel_callback,
        });

        this._super(parent, options);

        const Widget = record.fieldsInfo.list[changes.node].Widget;
        this.fieldWidget = new Widget(this, changes.node, record, {
            mode: 'readonly',
            viewType: 'list',
            noOpen: true,
        });
    },

    /**
     * @override
     */
    willStart: function () {
        this.fieldWidget._widgetRenderAndInsert(() => { }).then(() => {
            this.$content.find('.o_changes_widget').replaceWith(this.fieldWidget.$el);
        });
        return this._super.apply(this, arguments);
    },
});

return ListConfirmDialog;

});
