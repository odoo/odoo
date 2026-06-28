import { props, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2XAutocomplete, many2XAutocompleteProps } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
    many2ManyTagsFieldProps,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { roundDecimals } from "@web/core/utils/numbers";

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
    props = props({
        ...many2XAutocompleteProps,
        productModel: t.string().optional(),
        productId: t.number().optional(),
        productQuantity: t.number().optional(),
    });

    async search(name) {
        let roundingDigitsPromise = null;
        let referenceUnitPromise = null;
        let records;

        const recordsPromise = this.orm.searchRead(
            this.props.resModel,
            [...this.props.getDomain(), ["name", "ilike", name]],
            ["id", "display_name", "relative_factor", "factor", "relative_uom_id", "parent_path"],
        ).then((res) => records = res);

        if (
            this.props.productModel &&
            this.props.productId &&
            (
                this.props.productModel !== this.currentProductModel ||
                this.props.productId !== this.currentProductId
            )
        ) {
            this.currentProductModel = this.props.productModel;
            this.currentProductId = this.props.productId;
            roundingDigitsPromise = this.orm.cache({ type: "disk" })
                .call("decimal.precision", "precision_get", ["Product Unit"])
                .then((res) => this.roundingDigits = res);
            referenceUnitPromise = this.orm.read(
                this.props.productModel, [this.props.productId], ["uom_id"], { context: { "active_test": false } }
            ).then((product) =>
                this.orm.cache({ type: "disk" }).read("uom.uom", [product[0].uom_id[0]], ["name", "factor", "parent_path"])
            ).then((res) => this.referenceUnit = res[0]);
        }

        await Promise.all([recordsPromise, roundingDigitsPromise, referenceUnitPromise]);

        const hasCommonReference = (uom1, uom2) => {
            const uom1Path = uom1.parent_path.split("/");
            const uom2Path = uom2.parent_path.split("/");
            return uom1Path[0] === uom2Path[0];
        };
        records = records.map((record) => {
            let relativeInfo = this.referenceUnit && this.referenceUnit.id !== record.id ? `${roundDecimals((this.props.productQuantity || 1) * record.factor / this.referenceUnit.factor, this.roundingDigits)} ${this.referenceUnit.name}` : "";
            if (
                this.referenceUnit &&
                record.id !== this.referenceUnit.id &&
                hasCommonReference(record, this.referenceUnit) &&
                record.relative_uom_id
            ) {
                relativeInfo = `${roundDecimals((this.props.productQuantity || 1) * record.relative_factor, this.roundingDigits)} ${record.relative_uom_id[1]}`;
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

export class Many2ManyUomTagsField extends Many2ManyTagsField {
    static template = "uom.Many2ManyUomTagsField";
    static components = {
        ...Many2ManyTagsField.components,
        Many2XAutocomplete: Many2XUomTagsAutocomplete,
    };
    props = props({
        ...many2ManyTagsFieldProps,
        productField: t.string().optional("product_id"),
        quantityField: t.string().optional("product_uom_qty"),
    });

    async setup() {
        super.setup();
        this.productModel = getProductRelatedModel.call(this);
    }
}

export const many2ManyUomTagsField = {
    ...many2ManyTagsField,
    component: Many2ManyUomTagsField,
    additionalClasses: ['o_field_many2many_tags'],
    supportedOptions: [
        ...many2ManyTagsField.supportedOptions.filter((option) => option.name !== "color_field"),
        {
            label: _t("Product Field Name"),
            name: "product_field",
            type: "field",
            availableTypes: ["many2one"],
        },
        {
            label: _t("Quantity Field Name"),
            name: "quantity_field",
            type: "field",
            availableTypes: ["many2one"],
        },
    ],
    extractProps({ options }) {
        const props = many2ManyTagsField.extractProps(...arguments);
        props.productField = options.product_field;
        props.quantityField = options.quantity_field;
        return props;
    },
};

registry.category("fields").add("many2many_uom_tags", many2ManyUomTagsField);
