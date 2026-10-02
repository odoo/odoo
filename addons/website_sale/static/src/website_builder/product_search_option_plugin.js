import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { fetchProductSearchData } from "../snippets/s_product_search/product_search_utils";

export class ProductSearchOptionPlugin extends Plugin {
    static id = "productSearchOption";
    resources = {
        so_content_addition_selectors: [".s_product_search"],
        is_unremovable_selectors: ".s_product_search_attributes",
        builder_actions: {
            AddProductSearchAttributeFilterAction,
            SetProductSearchLabelAction,
        },
    };
}

registry.category("website-plugins").add(ProductSearchOptionPlugin.id, ProductSearchOptionPlugin);

export class AddProductSearchAttributeFilterAction extends BuilderAction {
    static id = "addProductSearchAttributeFilter";
    static dependencies = ["builderOptions"];

    async prepare() {
        const { attributes } = await fetchProductSearchData();
        this.attributes = attributes;
    }

    apply({ editingElement }) {
        const filterEl = document.createElement("div");
        filterEl.className = "s_product_search_attribute_filter min-w-0 d-empty-none";
        filterEl.dataset.attributeId = this.attributes[0].id;
        editingElement.querySelector(".s_product_search_attributes").appendChild(filterEl);
        this.dependencies.builderOptions.setNextTarget(filterEl);
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
