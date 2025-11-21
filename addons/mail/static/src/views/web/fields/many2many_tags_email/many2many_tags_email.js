import { RecipientTag, useRecipientChecker } from "@mail/core/web/recipient_tag";
import { parseEmail } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class FieldMany2ManyTagsEmailMany2xAutocomplete extends Many2XAutocomplete {
    /**
     * @override
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
        ...super.components,
        Tag: RecipientTag,
        Many2XAutocomplete: FieldMany2ManyTagsEmailMany2xAutocomplete,
    };
    static props = {
        ...super.props,
        context: { type: Object, optional: true },
        canEditTags: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        if (this.quickCreate) {
            this.quickCreate = this.quickCreateRecipient.bind(this);
        }

        this.recipientCheckerBus = useRecipientChecker(() =>
            this.tags.map((tag) => ({ id: tag.id, email: tag.props.email }))
        );

        const update = this.update;
        this.update = async (object) => {
            await update(object);
        };
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
        tags.forEach((tag) => {
            tag.props.email = emailByResId[tag.props.resId];
        });
        return tags;
    }

    /**
     * @override
     * @param {Record} record
     * @returns {Object}
     */
    getTagProps(record) {
        const p = super.getTagProps(record);
        return {
            ...p,
            text:
                record.data.name || record.data.email || record.data.display_name || _t("Unnamed"),
            bus: this.recipientCheckerBus,
            updateRecipient: this.updateRecipient.bind(this),
            name: p.text,
            email: record.data.email,
            tooltip: record.data.email || p.text,
            id: record.id,
            resId: record.resId,
        };
    }

    async quickCreateRecipient(request) {
        const [name, email] = parseEmail(request);
        const [partnerId] = await this.orm.create("res.partner", [{ name, email }]);
        return this.props.record.data[this.props.name].addAndRemove({ add: [partnerId] });
    }

    async updateRecipient(newEmail, partnerId) {
        const list = this.props.record.data[this.props.name];
        const partnerRecord = list.records.find((r) => r.resId === partnerId);
        partnerRecord.canSaveOnUpdate = true;
        return partnerRecord.update({ email: newEmail }, { save: true });
    }
}

export const fieldMany2ManyTagsEmail = {
    ...many2ManyTagsField,
    component: FieldMany2ManyTagsEmail,
    supportedOptions: [
        ...many2ManyTagsField.supportedOptions.filter((option) => option.name !== "color_field"),
    ],
    relatedFields: (fieldInfo) => [
        ...many2ManyTagsField.relatedFields(fieldInfo),
        { name: "email", type: "char", readonly: false },
        { name: "name", type: "char" },
    ],
    additionalClasses: ["o_field_many2many_tags"],
};

registry.category("fields").add("many2many_tags_email", fieldMany2ManyTagsEmail);
