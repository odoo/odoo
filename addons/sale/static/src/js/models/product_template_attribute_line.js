import { ProductTemplateAttributeValue } from './product_template_attribute_value';

export class ProductTemplateAttributeLine {
    /**
     * @param {number} id
     * @param {string} name
     * @param {'always'|'dynamic'|'no_variant'} create_variant
     * @param {ProductTemplateAttributeValue[]|object[]} selected_ptavs
     */
    constructor({id, name, create_variant, selected_ptavs}) {
        this.id = id;
        this.name = name;
        this.create_variant = create_variant;
        this.selected_ptavs = selected_ptavs.map(ptav => new ProductTemplateAttributeValue(ptav));
    }

    /**
     * Construct a ProductTemplateAttributeLine from the provided "product configurator"-shaped
     * PTAL.
     *
     * @param productConfiguratorPtal The "product configurator"-shaped PTAL.
     * @return {ProductTemplateAttributeLine} The corresponding ProductTemplateAttributeLine.
     */
    static fromProductConfiguratorPtal(productConfiguratorPtal) {
        const selectedPtavIds = new Set(productConfiguratorPtal.selected_attribute_value_ids);
        const selectedPtavs = productConfiguratorPtal.attribute_values
            .filter(ptav => selectedPtavIds.has(ptav.id))
            .map(ptav => new ProductTemplateAttributeValue({
                id: ptav.id,
                name: ptav.name,
                price_extra: ptav.price_extra,
                custom_value: productConfiguratorPtal.customValue,
            }));
        return new ProductTemplateAttributeLine({
            id: productConfiguratorPtal.id,
            name: productConfiguratorPtal.attribute.name,
            create_variant: productConfiguratorPtal.create_variant,
            selected_ptavs: selectedPtavs,
        });
    }

    /**
     * Return the extra price of the selected PTAVs.
     *
     * @return {Number} The extra price of the selected PTAVs.
     */
    get selectedPtavsPriceExtra() {
        return this.selected_ptavs.reduce((price, ptav) => price + ptav.price_extra, 0);
    }

    /**
     * Check whether this PTAL has selected custom PTAVs.
     *
     * @return {Boolean} Whether this PTAL has selected custom PTAVs.
     */
    get hasSelectedCustomPtav() {
        return this.selected_ptavs.some(ptav => ptav.custom_value);
    }

    /**
     * Return the display name of this PTAL.
     *
     * @return {String} The display name of this PTAL.
     */
    get ptalDisplayName() {
        const selectedPtavNames = this.selected_ptavs.map(ptav => ptav.name).join(', ');
        let ptalDisplayName = `${this.name}: ${selectedPtavNames}`;
        if (this.hasSelectedCustomPtav) {
            ptalDisplayName += ` (${this.selected_ptavs[0].custom_value})`;
        }
        return ptalDisplayName;
    }
}
