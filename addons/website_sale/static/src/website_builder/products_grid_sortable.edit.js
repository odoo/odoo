import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

function isPublished(productEl) {
    return productEl.querySelector(".oe_product_cart").dataset.publish === "on";
}

export class ProductsGridSortable extends Interaction {
    static selector = "#o_wsale_products_grid[data-wsale-sortable]";

    setup() {
        this.sortable = this.services.sortable
            .create({
                ref: () => this.el,
                elements: ".oe_product[data-product-template-id]",
                ignore: "[contenteditable='true']",
                placeholderClasses: ["visible", "bg-body-secondary", "rounded"],
                onDrop: this.onDrop.bind(this),
            })
            .enable();
    }

    destroy() {
        this.sortable.cleanup();
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement|null} params.previous
     * @param {HTMLElement|null} params.next
     */
    onDrop({ element, previous, next }) {
        // Don't mix published and unpublished products.
        const isPreviousUnpublished = previous && !isPublished(previous);
        const isNextPublished = next && isPublished(next);
        if (isPublished(element) ? isPreviousUnpublished : isNextPublished) {
            return;
        }
        if (previous) {
            previous.after(element);
        } else {
            next.before(element);
        }
        queueMicrotask(() => {
            this.services.website_edit.callShared("history", "commit");
        });
    }
}

registry.category("public.interactions.edit").add("website_sale.products_grid_sortable", {
    Interaction: ProductsGridSortable,
});
