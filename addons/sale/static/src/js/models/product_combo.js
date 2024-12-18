import { ProductComboItem } from './product_combo_item';

export class ProductCombo {
    /**
     * @param {number} id
     * @param {string} name
     * @param {ProductComboItem[]|object[]} combo_items
     */
    constructor({id, name, combo_items}) {
        this.id = id;
        this.name = name;
        this.combo_items = combo_items.map(item => new ProductComboItem(item));
    }

    /**
     * Return the selected combo item, if any.
     *
     * @return {ProductComboItem|undefined} The selected combo item, if any.
     */
    get selectedComboItem() {
        return this.combo_items.find(item => item.is_selected);
    }
}
