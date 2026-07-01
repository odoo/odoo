import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { WebsiteConfigAction } from "@website/builder/plugins/customize_website_plugin";

export class CheckoutPageOptionPlugin extends Plugin {
    static id = "checkoutPageOption";
    static shared = ["loadSelectedCategories"];
    resources = {
        builder_actions: {
            SetExtraStepAction,
            SetExtraStepCategoriesAction,
            SetCompanyDetailsAction,
        },
    };

    async loadSelectedCategories() {
        const websiteId = this.services.website.currentWebsite.id;
        const [website] = await this.services.orm.read(
            "website",
            [websiteId],
            ["extra_step_category_ids"],
        );
        const categoryIds = website.extra_step_category_ids;
        if (!categoryIds.length) {
            return [];
        }
        return this.services.orm.read(
            "product.public.category",
            categoryIds,
            ["id", "name"],
        );
    }
}

export class SetExtraStepAction extends WebsiteConfigAction {
    static id = "setExtraStep";
    async apply(context) {
        await Promise.all([
            super.apply(context),
            rpc("/shop/config/website", { extra_step: "true" }),
        ]);
    }
    async clean(context) {
        await Promise.all([
            super.clean(context),
            rpc("/shop/config/website", { extra_step: "false" }),
        ]);
    }
}

export class SetExtraStepCategoriesAction extends BuilderAction {
    static id = "setExtraStepCategories";

    getValue({ editingElement }) {
        return editingElement.dataset.extraStepCategoryIds || "[]";
    }

    async apply({ editingElement, value }) {
        const selection = JSON.parse(value || "[]");
        const categoryIds = selection.map((c) => c.id);
        editingElement.dataset.extraStepCategoryIds = value;
        await rpc("/shop/config/website", {
            extra_step_category_ids: categoryIds,
        });
    }
}

// Disable the "Required" sub-toggle when Company Details is turned off, so
// re-enabling Company Details starts with Required off.
export class SetCompanyDetailsAction extends WebsiteConfigAction {
    static id = "setCompanyDetails";

    async clean(action) {
        (action.params.views ??= []).push("website_sale.required_attributes");
        return super.clean(action);
    }
}


registry.category("website-plugins").add(CheckoutPageOptionPlugin.id, CheckoutPageOptionPlugin);
