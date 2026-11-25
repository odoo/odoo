import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { fetchCategories } from "./product_categories";

/**
 * Add a column to the "Odoo Menu" mega menu for each top-level category created since the menu,
 * placed by sequence.
 */
export class ProductCategoriesMenu extends Interaction {
    static selector = ".s_product_categories_menu";

    setup() {
        // Join the call of the columns, without delaying the page until it returns
        this.response = fetchCategories();
    }

    start() {
        this.waitFor(this.response).then(
            this.protectSyncAfterAsync(({ top_category_ids }) => this.addColumns(top_category_ids))
        );
    }

    /**
     * Add the columns of the given top-level categories that are not displayed yet.
     *
     * @param {number[]} topCategoryIds - IDs of the top-level categories, by sequence.
     */
    addColumns(topCategoryIds) {
        const columnElByCategoryId = new Map(
            [...this.el.querySelectorAll(":scope > .s_product_categories")].map((columnEl) => [
                parseInt(columnEl.dataset.parentCategoryId),
                columnEl,
            ])
        );
        topCategoryIds.forEach((categoryId, index) => {
            if (columnElByCategoryId.has(categoryId)) {
                return;
            }
            // Place the column before the one of the next category by sequence, if any
            const nextColumnEl = topCategoryIds
                .slice(index + 1)
                .map((nextCategoryId) => columnElByCategoryId.get(nextCategoryId))
                .find(Boolean);
            const columnEl = this.createColumn(categoryId);
            this.el.insertBefore(columnEl, nextColumnEl || null);
            columnElByCategoryId.set(categoryId, columnEl);
            this.services["public.interactions"].startInteractions(columnEl);
        });
    }

    /**
     * Create the column of a category by copying another column of the menu, so that it gets the
     * same options, like the alignment or the heading.
     *
     * @param {number} categoryId
     * @returns {HTMLElement}
     */
    createColumn(categoryId) {
        const siblingEl = this.el.querySelector(":scope > .s_product_categories");
        const columnEl = siblingEl ? siblingEl.cloneNode(false) : this.createDefaultColumn();
        columnEl.dataset.parentCategoryId = categoryId;
        // The visibility of the column is decided by its own interaction
        columnEl.classList.remove("d-none");
        return columnEl;
    }

    /**
     * Create a column like the ones of the "Odoo Menu" template, for a menu without any column.
     *
     * @returns {HTMLElement}
     */
    createDefaultColumn() {
        const columnEl = document.createElement("div");
        columnEl.className = "s_product_categories pt-3 pb-4 o_not_editable";
        Object.assign(columnEl.dataset, {
            snippet: "s_product_categories",
            name: "Product Categories",
            showParent: "true",
        });
        return columnEl;
    }
}

registry
    .category("public.interactions")
    .add("website_sale.product_categories_menu", ProductCategoriesMenu);
