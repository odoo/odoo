import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { DataAttributeAction } from "@html_builder/core/core_builder_action_plugin";
import { fetchProductSearchData, renderAttributeFilter } from "../snippets/s_product_search/product_search_utils";

export class ProductSearchOptionPlugin extends Plugin {
    static id = "productSearchOption";
    resources = {
        so_content_addition_selectors: [".s_product_search"],
        builder_actions: {
            SetProductSearchAttributeAction,
            SetProductSearchLabelAction,
        },
    };
}

registry.category("website-plugins").add(ProductSearchOptionPlugin.id, ProductSearchOptionPlugin);

export class SetProductSearchAttributeAction extends DataAttributeAction {
    static id = "setProductSearchAttribute";

    async apply(context) {
        super.apply(context);
        const { attributes } = await fetchProductSearchData();
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
