import { Plugin, shared } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

export class ProductCategoriesOptionPlugin extends Plugin {
    static id = "productCategoriesOption";
    static shared = shared(["getCategories"]);

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [".s_product_categories"],
        dropzone_selectors: {
            // The snippet only displays the categories: nothing can be dropped inside it
            plugin: this,
            get selector() {
                return [
                    ...this.plugin.getResource("so_content_addition_selectors"),
                    ".s_card",
                ].join(", ");
            },
            excludeAncestor: ".s_product_categories",
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        clean_for_save_processors: this.removeColumn.bind(this),
    };

    /**
     * Return the categories that the snippet can display, with their number of children.
     *
     * @returns {Promise<Object[]>} The `id` and `name` (with the count) of each category.
     */
    getCategories() {
        this.categories ??= this.services.orm.call(
            "product.public.category",
            "get_available_snippet_categories",
            [this.services.website.currentWebsiteId]
        );
        return this.categories;
    }

    /**
     * Display the first category, headed by its name, in a dropped snippet.
     */
    async onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches(".s_product_categories") || snippetEl.dataset.parentCategoryId) {
            return;
        }
        const [firstCategory] = await this.getCategories();
        if (firstCategory) {
            snippetEl.dataset.parentCategoryId = firstCategory.id;
            snippetEl.dataset.showParent = "true";
        }
    }

    /**
     * Remove the column from the saved content, as it is rendered when the page loads.
     *
     * @param {HTMLElement} root
     * @returns {HTMLElement}
     */
    removeColumn(root) {
        for (const snippetEl of selectElements(root, ".s_product_categories")) {
            snippetEl.replaceChildren();
        }
        return root;
    }
}

registry
    .category("website-plugins")
    .add(ProductCategoriesOptionPlugin.id, ProductCategoriesOptionPlugin);
