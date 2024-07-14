/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";

export class Product extends Reactive {
    constructor([id, productName]) {
        super();

        this.id = id;
        this.name = productName;
    }
}
