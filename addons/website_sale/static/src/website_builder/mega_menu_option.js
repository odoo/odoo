import { onWillStart } from "@odoo/owl";
import { MegaMenuOption } from "@website/builder/plugins/options/mega_menu_option";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(MegaMenuOption, {
    // static
    dependencies: [
        ...(MegaMenuOption.dependencies || []),
        "websiteBridge",
    ],
});

patch(MegaMenuOption.prototype, {
    setup() {
        this.orm = useService("orm");
        this.website = useService('website');
        super.setup();
        this.productCategories = [];

        onWillStart(async () => {
            this.productCategories = await this.orm.call("product.public.category", "search", [[
                ["has_published_products", "=", true],
                "|",
                ["website_id", "=", false],
                ["website_id", "=", this.website.currentWebsiteId],
            ]],
            { context: this.dependencies.websiteBridge.getWebsiteContextLang() },
            );
        });
    },
});
