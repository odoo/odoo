import { BuilderAction } from "@html_builder/core/builder_action";
import { PreviewableWebsiteConfigAction } from "@website/builder/plugins/customize_website_plugin";
import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { ProductsListPageOption } from "@website_sale/website_builder/products_list_page_option";

class ProductsListPageOptionPlugin extends Plugin {
    static id = "productsListPageOptionPlugin";

    resources = {
        builder_options: [ProductsListPageOption],
        builder_actions: {
            SetShopContainerAction,
            SetPpgAction,
            SetPprAction,
            SetDefaultSortAction,
        },
    };
}
export class SetShopContainerAction extends PreviewableWebsiteConfigAction {
    static id = "setShopContainer";

    async apply({ editingElement: productDetailMainEl, isPreviewing, params, value }) {
        await super.apply({ editingElement: productDetailMainEl, isPreviewing, params, value });

        if (!isPreviewing) {
            await rpc("/shop/config/website", { 'shop_page_container': value });
        }
    }
}
export class SetPpgAction extends BuilderAction {
    static id = "setPpg";
    setup() {
        this.reload = {};
    }
    getValue({ editingElement }) {
        return parseInt(editingElement.dataset.ppg);
    }
    apply({ value }) {
        const PPG_LIMIT = 10000;
        let ppg = parseInt(value);
        if (!ppg || ppg < 1) {
            return false;
        }
        ppg = Math.min(ppg, PPG_LIMIT);
        return rpc("/shop/config/website", { shop_ppg: ppg });
    }
}
export class SetPprAction extends BuilderAction {
    static id = "setPpr";
    setup() {
        this.reload = {};
    }
    isApplied({ editingElement, value }) {
        return parseInt(editingElement.dataset.ppr) === value;
    }
    apply({ value }) {
        const ppr = parseInt(value);
        return rpc("/shop/config/website", { shop_ppr: ppr });
    }
}
export class SetDefaultSortAction extends BuilderAction {
    static id = "setDefaultSort";
    setup() {
        this.reload = {};
    }
    isApplied({ editingElement, value }) {
        return editingElement.dataset.defaultSort === value;
    }
    apply({ value }) {
        return rpc("/shop/config/website", { shop_default_sort: value });
    }
}

registry
    .category("website-plugins")
    .add(ProductsListPageOptionPlugin.id, ProductsListPageOptionPlugin);
