import { onMounted } from "@odoo/owl";

import { parseEmail } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { useOpenMany2XRecord, Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class FieldMany2ManyTagsEmailTagsList extends TagsList {
    static template = "FieldMany2ManyTagsEmailTagsList";
}

export class FieldMany2ManyTagsEmailMany2xAutocomplete extends Many2XAutocomplete {
    /**
     * @param {string} value
     * @returns {Object}
     */
    getCreationContext(value) {
        const [name, email] = value ? parseEmail(value) : ["", ""];
        const context = super.getCreationContext(name);
        if (email) {
            context["default_email"] = email;
        }
        return context;
    }
}

export class FieldMany2ManyTagsEmail extends Many2ManyTagsField {
    static template = "FieldMany2ManyTagsEmailTags";
    static components = {
        ...FieldMany2ManyTagsEmail.components,
        TagsList: FieldMany2ManyTagsEmailTagsList,
        Many2XAutocomplete: FieldMany2ManyTagsEmailMany2xAutocomplete
    };
    static props = {
        ...Many2ManyTagsField.props,
        context: { type: Object, optional: true },
        canEditTags: { type: Boolean, optional: true }
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
                if (this.props.canEditTags) {
                    // Reload the tag list to update the display:
                    const list = this.props.record.data[this.props.name];
                    await list.addAndRemove({
                        add: [],
                        remove: [],
                        reload: true,
                    });
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
        if (!invalidRecords.length) {
            return;
        }
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
        if (this.openedDialogs) {
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

    /**
     * @override
     * @param {Record} record
     * @returns {Object}
     */
    getTagProps(record) {
        const props = super.getTagProps(record);
        props.onClick = (ev) => this.onTagClick(ev, record);
        return props;
    }

    /**
     * @param {Event} event
     * @param {Record} record
     */
    onTagClick(event, record) {
        if (this.props.canEditTags) {
            return this.openMany2xRecord({
                resId: record.resId,
                context: this.props.context,
                title: _t("Edit: %s", record.data.display_name),
            });
        }
    }
}

export const fieldMany2ManyTagsEmail = {
    ...many2ManyTagsField,
    component: FieldMany2ManyTagsEmail,
    supportedOptions: [
        ...many2ManyTagsField.supportedOptions,
        {
            label: _t("Edit Tags"),
            name: "edit_tags",
            type: "boolean",
            help: _t("If checked, clicking on the tag will open the form that allows to directly edit it."),
        },
    ],
    extractProps({ options, attrs }, dynamicInfo) {
        const props = many2ManyTagsField.extractProps(...arguments);
        props.context = dynamicInfo.context;
        const hasEditPermission = attrs.can_write ? evaluateBooleanExpr(attrs.can_write) : true;
        props.canEditTags = options.edit_tags ? hasEditPermission : false;
        return props;
    },
    relatedFields: (fieldInfo) => [
        ...many2ManyTagsField.relatedFields(fieldInfo),
        { name: "email", type: "char" },
    ],
    additionalClasses: ["o_field_many2many_tags"],
};

registry.category("fields").add("many2many_tags_email", fieldMany2ManyTagsEmail);
