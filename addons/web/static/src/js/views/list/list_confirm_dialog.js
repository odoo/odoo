odoo.define('web.ListConfirmDialog', function (require) {
"use strict";

const core = require('web.core');
const Dialog = require('web.Dialog');
const FieldWrapper = require('web.FieldWrapper');
const { WidgetAdapterMixin } = require('web.OwlCompatibility');
const utils = require('web.utils');

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
const ListConfirmDialog = Dialog.extend(WidgetAdapterMixin, {
    /**
     * @constructor
     * @override
     * @param {Widget} parent
     * @param {Object} record edited record with updated value
     * @param {Object} changes changes registered by the list controller
     * @param {Object} changes isDomainSelected true iff the user selected the
     *   whole domain
     * @param {string} changes.fieldLabel label of the changed field
     * @param {string} changes.fieldName technical name of the changed field
     * @param {number} changes.nbRecords number of records (total)
     * @param {number} changes.nbValidRecords number of valid records
     * @param {Object} [options]
     */
    init: function (parent, record, changes, options) {
        options = Object.assign({}, options, {
            $content: $(qweb.render('ListView.confirmModal', { changes })),
            buttons: options.buttons || [{
                text: _t("Ok"),
                classes: 'btn-primary',
                close: true,
                click: options.confirm_callback,
            }, {
                text: _t("Cancel"),
                close: true,
                click: options.cancel_callback,
            }],
            onForceClose: options.cancel_callback,
            size: options.size || 'medium',
            title: options.title || _t("Confirmation"),
        });

        this._super(parent, options);

        const Widget = record.fieldsInfo.list[changes.fieldName].Widget;
        const widgetOptions = {
            mode: 'readonly',
            viewType: 'list',
            noOpen: true,
        };
        this.isLegacyWidget = !utils.isComponent(Widget);
        if (this.isLegacyWidget) {
            this.fieldWidget = new Widget(this, changes.fieldName, record, widgetOptions);
        } else {
            this.fieldWidget = new FieldWrapper(this, Widget, {
                fieldName: changes.fieldName,
                record,
                options: widgetOptions,
            });
        }
    },
    /**
     * @override
     */
    willStart: function () {
        let widgetProm;
        if (this.isLegacyWidget) {
            widgetProm = this.fieldWidget._widgetRenderAndInsert(function () {});
        } else {
            widgetProm = this.fieldWidget.mount(document.createDocumentFragment());
        }
        return Promise.all([widgetProm, this._super.apply(this, arguments)]);
    },
    /**
     * @override
     */
    start: function () {
        this.$content.find('.o_changes_widget').replaceWith(this.fieldWidget.$el);
        this.fieldWidget.el.style.pointerEvents = 'none';
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        WidgetAdapterMixin.destroy.call(this);
        this._super();
    },
});

return ListConfirmDialog;

});
