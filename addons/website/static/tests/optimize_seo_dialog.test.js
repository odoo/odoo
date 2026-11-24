import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import {
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { OptimizeSEODialog } from "@website/components/dialog/seo";
import { defineWebsiteModels } from "./builder/website_helpers";

defineWebsiteModels();

test("custom url can be edited with a non-ascii slug", async () => {
    mockService("website", {
        currentWebsite: {
            id: 1,
            metadata: {
                mainObject: { model: "product.public.category", id: 1 },
                path: "http://localhost/shop/category/%D0%BC%D0%B5%D0%B1%D0%B5%D0%BB%D0%B8-1",
            },
        },
        pageDocument: document,
    });
    onRpc("/website/get_seo_data", () => ({
        can_edit_seo: true,
        has_social_default_image: false,
        seo_name: "",
        seo_name_default: "мебели",
    }));
    onRpc("/website/get_alt_images", () => "[]");
    onRpc("/website/get_languages", () => []);
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(OptimizeSEODialog);
    await waitFor(".oe_seo_configuration");
    expect(".seo_name_pre").toHaveText("/shop/category/");
    expect(".seo_name_post").toHaveText("-1");
});
