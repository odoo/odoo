import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/**
 * Many2ManyTagsField with tag selection and options ordered by sequence
 */
export class Many2ManyTagsFieldWithSequence extends Many2ManyTagsField {
    static props = {
        ...Many2ManyTagsField.props,
        sequenceField: { type: String },
    };
    static template = "survey.Many2ManyTagsFieldWithSequence";

    getTagProps(record) {
        return Object.assign(super.getTagProps(record), {
            sequence: record.data[this.props.sequenceField],
        });
    }
}

export const many2ManyTagsFieldWithSequence = {
    ...many2ManyTagsField,
    component: Many2ManyTagsFieldWithSequence,
    displayName: _t("Tags with sequence"),
    supportedOptions: [
        ...many2ManyTagsField.supportedOptions,
        {
            label: _t("Sequence field"),
            name: "sequence_field",
            availableTypes: ["integer"],
            help: _t("Set an integer field to order selected tags by sequence."),
        },
    ],
    relatedFields: ({ options }) => {
        const relatedFields = many2ManyTagsField.relatedFields({ options });
        if (options.sequence_field) {
            relatedFields.push({ name: options.sequence_field, type: "integer", readonly: false });
        }
        return relatedFields;
    },
    extractProps({ attrs, options, string }, dynamicInfo) {
        return {
            ...many2ManyTagsField.extractProps(...arguments),
            sequenceField: options.sequence_field,
        };
    },
};

registry.category("fields").add("many2many_tags_with_sequence", many2ManyTagsFieldWithSequence);
