import { registry } from "@web/core/registry";
import { Many2ManyBinaryField, many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";

export class SurveyAttachmentList extends Many2ManyBinaryField {
    static template = "survey.SurveyAttachmentList";
}

export const surveyAttachmentList = {
    ...many2ManyBinaryField,
    component: SurveyAttachmentList,
};

registry.category("fields").add("survey_attachment_list", surveyAttachmentList);
