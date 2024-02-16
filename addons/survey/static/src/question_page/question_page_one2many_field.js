import { _t } from "@web/core/l10n/translation";
import { QuestionPageListRenderer } from "./question_page_list_renderer";
import { registry } from "@web/core/registry";
import { useOpenX2ManyRecord, useX2ManyCrud } from "@web/views/fields/relational_utils";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useSubEnv } from "@odoo/owl";

/**
 * For convenience, we'll prevent closing the question form dialog and
 * stay in edit mode to make sure only valid records are saved. Therefore,
 * in case of error occurring when saving we will replace default error
 * modal with a notification.
 */

class SurveySaveError extends Error {}
function SurveySaveErrorHandler(env, error, originalError) {
    if (originalError instanceof SurveySaveError) {
        env.services.notification.add(originalError.message, {
            title: _t("Validation Error"),
            type: "danger",
        });
        return true;
    }
}
registry
    .category("error_handlers")
    .add("surveySaveErrorHandler", SurveySaveErrorHandler, { sequence: 10 });

class QuestionPageOneToManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: QuestionPageListRenderer,
    };
    static defaultProps = {
        ...X2ManyField.defaultProps,
        editable: "bottom",
    };
    setup() {
        super.setup();
        useSubEnv({
            openRecord: (record) => this.openRecord(record),
        });

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
            await superSaveRecord(record);
            try {
                await self.props.record.save();
            } catch (error) {
                // In case of error occurring when saving.
                // Remove erroneous question row added to the embedded list
                await this.list.delete(record);
                throw new SurveySaveError(error.data.message);
            }
        };

        const updateRecord = async (record) => {
            await superUpdateRecord(record);
            try {
                await self.props.record.save();
            } catch (error) {
                throw new SurveySaveError(error.data.message);
            }
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
            const { record, name } = this.props;
            if (!await record.save()) {
                // do not open question form as it won't be savable either.
                return;
            }
            if (params.record) {
                params.record = record.data[name].records.find(r => r.resId === params.record.resId);
            }
            await openRecord(params);
        };
        this.canOpenRecord = true;
    }
}

export const questionPageOneToManyField = {
    ...x2ManyField,
    component: QuestionPageOneToManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
    
};

registry.category("fields").add("question_page_one2many", questionPageOneToManyField);
