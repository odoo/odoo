import { Many2One } from "@web/views/fields/many2one/many2one";
import { Many2XAutocompleteProduct } from "@product/many2x_autocomplete_product/many2x_autocomplete_product";

export class Many2OneProduct extends Many2One {
    static template = "product.Many2OneProduct";
    static components = { Many2XAutocompleteProduct }
    static props = {
        ...super.props,
        onFocus: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
    }

    get many2XAutocompleteProps() {
        return {
            ...super.many2XAutocompleteProps,
            onFocus: this.props?.onFocus?.bind(this),
            onBlur: this.props?.onBlur?.bind(this),
        }
    }
}
