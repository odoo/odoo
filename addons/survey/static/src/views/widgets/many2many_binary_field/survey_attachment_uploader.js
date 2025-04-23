import { registry } from "@web/core/registry";
import { Many2ManyBinaryField, many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";

export class SurveyAttachmentUploader extends Many2ManyBinaryField {
    static template = "survey.SurveyAttachmentUploader";
}

export const surveyAttachmentUploader = {
    ...many2ManyBinaryField,
    component: SurveyAttachmentUploader,
};

registry.category("fields").add("survey_attachment_uploader", surveyAttachmentUploader);
