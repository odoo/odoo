import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsFieldColorEditable,
    many2ManyTagsFieldColorEditable,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { roundPrecision } from "@web/core/utils/numbers";
import { onWillUpdateProps } from "@odoo/owl";

export function getProductRelatedModel() {
    const field = this.props.record.fields[this.props.productField];
    // The widget is either used alongisde a product related field or either used in a product view.
    let resModel = field?.relation || this.props.record.resModel;
    if (!["product.product", "product.template"].includes(resModel)) {
        throw new Error(`The widget '${this.constructor.name}' (field '${this.props.name}') needs a 'product.product' or 'product.template' field. '${this.props.productField}' is used but is related to '${field?.relation}' model.`);
    }
    return resModel;
}

export class Many2XUomTagsAutocomplete extends Many2XAutocomplete {
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
            const context = { "active_test" : false };
            const product = await this.orm.searchRead(props.productModel, [["id", "=", props.productId]], ["uom_id"], { context });
            this.referenceUnit = (await this.orm.searchRead("uom.uom", [["id", "=", product[0].uom_id[0]]], ["name", "factor", "parent_path", "rounding"]))[0];
        }
    }

    async search(name) {
        let records = await this.orm.searchRead(
            this.props.resModel,
            [...this.props.getDomain(), ["name", "ilike", name]],
            ["id", "display_name", "relative_factor", "factor", "relative_uom_id", "parent_path"],
        );
        const hasCommonReference = (uom1, uom2) => {
            const uom1Path = uom1.parent_path.split("/");
            const uom2Path = uom2.parent_path.split("/");
            return uom1Path[0] === uom2Path[0];
        };
        records = records.map((record) => {
            let relativeInfo = this.referenceUnit && this.referenceUnit.id !== record.id ? `${roundPrecision((this.props.productQuantity || 1) * record.factor / this.referenceUnit.factor, this.referenceUnit.rounding)} ${this.referenceUnit.name}` : "";
            if (
                this.referenceUnit &&
                record.id !== this.referenceUnit.id &&
                hasCommonReference(record, this.referenceUnit) &&
                record.relative_uom_id
            ) {
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
        ...Many2ManyTagsFieldColorEditable.defaultProps,
        productField: "product_id",
        quantityField: "product_uom_qty",
    }

    async setup() {
        super.setup();
        this.productModel = getProductRelatedModel.call(this);
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

registry.category("fields").add("many2many_uom_tags", many2ManyUomTagsField);
