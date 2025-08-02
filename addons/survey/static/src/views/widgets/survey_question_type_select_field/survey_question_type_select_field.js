import {
    BadgeSelectionWithFilterField,
    badgeSelectionFieldWithFilter,
} from "@web/views/fields/badge_selection_with_filter/badge_selection_field_with_filter";
import { registry } from "@web/core/registry";

export class SurveyQuestionTypeSelectField extends BadgeSelectionWithFilterField {
    static template = "survey.SurveyQuestionTypeSelectField";
    static icons = {
        simple_choice: "fa-list-ol",
        text_box: "fa-bars",
        char_box: "fa-minus",
        numerical_box: "fa-hashtag",
        scale: "fa-smile-o",
        date: "fa-calendar-o",
        datetime: "fa-calendar",
        time: "fa-clock-o",
        matrix: "fa-th",
    };

    setup() {
        super.setup();
        this.icons = SurveyQuestionTypeSelectField.icons;
    }

    get string() {
        if (!this.props.record.data[this.props.name]) {
            return "";
        }
        return this.props.record.data[this.props.name] === "multiple_choice"
            ? "simple_choice"
            : this.options.find((o) => o[0] === this.props.record.data[this.props.name])[1];
    }

    get value() {
        const rawValue = super.value;
        return rawValue === "multiple_choice" ? "simple_choice" : rawValue;
    }

    onChange(value) {
        if (value !== this.value) {
            this.props.record.update({ [this.props.name]: value });
        }
    }
}

export const surveyQuestionTypeSelectField = {
    ...badgeSelectionFieldWithFilter,
    component: SurveyQuestionTypeSelectField,
};

registry.category("fields").add("survey_question_type_select", surveyQuestionTypeSelectField);
