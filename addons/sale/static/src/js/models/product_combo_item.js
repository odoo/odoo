import { ProductProduct } from './product_product';

export class ProductComboItem {
    /**
     * @param {number} id
     * @param {number} extra_price
     * @param {boolean} is_selected
     * @param {ProductProduct|object} product
     */
    constructor({id, extra_price, is_selected, product}) {
        this.id = id;
        this.extra_price = extra_price;
        this.is_selected = is_selected;
        this.product = new ProductProduct(product);
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
