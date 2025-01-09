import { ProductProduct } from './product_product';

export class ProductComboItem {
    /**
     * @param {number} id
     * @param {number} extra_price
     * @param {boolean} is_preselected
     * @param {boolean} is_selected
     * @param {boolean} is_configurable
     * @param {ProductProduct|object} product
     */
    constructor({id, extra_price, is_preselected, is_selected, is_configurable, product}) {
        this.id = id;
        this.extra_price = extra_price;
        this.is_preselected = is_preselected;
        this.is_selected = is_selected;
        this.is_configurable = is_configurable;
        this.product = new ProductProduct(product);
    }

    /**
     * Return the combo item's "total" extra price.
     *
     * The total extra price is the sum of:
     * - The combo item's extra price,
     * - The extra price of the selected `no_variant` PTAVs of the combo item's product.
     *
     * @return {Number} The combo item's "total" extra price.
     */
    get totalExtraPrice() {
        return this.extra_price + this.product.selectedNoVariantPtavsPriceExtra;
    }

    /**
     * Return a deep copy of this combo item.
     *
     * @return {ProductComboItem} A deep copy of this combo item.
     */
    deepCopy() {
        return new ProductComboItem(JSON.parse(JSON.stringify(this)));
    }
}
