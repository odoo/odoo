/** @odoo-module */
import AbstractService from 'web.AbstractService';
import core from 'web.core';

/**
 * This service store data from non-knowledge form view records that can be used
 * by a Knowledge form view.
 *
 * A typical usage could be the following:
 * - A form view is loaded and one field of the current record is a match for
 *   Knowledge @see FormController @see FormRenderer
 *   - Information about this record and how to access its form view is stored
 *     in this @see KnowledgeService .
 * - A knowledge Article is opened and it contains a @see TemplateToolbar .
 *   - When the toolbar is injected (@see FieldHtmlInjector ) in the view, it
 *     asks this @see KnowledgeService if the record can be interacted with.
 *   - if there is one such record, the related buttons are displayed in the
 *     toolbar.
 * - When one such button is used, the form view of the record is reloaded
 *   @see KnowledgeMacro and the button action is executed through a @see Macro
 *   - an exemple of macro action would be copying the template contents as the
 *     value of a field_html of the record, such as "description"
 *
 * Scope of the service:
 * It is meant to be called on 3 occasions:
 * 1) by @see FormController :
 *        It will only be called if the viewed record can be used within the
 *        Knowledge module. Such a record should have a chatter in its form
 *        view, or have at least one field in a whitelist specified in the
 *        controller.
 * 2) by @see FormRenderer :
 *        It will only be called if the viewed record has a field match in the
 *        whitelist of the controller. The renderer has to verify that the
 *        field's container is visible to the user (so that the field can be
 *        interacted with).
 * 3) by @see KnowledgeToolbar :
 *        It will be called by a toolbar to check whether it has a record that
 *        can be interacted with in the context of the toolbar (withChatter or
 *        withHtmlField).
 */
const KnowledgeService = AbstractService.extend({
    /**
     * @override
     */
    start() {
        this._super.apply(...arguments);
        this._records = new Set();
        this._lastVisitedRecordWithChatter = null;
        this._lastVisitedRecordWithHtmlField = null;
        /**
         * Some records are added by the controller but need to be validated by
         * the renderer. They are stored in this stack until the rendering is
         * done.
         */
        this._toValidateStackWithHtmlField = [];
    },
    /**
     * Called by the controller to indicate that a record need to be validated
     * by the renderer @see FormController
     *
     * @param {Object} record
     */
    pushToValidateWithHtmlField(record) {
        if (record && record.fieldNames.length) {
            this._toValidateStackWithHtmlField.push(record);
        }
    },
    /**
     * Called by the renderer to validate a record @see FormRenderer
     *
     * @returns {Object}
     */
    popToValidateWithHtmlField() {
        return this._toValidateStackWithHtmlField.pop();
    },
    /**
     * Called when a record may be used by a Knowledge form view.
     *
     * @param {Object} record
     */
    registerRecord(record) {
        if (!record) {
            return;
        }
        this._records.add(record);
        if (record.withChatter) {
            /**
             * if the record is flagged "withChatter", overwrite the previously
             * registered record
             */
            this._lastVisitedRecordWithChatter = record;
        }
        if (record.withHtmlField) {
            /**
             * if the record is flagged "withHtmlField", reset the stack and
             * the previously registered record
             */
            this._toValidateStackWithHtmlField = [];
            this._lastVisitedRecordWithHtmlField = record;
        }
    },
    /**
     * Remove a record to signify that it can not be used by a Knowledge form
     * view anymore.
     *
     * @param {Object} record
     */
    unregisterRecord(record) {
        this._records.delete(record);
    },
    /**
     * Recover a record that is able to interact with the chatter
     *
     * @returns {Object}
     */
    getAvailableRecordWithChatter() {
        if (this._lastVisitedRecordWithChatter && !this._lastVisitedRecordWithChatter.withChatter) {
            this._records.delete(this._lastVisitedRecordWithChatter);
        }
        if (!this._records.has(this._lastVisitedRecordWithChatter)) {
            this._lastVisitedRecordWithChatter = null;
        }
        return this._lastVisitedRecordWithChatter;
    },
    /**
     * Recover a record that has an available field_html
     *
     * @returns {Object}
     */
    getAvailableRecordWithHtmlField() {
        if (this._lastVisitedRecordWithHtmlField && !this._lastVisitedRecordWithHtmlField.withHtmlField) {
            this._records.delete(this._lastVisitedRecordWithHtmlField);
        }
        if (!this._records.has(this._lastVisitedRecordWithHtmlField)) {
            this._lastVisitedRecordWithHtmlField = null;
        }
        return this._lastVisitedRecordWithHtmlField;
    },
    /**
     * Recover a copy of the set of the currently registered records
     *
     * @returns {Set}
     */
    getRecords() {
        return new Set(this._records);
    },
});

core.serviceRegistry.add('knowledgeService', KnowledgeService);

export default KnowledgeService;
