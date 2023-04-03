/* @odoo-module */

import { registry } from "@web/core/registry";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { sprintf } from "@web/core/utils/strings";

import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TagsList } from "@web/core/tags_list/tags_list";
import { _t } from "@web/core/l10n/translation";

import { onMounted, onWillUpdateProps } from "@odoo/owl";

export class FieldMany2ManyTagsEmailTagsList extends TagsList {}
FieldMany2ManyTagsEmailTagsList.template = "FieldMany2ManyTagsEmailTagsList";

export class FieldMany2ManyTagsEmail extends Many2ManyTagsField {
    static props = {
        ...Many2ManyTagsField.props,
        context: { type: Object, optional: true },
    };

    setup() {
        super.setup();

        this.openedDialogs = 0;
        this.recordsIdsToAdd = [];
        this.openMany2xRecord = useOpenMany2XRecord({
            resModel: this.relation,
            activeActions: {
                create: false,
                createEdit: false,
                write: true,
            },
            isToMany: true,
            onRecordSaved: async (record) => {
                if (record.data.email) {
                    this.recordsIdsToAdd.push(record.resId);
                }
            },
            fieldString: this.props.string,
        });

        // Using onWillStart causes an infinite loop, onMounted will handle the initial
        // check and onWillUpdateProps handles any addition to the field.
        onMounted(this.checkEmails.bind(this, this.props));
        onWillUpdateProps(this.checkEmails.bind(this));
    }

    async checkEmails(props) {
        const invalidRecords = props.record.data[props.name].records.filter(
            (record) => !record.data.email
        );
        // Remove records with invalid data, open form view to edit those and readd them if they are updated correctly.
        const dialogDefs = [];
        for (const record of invalidRecords) {
            dialogDefs.push(
                this.openMany2xRecord({
                    resId: record.resId,
                    context: props.context,
                    title: sprintf(_t("Edit: %s"), record.data.display_name),
                })
            );
        }
        this.openedDialogs += invalidRecords.length;
        const invalidRecordIds = invalidRecords.map((rec) => rec.resId);
        if (invalidRecordIds.length) {
            this.props.record.data[this.props.name].replaceWith(
                props.record.data[props.name].currentIds.filter(
                    (id) => !invalidRecordIds.includes(id)
                )
            );
        }
        return Promise.all(dialogDefs).then(() => {
            this.openedDialogs -= invalidRecords.length;
            if (this.openedDialogs || !this.recordsIdsToAdd.length) {
                return;
            }
            props.record.data[props.name].add(this.recordsIdsToAdd, { isM2M: true });
            this.recordsIdsToAdd = [];
        });
    }

    get tags() {
        // Add email to our tags
        const tags = super.tags;
        const emailByResId = this.props.record.data[this.props.name].records.reduce(
            (acc, record) => {
                acc[record.resId] = record.data.email;
                return acc;
            },
            {}
        );
        tags.forEach((tag) => (tag.email = emailByResId[tag.resId]));
        return tags;
    }
}

FieldMany2ManyTagsEmail.components = {
    ...FieldMany2ManyTagsEmail.components,
    TagsList: FieldMany2ManyTagsEmailTagsList,
};

export const fieldMany2ManyTagsEmail = {
    ...many2ManyTagsField,
    component: FieldMany2ManyTagsEmail,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2ManyTagsField.extractProps(...arguments);
        props.context = dynamicInfo.context;
        return props;
    },
    relatedFields: (fieldInfo) => {
        return [...many2ManyTagsField.relatedFields(fieldInfo), { name: "email", type: "char" }];
    },
    additionalClasses: ["o_field_many2many_tags"],
};

registry.category("fields").add("many2many_tags_email", fieldMany2ManyTagsEmail);
