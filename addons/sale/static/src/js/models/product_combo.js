import { ProductComboItem } from './product_combo_item';

export class ProductCombo {
    /**
     * @param {number} id
     * @param {string} name
     * @param {ProductComboItem[]|object[]} combo_items
     * @param {number} included_qty
     */
    constructor({id, name, combo_items, included_qty}) {
        this.id = id;
        this.name = name;
        this.combo_items = combo_items.map(item => new ProductComboItem(item));
        this.included_qty = included_qty;
    }

    /**
     * Return the selected combo item, if any.
     *
     * @return {ProductComboItem|undefined} The selected combo item, if any.
     */
    get selectedComboItems() {
        return this.combo_items.filter(item => item.is_selected);
    }

    /**
    * Return the preselected combo item, if any.
    *
    * @return {ProductComboItem|undefined} The preselected combo items, if any.
    */
    get preselectedComboItem() {
        return this.combo_items.find(item => item.is_preselected);
    }

    /**
     * Check whether this combo is configurable.
     *
     * @return {Boolean} Whether this combo is configurable.
     */
    get isConfigurable() {
        return !this.combo_items.some(item => item.is_preselected);
    }
}
