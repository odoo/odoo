import {
    many2ManyTagsField,
    Many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted } from "@odoo/owl";

class BankTag extends Component {
    static template = "account.BankTag";
    static components = { BadgeTag };
    static props = ["allowOutPayment?", "color", "onClick", "onDelete", "onClick", "text"];
}

export class FieldMany2ManyTagsBanks extends Many2ManyTagsField {
    static template = "account.FieldMany2ManyTagsBanks";
    static components = {
        ...super.components,
        Tag: BankTag,
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
        onMounted(async () => {
            // Needed when you create a partner (from a move for example), we want the partner to be saved to be able
            // to have it as account holder
            const isDirty = await this.props.record.model.root.isDirty();
            if (isDirty) {
                this.props.record.model.root.save();
            }
        });
    }

    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            allowOutPayment: record.data?.allow_out_payment,
        };
    }

    openBanksListView() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Banks"),
            res_model: this.relation,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: this.getDomain(),
            target: "current",
        });
    }
}

export const fieldMany2ManyTagsBanks = {
    ...many2ManyTagsField,
    component: FieldMany2ManyTagsBanks,
    supportedOptions: [
        ...many2ManyTagsField.supportedOptions.filter((option) => option.name !== "color_field"),
        {
            label: _t("Allows out payments"),
            name: "allow_out_payment_field",
            type: "boolean",
        },
    ],
    additionalClasses: [
        ...(many2ManyTagsField.additionalClasses || []),
        "o_field_many2many_tags",
    ],
    relatedFields: ({ options }) => {
        return [
            ...many2ManyTagsField.relatedFields({ options }),
            { name: options.allow_out_payment_field, type: "boolean", readonly: false },
        ];
    },
};

registry.category("fields").add("many2many_tags_banks", fieldMany2ManyTagsBanks);
