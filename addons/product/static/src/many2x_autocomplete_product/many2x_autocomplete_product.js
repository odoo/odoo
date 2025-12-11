import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class Many2XAutocompleteProduct extends Many2XAutocomplete {
    static props = {
        ...super.props,
        onFocus: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
    }

    get autoCompleteProps() {
        return {
            ...super.autoCompleteProps,
            onFocus: this.props?.onFocus?.bind(this),
            onBlur: this.props?.onBlur?.bind(this),
        }
    }
}
