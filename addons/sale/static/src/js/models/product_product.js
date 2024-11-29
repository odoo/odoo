import { ProductTemplateAttributeLine } from './product_template_attribute_line';

export class ProductProduct {
    /**
     * The instance is initialized in `setup` to allow patching, as constructors can't be patched.
     */
    constructor(...args) {
        this.setup(...args);
    }

    /**
     * @param {number} id
     * @param {number} product_tmpl_id
     * @param {string} display_name
     * @param {ProductTemplateAttributeLine[]|object[]} ptals
     */
    setup({id, product_tmpl_id, display_name, ptals}) {
        this.id = id;
        this.product_tmpl_id = product_tmpl_id;
        this.display_name = display_name;
        this.ptals = ptals.map(ptal => new ProductTemplateAttributeLine(ptal));
    }

    /**
     * Return the `no_variant` PTALs.
     *
     * @return {ProductTemplateAttributeLine[]} The `no_variant` PTALs.
     */
    get noVariantPtals() {
        return this.ptals.filter(ptal => ptal.create_variant === 'no_variant');
    }

    /**
     * Check whether this product has `no_variant` PTALs.
     *
     * @return {Boolean} Whether this product has `no_variant` PTALs.
     */
    get hasNoVariantPtals() {
        return this.noVariantPtals.length > 0;
    }

    /**
     * Return the extra price of the selected `no_variant` PTAVs.
     *
     * @return {Number} The extra price of the selected `no_variant` PTAVs.
     */
    get selectedNoVariantPtavsPriceExtra() {
        return this.noVariantPtals.reduce((price, ptal) => price + ptal.selectedPtavsPriceExtra, 0);
    }

    /**
     * Return the selected PTAV ids.
     *
     * @return {Number[]} The selected PTAV ids.
     */
    get selectedPtavIds() {
        return this.ptals.flatMap(ptal => ptal.selected_ptavs).map(ptav => ptav.id);
    }

    /**
     * Return the selected `no_variant` PTAV ids.
     *
     * @return {Number[]} The selected `no_variant` PTAV ids.
     */
    get selectedNoVariantPtavIds() {
        return this.noVariantPtals.flatMap(ptal => ptal.selected_ptavs).map(ptav => ptav.id);
    }

    /**
     * Return the selected custom PTAVs.
     *
     * @return {{id: Number, value: String}[]} The selected custom PTAVs.
     */
    get selectedCustomPtavs() {
        return this.ptals.filter(ptal => ptal.hasSelectedCustomPtav).flatMap(
            ptal => ptal.selected_ptavs
        ).map(ptav => ({
            'id': ptav.id,
            'value': ptav.custom_value,
        }));
    }
}
