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

        this.relatedFieldWidget = undefined;
        if (this.fieldWidget.attrs.widget === 'daterange' && changes.relatedFieldName) {
            const fieldName = changes.relatedFieldName;
            const fieldLabel = record.fields[fieldName].string;
            this.$content.find('table.o_modal_changes tbody').append(qweb.render('ListView.confirmModal.relatedField', { fieldLabel }));
            const RelatedWidget = record.fieldsInfo.list[fieldName].Widget;

            if (this.isLegacyWidget) { // the related widget is the same (= DateRange widget) then we don't need to recheck it
                this.relatedFieldWidget = new RelatedWidget(this, fieldName, record, widgetOptions);
            } else {
                this.relatedFieldWidget = new FieldWrapper(this, Widget, {
                    fieldName,
                    record,
                    options: widgetOptions,
                });
            }
        }
    },
    /**
     * @override
     */
    willStart: function () {
        const widgetPromises = [];
        if (this.isLegacyWidget) {
            widgetPromises.push(this.fieldWidget._widgetRenderAndInsert(function () {}));
            if (this.relatedFieldWidget) {
                widgetPromises.push(this.relatedFieldWidget._widgetRenderAndInsert(function () {}));
            }
        } else {
            widgetPromises.push(this.fieldWidget.mount(document.createDocumentFragment()));
            if (this.relatedFieldWidget) {
                widgetPromises.push(this.relatedFieldWidget.mount(document.createDocumentFragment()));
            }
        }
        return Promise.all([...widgetPromises, this._super.apply(this, arguments)]);
    },
    /**
     * @override
     */
    start: function () {
        this.$content.find('.o_changes_widget').replaceWith(this.fieldWidget.$el);
        this.fieldWidget.el.style.pointerEvents = 'none';
        if (this.relatedFieldWidget) {
            this.$content.find('.o_changes_related_widget').replaceWith(this.relatedFieldWidget.$el);
            this.relatedFieldWidget.el.style.pointerEvents = 'none';
        }
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
