import { registry } from "@web/core/registry";
import { ProductCategories } from "./product_categories";
import { ProductCategoriesMenu } from "./product_categories_menu";

// In edit mode, render the category names as fields, so that editing them renames the categories
const ProductCategoriesEdit = (I) =>
    class extends I {
        editMode = true;
    };

registry
    .category("public.interactions.edit")
    .add("website_sale.product_categories", {
        Interaction: ProductCategories,
        mixin: ProductCategoriesEdit,
    })
    .add("website_sale.product_categories_menu", { Interaction: ProductCategoriesMenu });
