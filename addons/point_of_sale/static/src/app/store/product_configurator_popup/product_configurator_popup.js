import { Dialog } from "@web/core/dialog/dialog";
import { Component, onMounted, useRef, useState, useSubEnv } from "@odoo/owl";
import { usePos } from "../pos_hook";
import { useRefListener, useService } from "@web/core/utils/hooks";
import { ProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";

export class BaseProductAttribute extends Component {
    static template = "";
    static props = ["attributeLine"];
    setup() {
        this.env.attribute_components.push(this);
        this.attributeLine = this.props.attributeLine;
        this.values = this.attributeLine.product_template_value_ids;
        this.state = useState({
            attribute_value_ids: parseFloat(this.values[0].id),
            custom_value: "",
        });
    }

    getValue() {
        const attribute_value_ids =
            this.attributeLine.attribute_id.display_type === "multi"
                ? this.values.filter((val) => this.state.attribute_value_ids[val.id])
                : [this.values.find((val) => val.id === parseInt(this.state.attribute_value_ids))];

        const extra = attribute_value_ids.reduce((acc, val) => acc + val.price_extra, 0);
        const valueIds = attribute_value_ids.map((val) => val.id);
        const value = attribute_value_ids
            .map((val) => {
                if (val.is_custom && this.state.custom_value) {
                    return `${val.name}: ${this.state.custom_value}`;
                }
                return val.name;
            })
            .join(", ");
        const hasCustom = attribute_value_ids.some((val) => val.is_custom);

        return {
            value,
            valueIds,
            custom_value: this.state.custom_value,
            extra,
            hasCustom,
        };
    }

    getFormatPriceExtra(val) {
        const sign = val < 0 ? "- " : "+ ";
        return sign + this.env.utils.formatCurrency(Math.abs(val));
    }
}

export class RadioProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.RadioProductAttribute";

    setup() {
        super.setup();
        this.root = useRef("root");
        onMounted(this.onMounted);
    }
    onMounted() {
        // With radio buttons `t-model` selects the default input by searching for inputs with
        // a matching `value` attribute. In our case, we use `t-att-value` so `value` is
        // not found yet and no radio is selected by default.
        // We then manually select the first input of each radio attribute.
        this.root.el.querySelector("input[type=radio]").checked = true;
    }
}

export class PillsProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.PillsProductAttribute";
}

export class SelectProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.SelectProductAttribute";
}

export class ColorProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.ColorProductAttribute";
}

export class MultiProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.MultiProductAttribute";

    setup() {
        super.setup();
        this.state = useState({
            attribute_value_ids: {},
            custom_value: "",
        });

        this.initAttribute();
    }

    initAttribute() {
        for (const value of this.values) {
            this.state.attribute_value_ids[value.id] = false;
        }
    }
}

export class ProductConfiguratorPopup extends Component {
    static template = "point_of_sale.ProductConfiguratorPopup";
    static components = {
        RadioProductAttribute,
        ProductInfoBanner,
        PillsProductAttribute,
        SelectProductAttribute,
        ColorProductAttribute,
        MultiProductAttribute,
        Dialog,
    };
    static props = ["product", "getPayload", "close"];

    setup() {
        useSubEnv({ attribute_components: [] });
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.inputArea = useRef("input-area");
        this.state = useState({
            product: this.props.product,
            payload: this.env.attribute_components,
        });

        this.computeProductProduct();
        useRefListener(this.inputArea, "touchend", this.computeProductProduct.bind(this));
        useRefListener(this.inputArea, "click", this.computeProductProduct.bind(this));
    }
    computePayload() {
        const attribute_custom_values = [];
        let attribute_value_ids = [];
        var price_extra = 0.0;

        this.state.payload.forEach((attribute_component) => {
            const { valueIds, extra, custom_value, hasCustom } = attribute_component.getValue();
            attribute_value_ids.push(valueIds);

            if (hasCustom) {
                // for custom values, it will never be a multiple attribute
                attribute_custom_values[valueIds[0]] = custom_value;
            }
            const attr = this.pos.data.models["product.template.attribute.value"].get(valueIds[0]);
            if (attr && attr.attribute_id.create_variant !== "always") {
                price_extra += extra;
            }
        });

        attribute_value_ids = attribute_value_ids.flat();
        return {
            attribute_value_ids,
            attribute_custom_values,
            price_extra,
        };
    }
    computeProductProduct() {
        let product = this.props.product;
        const formattedPayload = this.computePayload();
        const alwaysVariants = this.props.product.attribute_line_ids.every(
            (line) => line.attribute_id.create_variant === "always"
        );

        if (alwaysVariants) {
            const newProduct = this.pos.models["product.product"]
                .filter((p) => p.raw?.product_template_variant_value_ids?.length > 0)
                .find((p) =>
                    p.raw.product_template_variant_value_ids.every((v) =>
                        formattedPayload.attribute_value_ids.includes(v)
                    )
                );
            if (newProduct) {
                product = newProduct;
            }
        }

        this.state.product = product;
    }
    get imageUrl() {
        const product = this.props.product;
        return `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
    }
    get unitPrice() {
        return this.env.utils.formatCurrency(this.props.product.lst_price);
    }
    close() {
        this.props.close();
    }
    confirm() {
        this.props.getPayload(this.computePayload());
        this.props.close();
    }
    isArchivedCombination() {
        const variantAttributeValueIds = this.getVariantAttributeValueIds();
        if (variantAttributeValueIds.length === 0) {
            return false;
        }
        return this.props.product._isArchivedCombination(variantAttributeValueIds);
    }
    getVariantAttributeValueIds() {
        const attribute_value_ids = [];
        this.state.payload.forEach((att_component) => {
            const { valueIds } = att_component.getValue();
            if (att_component.attributeLine.attribute_id.create_variant === "always") {
                attribute_value_ids.push(valueIds);
            }
        });
        return attribute_value_ids.flat();
    }
}
