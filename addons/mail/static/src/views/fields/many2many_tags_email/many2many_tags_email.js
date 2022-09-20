/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { sprintf } from "@web/core/utils/strings";

import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";

const { onMounted, onWillUpdateProps } = owl;

export class FieldMany2ManyTagsEmailTagsList extends TagsList {}
FieldMany2ManyTagsEmailTagsList.template = "FieldMany2ManyTagsEmailTagsList";

export class FieldMany2ManyTagsEmail extends Many2ManyTagsField {
    setup() {
        super.setup();

        this.openedDialogs = 0;
        this.recordsIdsToAdd = [];
        this.openMany2xRecord = useOpenMany2XRecord({
            resModel: this.props.relation,
            activeActions: {
                canCreate: false,
                canCreateEdit: false,
                canWrite: true,
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
        const invalidRecords = props.value.records.filter((record) => !record.data.email);
        // Remove records with invalid data, open form view to edit those and readd them if they are updated correctly.
        const dialogDefs = [];
        for (const record of invalidRecords) {
            dialogDefs.push(this.openMany2xRecord({
                resId: record.resId,
                context: props.record.getFieldContext(this.props.name),
                title: sprintf(this.env._t("Edit: %s"), record.data.display_name),
            }));
        }
        this.openedDialogs += invalidRecords.length;
        const invalidRecordIds = invalidRecords.map(rec => rec.resId);
        if (invalidRecordIds.length) {
            this.props.value.replaceWith(props.value.currentIds.filter(id => !invalidRecordIds.includes(id)));
        }
        return Promise.all(dialogDefs).then(() => {
            this.openedDialogs -= invalidRecords.length;
            if (this.openedDialogs || !this.recordsIdsToAdd.length) {
                return;
            }
            props.value.add(this.recordsIdsToAdd, { isM2M: true });
            this.recordsIdsToAdd = [];
        });
    }

    get tags() {
        // Add email to our tags
        const tags = super.tags;
        const emailByResId = this.props.value.records.reduce((acc, record) => {
            acc[record.resId] = record.data.email;
            return acc;
        }, {});
        tags.forEach(tag => tag.email = emailByResId[tag.resId]);
        return tags;
    }
};

FieldMany2ManyTagsEmail.components = {
    ...FieldMany2ManyTagsEmail.components,
    TagsList: FieldMany2ManyTagsEmailTagsList,
};

FieldMany2ManyTagsEmail.fieldsToFetch = Object.assign({},
    Many2ManyTagsField.fieldsToFetch,
    {email: {name: 'email', type: 'char'}}
);
registry.category("fields").add("many2many_tags_email", FieldMany2ManyTagsEmail);

/* fieldsToFetch are retrieved from legacy widget.. */
import field_registry from 'web.field_registry';
import relational_fields from 'web.relational_fields';

var M2MTags = relational_fields.FieldMany2ManyTags;

var FieldMany2ManyTagsEmailLegacy = M2MTags.extend({
    fieldsToFetch: _.extend({}, M2MTags.prototype.fieldsToFetch, {
        email: {type: 'char'},
    }),
});

field_registry.add('many2many_tags_email', FieldMany2ManyTagsEmailLegacy);
