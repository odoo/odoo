/** @odoo-module **/

import FormController from 'web.FormController';
import { Domain } from '@web/core/domain';

FormController.include({
    /**
     * Knowledge articles can interact with some records with the help of the
     * @see KnowledgeService. Those records need to have a field whose name is
     * in @see knowledgeTriggerFieldNames. This list is ordered and the first
     * match found in a record will take precedence. Once a match is found, it
     * is stored in the KnowledgeService to be accessed later by an article.
     *
     * @override
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.knowledgeRecordFieldNames = [
            'note', 'memo', 'description', 'comment', 'narration', 'additional_note', 'internal_notes', 'notes'
        ];
        if (this._isPotentialKnowledgeRecord()) {
            this._searchKnowledgeRecord();
        }
        if (this.ignoreKnowledgeRecordSearch) {
            this._unregisterObsoleteKnowledgeRecords(this.renderer.breadcrumbs);
        }
    },
    /**
     * Since Knowledge toolbars are cleaned before saving the record
     * @see KnowledgePlugin , the renderer needs to render them again once it is
     * done.
     *
     * @override
     * @param {string} recordID
     */
    saveRecord: async function (recordID) {
        const changedFields = this._super(...arguments);
        recordID = recordID || this.handle;
        if (recordID) {
            changedFields.then(() => {
                this.renderer.refreshFieldHtmlInjectors(recordID);
            });
        }
        return changedFields;
    },
    /**
     * Notify the @see KnowledgeService that the record was updated
     *
     * @override
     */
    update: async function (params, options) {
        await this._super(...arguments);
        if (this._isPotentialKnowledgeRecord()) {
            this._searchKnowledgeRecord();
        }
        if (this.ignoreKnowledgeRecordSearch) {
            this._unregisterObsoleteKnowledgeRecords(this.renderer.breadcrumbs);
        }
    },
    /**
     * Evaluate the provided breadcrumbs sequence against currently recorded
     * records in @see KnowledgeService to remove them if they are obsolete.
     * Breadcrumb information does not contain the res_id of the record for a
     * form view, and the actionService does not allow to access the breadcrumb
     * controller externally. This is why the full breadcrumb string sequence is
     * used here as an identifier.
     *
     * @param {Array} breadcrumbs
     * @param {boolean} revoke whether the record is deemed obsolete if a match
     *                         is found or not.
     */
    _unregisterObsoleteKnowledgeRecords: function (breadcrumbs, revoke = false) {
        const records = this.call('knowledgeService', 'getRecords');
        let isObsolete = revoke;
        for (let record of records) {
            if (record.breadcrumbs.length > breadcrumbs.length) {
                isObsolete = !revoke;
            } else {
                const slicedBreadcrumbs = breadcrumbs.slice(0, record.breadcrumbs.length);
                if (_.isEqual(slicedBreadcrumbs, record.breadcrumbs)) {
                    isObsolete = revoke;
                } else {
                    isObsolete = !revoke;
                }
            }
            if (isObsolete) {
                this.call('knowledgeService', 'unregisterRecord', record);
            }
        }
    },
    /**
     * Conditions for a record to be usable by a Knowledge article:
     * - The current view is not a Knowledge form
     * - has a ControlPanel which uses breadcrumbs
     * - is the result of an action
     * - displays an existing record (already stored in DB)
     * (saved new records will be registered upon @see update )
     */
    _isPotentialKnowledgeRecord: function () {
        return !this.ignoreKnowledgeRecordSearch && this.withControlPanel && this.controlPanelProps.withBreadcrumbs &&
            this.controlPanelProps.action && this.controlPanelProps.action.controllers &&
            this.handle && !this.model.localData[this.handle].isNew();
    },
    /**
     * @param {Object} record raw record
     * @param {string} modifier modifier as registered in the view (xml)
     * @returns {boolean} whether the domain includes this record
     */
    _readModifier: function (record, modifier) {
        if (!modifier) {
            // falsy modifier
            return false;
        }
        let value = false;
        try {
            // unaware of context
            const preDomain = new Domain(modifier);
            // aware of context
            const domain = new Domain(preDomain.toList(record.context));
            value = domain.contains(record.data);
        } catch (_error) {
            // truthy modifier
            return true;
        }
        return value;
    },
    /**
     * Evaluate the current record and notify @see KnowledgeService if it can or
     * could be used in a Knowledge article.
     *
     * @private
     */
    _searchKnowledgeRecord: function () {
        const record = this.model.get(this.handle, {raw: true});
        const controller = this.controlPanelProps.action.controllers.form;
        const breadcrumbs = this.controlPanelProps.breadcrumbs.slice();
        // add the current breadcrumbs information
        breadcrumbs.push({
            title: record.data.display_name,
            controllerID: controller.jsId,
        });
        /**
         * If the current potential record has exactly the same breadcrumbs
         * sequence as another record registered in the @see KnowledgeService,
         * the previous record should be unregistered here because this problem
         * will not be caught later, as the Knowledge form view only checks
         * whether its breadcrumbs sequence contains a record's breadcrumbs
         * sequence, regardless of the fact that the current potential record
         * may not have been registered in the service.
         *
         * This call could be omitted if the breadcrumbs would also store the
         * related res_id if any, but currently two records with the same
         * display name and model will have exactly the same breadcrumbs
         * information (controllerID and title).
         */
        this._unregisterObsoleteKnowledgeRecords(breadcrumbs, true);
        const hasMessageIds = this.renderer.chatterFields && this.renderer.chatterFields.hasMessageIds;
        const view = this.controlPanelProps.view;
        const fields = view.viewFields;
        const formFields = view.fieldsInfo.form;
        const knowledgeRecord = {
            res_id: record.res_id,
            res_model: view.model,
            breadcrumbs: breadcrumbs,
            fieldNames: [],
        };
        if (hasMessageIds) {
            knowledgeRecord.withChatter = true;
            this.call('knowledgeService', 'registerRecord', knowledgeRecord);
        }
        for (let fieldName of this.knowledgeRecordFieldNames) {
            if (fieldName in formFields && fields[fieldName].type === 'html' && !fields[fieldName].readonly) {
                const readonlyModifier = formFields[fieldName].modifiers.readonly;
                const invisibleModifier = formFields[fieldName].modifiers.invisible;
                if (this._readModifier(record, readonlyModifier) || this._readModifier(record, invisibleModifier)) {
                    continue;
                }
                knowledgeRecord.fieldNames.push({
                    name: fieldName,
                    string: fields[fieldName].string,
                });
            }
        }
        /**
         * While a field by itself can be visible and not readonly, its
         * group / notebook pane could be invisible. Another check will be done
         * after rendering to determine if any of the catched fields are in fact
         * usable by the user. @see FormRenderer
         */
        this.call('knowledgeService', 'pushToValidateWithHtmlField', knowledgeRecord);
    },
});
