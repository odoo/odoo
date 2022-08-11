/** @odoo-module */

import { QuestionPageListRenderer } from "./question_page_list_renderer";
import { registry } from "@web/core/registry";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

class QuestionPageOneToManyField extends X2ManyField {}
QuestionPageOneToManyField.components = {
    ...X2ManyField.components,
    ListRenderer: QuestionPageListRenderer,
};
QuestionPageOneToManyField.defaultProps = {
    ...X2ManyField.defaultProps,
    editable: "bottom",
};

registry.category("fields").add("question_page_one2many", QuestionPageOneToManyField);
