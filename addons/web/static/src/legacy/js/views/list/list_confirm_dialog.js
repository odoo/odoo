/** @odoo-module alias=web.ListConfirmDialog **/

import core from 'web.core';
import Dialog from 'web.Dialog';
import FieldWrapper from 'web.FieldWrapper';
import { WidgetAdapterMixin } from 'web.OwlCompatibility';
import utils from 'web.utils';

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
     * @param {Object} params
     * @param {Object} params.isDomainSelected true iff the user selected the
     *   whole domain
     * @param {string} params.fields list of field names and labels
     * @param {number} params.nbRecords number of records (total)
     * @param {number} params.nbValidRecords number of valid records
     * @param {Object} [options]
     */
    init: function (parent, record, params, options) {
        options = Object.assign({}, options, {
            $content: $(qweb.render('ListView.confirmModal', params)),
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

        this.fieldWidgets = params.fields.map(({ name }) => {
            const Widget = record.fieldsInfo.list[name].Widget;
            const widgetOptions = {
                mode: 'readonly',
                viewType: 'list',
                noOpen: true,
            };
            if (!utils.isComponent(Widget)) {
                return {
                    isLegacyWidget: true,
                    fieldWidget: new Widget(this, name, record, widgetOptions),
                };
            } else {
                return {
                    isLegacyWidget: false,
                    fieldWidget: new FieldWrapper(this, Widget, {
                        fieldName: name,
                        record,
                        options: widgetOptions,
                    }),
                };
            }
        });
    },
    /**
     * @override
     */
    willStart: function () {
        const proms = this.fieldWidgets.map(({ isLegacyWidget, fieldWidget }) => {
            if (isLegacyWidget) {
                return fieldWidget._widgetRenderAndInsert(function () {});
            } else {
                return fieldWidget.mount(document.createDocumentFragment());
            }
        });
        proms.push(this._super.apply(this, arguments));
        return Promise.all(proms);
    },
    /**
     * @override
     */
    start: function () {
        this.fieldWidgets.forEach(({ fieldWidget }) => {
            this.$content.find(`.o_changes_widget[data-name=${fieldWidget.name}]`).replaceWith(fieldWidget.$el);
            fieldWidget.el.style.pointerEvents = 'none';
        });
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

export default ListConfirmDialog;
