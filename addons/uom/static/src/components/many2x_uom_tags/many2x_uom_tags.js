import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsFieldColorEditable,
    many2ManyTagsFieldColorEditable,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import {
    Many2OneField,
    many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { UomAutoComplete } from "@uom/components/uom_autocomplete/uom_autocomplete";
import { roundPrecision } from "@web/core/utils/numbers";
import { onWillUpdateProps } from "@odoo/owl";

export class Many2XUomTagsAutocomplete extends Many2XAutocomplete {
    static components = {
        ...Many2XAutocomplete.components,
        AutoComplete: UomAutoComplete,
    };
    static props = {
        ...Many2XAutocomplete.props,
        productModel: { type: String, optional: true },
        productId: { type: Number, optional: true },
        productQuantity: { type: Number, optional: true },
    };

    async setup() {
        super.setup();
        onWillUpdateProps(async (nextProps) => {
            if (nextProps.productModel !== this.props.productModel || 
                nextProps.productId !== this.props.productId
            ) {
                await this.updateReferenceUnit(nextProps);
            }
        });
        await this.updateReferenceUnit();
    }

    async updateReferenceUnit(props = this.props) {
        if (props.productModel && props.productId) {
            const product = await this.orm.searchRead(props.productModel, [["id", "=", props.productId]], ["uom_id"]);
            this.referenceUnit = (await this.orm.searchRead("uom.uom", [["id", "=", product[0].uom_id[0]]], ["name", "factor", "parent_path", "rounding"]))[0];
        }
    }

    async search(name) {
        let records = await this.orm.searchRead(
            this.props.resModel,
            [...this.props.getDomain(), ["name", "ilike", name]],
            ["id", "name", "relative_factor", "factor", "relative_uom_id", "parent_path"],
        );
        const hasCommonReference = (uom1, uom2) => {
            const uom1Path = uom1.parent_path.split("/");
            const uom2Path = uom2.parent_path.split("/");
            return uom1Path[0] === uom2Path[0];
        };
        records = records.map((record) => {
            let relativeInfo = this.referenceUnit && this.referenceUnit.id !== record.id ? `${roundPrecision((this.props.productQuantity || 1) * record.factor / this.referenceUnit.factor, this.referenceUnit.rounding)} ${this.referenceUnit.name}` : "";
            if (this.referenceUnit && record.id !== this.referenceUnit.id && hasCommonReference(record, this.referenceUnit)) {
                relativeInfo = `${roundPrecision((this.props.productQuantity || 1) * record.relative_factor, this.referenceUnit.rounding)} ${record.relative_uom_id[1]}`;
            }
            return {
                ...record,
                relative_info: relativeInfo,
            };
        });
        if (this.referenceUnit) {
            records.sort((a, b) => hasCommonReference(a, this.referenceUnit) ? -1 : hasCommonReference(b, this.referenceUnit) ? 1 : 0);
        }
        return records;
    }

    mapRecordToOption(result) {
        return {
            value: result.id,
            label: result.name ? result.name.split("\n")[0] : _t("Unnamed"),
            displayName: result.name,
            relative_info: result.relative_info,
        };
    }
}

export class Many2ManyUomTagsField extends Many2ManyTagsFieldColorEditable {
    static template = "uom.Many2ManyUomTagsField";
    static components = {
        ...Many2ManyTagsFieldColorEditable.components,
        Many2XAutocomplete: Many2XUomTagsAutocomplete,
    };
    static props = {
        ...Many2ManyTagsFieldColorEditable.props,
        productField: { type: String, optional: true },
        quantityField: { type: String, optional: true },
    }
    static defaultProps = {
        ...Many2OneField.defaultProps,
        productField: "product_id",
        quantityField: "product_uom_qty",
    }
}

export class Many2OneUomField extends Many2OneField {
    static template = "uom.Many2OneUomField";
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: Many2XUomTagsAutocomplete,
    };
    static props = {
        ...Many2OneField.props,
        productField: { type: String, optional: true },
        quantityField: { type: String, optional: true },
    }
    static defaultProps = {
        ...Many2OneField.defaultProps,
        productField: "product_id",
        quantityField: "product_uom_qty",
    }
}   

export const many2ManyUomTagsField = {
    ...many2ManyTagsFieldColorEditable,
    component: Many2ManyUomTagsField,
    additionalClasses: ['o_field_many2many_tags'],
    supportedOptions: [
        ...(many2ManyTagsFieldColorEditable.supportedOptions || []),
        {
            label: _t("Product Field Name"),
            name: "product_field",
            type: "field",
            availableTypes: ["many2one"]
        },
        {
            label: _t("Quantity Field Name"),
            name: "quantity_field",
            type: "field",
            availableTypes: ["many2one"]
        }
    ],
    extractProps({ options }) {
        const props = many2ManyTagsFieldColorEditable.extractProps(...arguments);
        props.productField = options.product_field;
        props.quantityField = options.quantity_field;
        return props;
    },
};

export const many2OneUomField = {
    ...many2OneField,
    component: Many2OneUomField,
    additionalClasses: ['o_field_many2one'],
    supportedOptions: [
        ...(many2OneField.supportedOptions || []),
        {
            label: _t("Product Field Name"),
            name: "product_field",
            type: "field",
            availableTypes: ["many2one"]
        },
        {
            label: _t("Quantity Field Name"),
            name: "quantity_field",
            type: "field",
            availableTypes: ["many2one"]
        }
    ],
    extractProps({ options }) {
        const props = many2OneField.extractProps(...arguments);
        props.productField = options.product_field;
        props.quantityField = options.quantity_field;
        return props;
    },
};

registry.category("fields").add("many2many_uom_tags", many2ManyUomTagsField);
registry.category("fields").add("many2one_uom", many2OneUomField);
