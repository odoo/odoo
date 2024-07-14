/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";

export class Orderline extends Reactive {
    constructor(
        {
            id,
            internal_note = "",
            product_cancelled,
            product_category_ids,
            product_id,
            product_name,
            product_quantity,
            attribute_ids,
            todo,
        },
        order,
        blinkingNote
    ) {
        super();

        this.id = id;
        this.internalNote = internal_note;
        this.productCancelled = product_cancelled;
        this.productCategoryIds = product_category_ids;
        this.productId = product_id;
        this.productName = product_name;
        this.productQuantity = product_quantity;
        this.attribute_ids = attribute_ids ?? [];
        this.todo = todo;
        this.order = order;
        this.blinkingNote = blinkingNote || false;

        if (this.blinkingNote) {
            setTimeout(() => {
                this.blinkingNote = false;
            }, 20000);
        }
    }

    get isCancelled() {
        return this.productCount === 0 ? true : false;
    }

    get productCount() {
        const productCount = this.productQuantity - this.productCancelled;
        return productCount;
    }
}
