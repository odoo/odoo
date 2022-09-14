/** @odoo-module */

import { QuestionPageListRenderer } from "./question_page_list_renderer";
import { registry } from "@web/core/registry";
import { useOpenX2ManyRecord, useX2ManyCrud } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

const { useSubEnv } = owl;

class QuestionPageOneToManyField extends X2ManyField {
    setup() {
        super.setup();
        useSubEnv({
            openRecord: (record) => this.openRecord(record),
        });
        this.notificationService = useService("notification");

        // Systematically and automatically save SurveyForm at each question edit/creation
        // enables checking validation parameters consistency and using questions as triggers
        // immediately during question creation.
        // Preparing everything in order to override `this._openRecord` below.
        const { saveRecord: superSaveRecord, updateRecord: superUpdateRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        const self = this;
        const saveRecord = async (record) => {
            const saveResponse = await superSaveRecord(record);
            try {
                await self.props.record.save({stayInEdition: true, throwOnError: true});
            } catch (error) {
                return self.handleSurveySaveError(error, record);
            }
            return saveResponse;
        };

        const updateRecord = async (record) => {
            const updateResponse = await superUpdateRecord(record);
            try {
                await self.props.record.save({stayInEdition: true, throwOnError: true});
            } catch (error) {
                return self.handleSurveySaveError(error);
            }
            return updateResponse;
        };

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord,
            updateRecord,
        });
        this._openRecord = async (params) => {
            if (!await self.props.record.save({ stayInEdition: true })) {
                // do not open question form as it won't be savable either.
                return;
            }
            if (params.record) {
                // Force synchronization of fields that depend on sequence
                // (allowed_triggering_question_ids, is_placed_before_trigger)
                // as records may have been re-ordered before opening this one.
                await params.record.load();
            }
            openRecord(params);
        };
    }

    /**
     * For convenience, we'll prevent closing the question form dialog and
     * stay in edit mode to make sure only valid records are saved. Therefore,
     * two things should be cared for in case of error occurring when saving
     * the question:
     *   * Remove erroneous question row added to the embedded list
     *   * Replace default error modal with a notification
     *
     *   @param {Error} error Error thrown when saving survey/question.
     *   @param {Record?} recordToDelete (optional) In case the error is
     *   thrown when saving a new question, it should be deleted from the
     *   list.
     */
    async handleSurveySaveError(error, recordToDelete) {
        error.event.preventDefault();
        if (recordToDelete) {
            const listRecord = this.list.records.find(r => r.__bm_handle__ === recordToDelete.__bm_handle__);
            await this.list.delete(listRecord.id);
        }
        this.notificationService.add(
            error.message.data.message, {
                title: this.env._t("Validation Error"),
                type: "danger"
            }
        );
        // Prevent closing the question form view
        return Promise.reject("Impossible to save survey, see error notification.");
    }
}
QuestionPageOneToManyField.components = {
    ...X2ManyField.components,
    ListRenderer: QuestionPageListRenderer,
};
QuestionPageOneToManyField.defaultProps = {
    ...X2ManyField.defaultProps,
    editable: "bottom",
};

registry.category("fields").add("question_page_one2many", QuestionPageOneToManyField);
