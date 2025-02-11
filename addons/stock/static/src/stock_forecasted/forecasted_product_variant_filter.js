import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";

export class ForecastedProductVariantFilter extends Component {
    static template = "stock.ForecastedProductVariantFilter";
    static components = { Dropdown, DropdownItem };
    static props = { action: Object, setVariantInContext: Function, variants: Array };

    setup() {
        this.context = this.props.action.context;
        this.variants = this.props.variants;
    }

    _onSelected(id) {
        this.props.setVariantInContext(Number(id));
    }

    get activeVariant() {
        return this.context.variant_id ? this.variants.find((v) => v.id == this.context.variant_id) : this.variants[0];
    }

    get variantItems() {
        return this.variants.map(variant => ({
            id: variant.id,
            label: variant.display_name,
            onSelected: () => this._onSelected(variant.id),
        }));
    }
}
