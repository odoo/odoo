/** @odoo-module */

import { QuestionPageListRenderer } from "./question_page_list_renderer";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
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

        // Systematically and automatically save SurveyForm at each question edit/creation mainly
        // enables allows checking validation parameters consistency and use questions as triggers
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
            if (!await self.props.record.save({stayInEdition: true})) {
                return;
            }
            const activeElement = document.activeElement;
            if (params.record) {
                // Trigger loading for values that may have changed when reordering/deleting
                // rows (allowed_triggering_question_ids, is_conditional, is_placed_before_trigger).
                await params.record.load();
            }
            openRecord({
                ...params,
                onClose: () => {
                    if (activeElement) {
                        activeElement.focus();
                    }
                },
            });
        };
    }

    /**
     * As it is convenient to keep the questions modal open, two things should
     * be cared for in case of error while saving the form after adding or
     * updating a question:
     *   * Remove erroneous question row added
     *   * Replace default error modal with a notification
     *
     *   @param {Error} error Error thrown when saving survey/question.
     *   @param {Record} recordToDelete (optional) In case the error is
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
        return Promise.reject(_lt("Impossible to save survey, see error notification."));
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
