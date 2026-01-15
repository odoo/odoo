import { RecipientsInputTagsList } from "@mail/core/web/recipients_input_tags_list";
import { RecipientsPopover } from "@mail/core/web/recipients_popover";
import { parseEmail } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class FieldMany2ManyTagsEmailTagsList extends RecipientsInputTagsList {
    static template = "FieldMany2ManyTagsEmailTagsList";
}

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
        ...FieldMany2ManyTagsEmail.components,
        TagsList: FieldMany2ManyTagsEmailTagsList,
        Many2XAutocomplete: FieldMany2ManyTagsEmailMany2xAutocomplete,
    };
    static props = {
        ...Many2ManyTagsField.props,
        context: { type: Object, optional: true },
        canEditTags: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        if (this.quickCreate) {
            this.quickCreate = this.quickCreateRecipient.bind(this);
        }
        this.openedDialogs = 0;
        this.recordsIdsToAdd = [];

        this.recipientsPopover = usePopover(RecipientsPopover);
        this.actionService = useService("action");

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
            tag.email = emailByResId[tag.resId];
            tag.name = tag.text;
            tag.title = tag.text;
        });
        return tags;
    }

    /**
     * @override
     * @param {Record} record
     * @returns {Object}
     */
    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            text:
                record.data.name || record.data.email || record.data.display_name || _t("Unnamed"),
            onClick: (ev) => this.onTagClick(ev, record),
        };
    }

    /**
     * @param {Event} event
     * @param {Record} record
     */
    onTagClick(event, record) {
        const viewProfileBtnOverride = () => {
            const action = {
                type: "ir.actions.act_window",
                res_model: "res.partner",
                res_id: record.resId,
                views: [[false, "form"]],
                target: "current",
            };
            this.actionService.doAction(action);
        };
        this.recipientsPopover.open(event.target, {
            id: record.resId,
            viewProfileBtnOverride,
        });
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
        ...many2ManyTagsField.supportedOptions,
        {
            label: _t("Edit Tags"),
            name: "edit_tags",
            type: "boolean",
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
        { name: "email", type: "char", readonly: false },
        { name: "name", type: "char" },
    ],
    additionalClasses: ["o_field_many2many_tags"],
};

registry.category("fields").add("many2many_tags_email", fieldMany2ManyTagsEmail);
