export class ProductTemplateAttributeValue {
    /**
     * @param {number} id
     * @param {string} name
     * @param {number} price_extra
     * @param {string|undefined} custom_value
     * @param {boolean|undefined} is_custom
     */
    constructor({id, name, price_extra, custom_value, is_custom}) {
        this.id = id;
        this.name = name;
        this.price_extra = price_extra;
        this.custom_value = custom_value;
        this.is_custom = is_custom;
    }
}
