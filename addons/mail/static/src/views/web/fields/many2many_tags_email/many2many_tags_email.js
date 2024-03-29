/* @odoo-module */

import { onMounted } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";

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

        const update = this.update;
        this.update = async (object) => {
            await update(object);
            await this.checkEmails();
        };

        onMounted(() => {
            this.checkEmails();
        });
    }

    async checkEmails() {
        const list = this.props.record.data[this.props.name];
        const invalidRecords = list.records.filter((record) => !record.data.email);
        // Remove records with invalid data, open form view to edit those and readd them if they are updated correctly.
        const dialogDefs = [];
        for (const record of invalidRecords) {
            dialogDefs.push(
                this.openMany2xRecord({
                    resId: record.resId,
                    context: this.props.context,
                    title: _t("Edit: %s", record.data.display_name),
                })
            );
        }
        this.openedDialogs += invalidRecords.length;
        await Promise.all(dialogDefs);

        this.openedDialogs -= invalidRecords.length;
        if (this.openedDialogs || !this.recordsIdsToAdd.length) {
            return;
        }

        const invalidRecordIds = invalidRecords.map((rec) => rec.resId);
        await list.addAndRemove({
            remove: invalidRecordIds.filter((id) => !this.recordsIdsToAdd.includes(id)),
            reload: true,
        });
        this.recordsIdsToAdd = [];
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
