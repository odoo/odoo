import {
    many2ManyTagsFieldColorEditable,
    Many2ManyTagsFieldColorEditable,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useService } from "@web/core/utils/hooks";

export class FieldMany2ManyTagsSalaryBankTagsList extends TagsList {
    static template = "web.TagsList";
}

export class FieldMany2ManyTagsSalaryBank extends Many2ManyTagsFieldColorEditable {
    static template = "web.Many2ManyTagsField";
    static components = {
        ...Many2ManyTagsFieldColorEditable.components,
        TagsList: FieldMany2ManyTagsSalaryBankTagsList,
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
        const parentOpenMany2xRecord = this.openMany2xRecord;
        this.openMany2xRecord = async (...args) => {
            const result = await parentOpenMany2xRecord(...args);
            const isDirty = await this.props.record.model.root.isDirty();
            if (isDirty) {
                await this.props.record.model.root.save();
            }
            await this.props.record.load();
            return result;
        };
    }

    getTagProps(record) {
        var text = record.data?.display_name;
        const amount = record.data?.employee_salary_amount;
        const has_multiple_bank_accounts = this.props.record.data["has_multiple_bank_accounts"];
        if (has_multiple_bank_accounts && amount) {
            const symbol = record.data?.currency_symbol;
            if (record.data?.employee_salary_amount_is_percentage) {
                text =
                    (amount && amount <= 100 ? `(${amount.toFixed(0)}%) ` : "") +
                    record.data?.display_name;
            } else if (amount) {
                text = `(${amount.toFixed(2)}${symbol ? symbol : ""}) ` + record.data?.display_name;
            }
        }
        return {
            ...super.getTagProps(record),
            text,
        };
    }
}

export const fieldMany2ManyTagsSalaryBank = {
    ...many2ManyTagsFieldColorEditable,
    component: FieldMany2ManyTagsSalaryBank,
    relatedFields: () => [
        { name: "employee_salary_amount" },
        { name: "employee_salary_amount_is_percentage" },
        { name: "display_name" },
        { name: "currency_symbol" },
    ],
    additionalClasses: [
        ...(many2ManyTagsFieldColorEditable.additionalClasses || []),
        "o_field_many2many_tags",
    ],
    extractProps({ options, attrs, string, placeholder }, dynamicInfo) {
        const props = many2ManyTagsFieldColorEditable.extractProps(
            { options, attrs, string, placeholder },
            dynamicInfo
        );
        props.nameCreateField = "acc_number";
        return props;
    },
};

registry.category("fields").add("many2many_tags_salary_bank", fieldMany2ManyTagsSalaryBank);
