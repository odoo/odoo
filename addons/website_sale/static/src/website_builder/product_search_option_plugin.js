import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { DataAttributeAction } from "@html_builder/core/core_builder_action_plugin";
import {
    ALL_FILTERS,
    fetchProductSearchData,
    renderAttributeFilter,
} from "../snippets/s_product_search/product_search_utils";

export class ProductSearchOptionPlugin extends Plugin {
    static id = "productSearchOption";
    resources = {
        so_content_addition_selectors: [".s_product_search"],
        builder_actions: {
            AddProductSearchAttributeFilterAction,
            SetProductSearchAttributeAction,
            SetProductSearchLabelAction,
        },
    };
}

registry.category("website-plugins").add(ProductSearchOptionPlugin.id, ProductSearchOptionPlugin);

export class AddProductSearchAttributeFilterAction extends BuilderAction {
    static id = "addProductSearchAttributeFilter";
    static dependencies = ["builderOptions"];

    async load() {
        const { attributes } = await fetchProductSearchData(ALL_FILTERS);
        return attributes;
    }

    apply({ editingElement, loadResult: attributes }) {
        const filterEl = document.createElement("div");
        filterEl.className = "s_product_search_attribute_filter min-w-0";
        filterEl.dataset.attributeId = attributes[0].id;
        editingElement.querySelector(".s_product_search_attributes").appendChild(filterEl);
        renderAttributeFilter(filterEl, attributes);
        this.dependencies.builderOptions.setNextTarget(filterEl);
    }
}

export class SetProductSearchAttributeAction extends DataAttributeAction {
    static id = "setProductSearchAttribute";

    async apply(context) {
        super.apply(context);
        const { attributes } = await fetchProductSearchData(ALL_FILTERS);
        renderAttributeFilter(context.editingElement, attributes);
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
