export class ProductTemplateAttributeValue {
    /**
     * @param {number} id
     * @param {string} name
     * @param {number} price_extra
     * @param {string|undefined} custom_value
     */
    constructor({id, name, price_extra, custom_value}) {
        this.id = id;
        this.name = name;
        this.price_extra = price_extra;
        this.custom_value = custom_value;
    }
}
