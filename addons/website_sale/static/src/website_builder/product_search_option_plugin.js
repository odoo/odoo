import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { DataAttributeAction } from "@html_builder/core/core_builder_action_plugin";
import { fetchProductSearchData } from "../snippets/s_product_search/product_search_utils";

export class ProductSearchOptionPlugin extends Plugin {
    static id = "productSearchOption";
    resources = {
        so_content_addition_selectors: [".s_product_search"],
        is_unremovable_selectors: ".s_product_search_attributes",
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        builder_actions: {
            AddProductSearchAttributeFilterAction,
            SetProductSearchAttributeAction,
            SetProductSearchLabelAction,
        },
    };

    async onSnippetDropped({ snippetEl }) {
        const searchEls = [
            ...(snippetEl.matches(".s_product_search") ? [snippetEl] : []),
            ...snippetEl.querySelectorAll(".s_product_search"),
        ];
        if (!searchEls.length) {
            return;
        }
        // Disable the tags field if there are no tags
        const { tags } = await fetchProductSearchData();
        if (!tags.length) {
            for (const searchEl of searchEls) {
                searchEl.querySelector(".s_product_search_tags_wrap").classList.add("d-none");
            }
        }
    }
}

registry.category("website-plugins").add(ProductSearchOptionPlugin.id, ProductSearchOptionPlugin);

export class AddProductSearchAttributeFilterAction extends BuilderAction {
    static id = "addProductSearchAttributeFilter";
    static dependencies = ["builderOptions", "websiteBridge"];

    async prepare() {
        const { attributes } = await fetchProductSearchData();
        this.attributes = attributes;
    }

    apply({ editingElement }) {
        const attribute = this.attributes[0];
        // Only the dropdown toggle is saved, the interaction renders the menu items.
        const filterEl = this.dependencies.websiteBridge.renderToElement(
            "website_sale.s_product_search.attribute_filter",
            { attribute }
        );
        editingElement.querySelector(".s_product_search_attributes").appendChild(filterEl);
        this.dependencies.builderOptions.setNextTarget(filterEl);
    }
}

export class SetProductSearchAttributeAction extends DataAttributeAction {
    static id = "setProductSearchAttribute";

    async prepare() {
        const { attributes } = await fetchProductSearchData();
        this.attributes = attributes;
    }

    apply(context) {
        super.apply(context);
        const { editingElement, value } = context;
        const attribute = this.attributes.find((attr) => attr.id === parseInt(value));
        editingElement.dataset.filterKey = `attribute_${value}`;
        editingElement.querySelector(".s_product_search_filter_label").textContent =
            attribute?.name || "";
    }
}

export class SetProductSearchLabelAction extends BuilderAction {
    static id = "setProductSearchLabel";

    getValue({ editingElement }) {
        return editingElement.textContent;
    }

    isApplied({ editingElement, value }) {
        return editingElement.textContent === value;
    }

    apply({ editingElement, value }) {
        editingElement.textContent = value;
    }
}
