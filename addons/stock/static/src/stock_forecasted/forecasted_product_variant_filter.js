import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";


export class ForecastedProductVariantFilter extends Component {
    static template = "stock.ForecastedProductVariantFilter";
    static components = { Dropdown, DropdownItem };
    static props = { action: Object, setVariantInContext: Function, variants: Array };

    setup() {
        this.orm = useService("orm");
        this.context = this.props.action.context;
        this.variants = this.props.variants;
    }

    _onSelected(id){
        this.props.setVariantInContext(Number(id));
    }

    get activeVariant() {
        let variantIds = null;
        if (Array.isArray(this.context.variant_id)) {
            variantIds = this.context.variant_id;
        } else {
            variantIds = [this.context.variant_id];
        }
        return variantIds
            ? this.variants.find((variant) => variantIds.includes(variant.id))
            : this.variants[0];
    }

    get variantItems() {
        return this.variants.map(variant => ({
            id: variant.id,
            label: variant.display_name,
            onSelected: () => this._onSelected(variant.id),
        }));
    }
}
