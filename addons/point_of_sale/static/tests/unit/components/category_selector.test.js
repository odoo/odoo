import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";

definePosModels();

test("child category is visible when parent is loaded only via a printer", async () => {
    const store = await setupPosEnv();

    const parentCategory = store.models["pos.category"].create({
        id: 1,
        name: "Parent Category",
    });
    const childCategory = store.models["pos.category"].create({
        id: 2,
        name: "Child Category",
        parent_id: parentCategory,
    });
    store.models["pos.printer"].create({
        id: 1,
        name: "Kitchen Printer",
        product_categories_ids: [parentCategory],
    });
    store.models["product.template"].create({
        id: 1,
        name: "Test Product",
        available_in_pos: true,
        pos_categ_ids: [childCategory],
    });

    store.config.limit_categories = true;
    store.config.iface_available_categ_ids = [childCategory];

    const categorySelector = await mountWithCleanup(CategorySelector, {});

    expect(categorySelector.getCategoriesAndSub().map((c) => c.name)).toInclude("Child Category");
});
