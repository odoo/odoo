import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { renderToFragment } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";

let batch = null;

/**
 * Fetch the given category with its children, and the top-level categories. The interactions that
 * start together, like the ones of a mega menu, fetch them in a single call.
 *
 * @param {number} [categoryId]
 * @returns {Promise<Object>} The `categories` that can be displayed, by ID, with their
 *     `child_categories`; and the `top_category_ids`, by sequence.
 */
export function fetchCategories(categoryId) {
    if (!batch) {
        const categoryIds = new Set();
        // Send the call once the interactions starting in the same tick have added their category
        const response = Promise.resolve().then(() => {
            batch = null;
            return rpc("/website_sale/snippet/product_categories", {
                category_ids: [...categoryIds],
            });
        });
        batch = { categoryIds, response };
    }
    if (categoryId) {
        batch.categoryIds.add(categoryId);
    }
    return batch.response;
}

export class ProductCategories extends Interaction {
    static selector = ".s_product_categories";
    editMode = false;
    dynamicContent = {
        // Hide the snippet from visitors when it has nothing to display
        _root: { "t-att-class": () => ({ "d-none": !this.editMode && this.isEmpty() }) },
    };

    async willStart() {
        const categoryId = parseInt(this.el.dataset.parentCategoryId);
        if (categoryId) {
            const { categories } = await this.waitFor(fetchCategories(categoryId));
            this.categoryData = categories[categoryId];
        }
    }

    get showParent() {
        return !!this.el.dataset.showParent;
    }

    get showSeparator() {
        return !!this.el.dataset.showSeparator;
    }

    /**
     * Return whether the snippet has nothing to display: its category has no published products,
     * or it has no children with published products while its heading is hidden.
     *
     * @returns {boolean}
     */
    isEmpty() {
        return (
            !this.categoryData || (!this.showParent && !this.categoryData.child_categories.length)
        );
    }

    start() {
        // The column is kept when the interaction stops, so that the editor can save the
        // categories renamed in it before saving the page, from which it is removed
        this.el.replaceChildren(
            renderToFragment("website_sale.ProductCategoriesColumn", {
                categoryData: this.categoryData,
                showParent: this.showParent,
                showSeparator: this.showSeparator,
                editMode: this.editMode,
            })
        );
    }
}

registry
    .category("public.interactions")
    .add("website_sale.product_categories", ProductCategories);
