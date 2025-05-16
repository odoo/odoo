import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class CouponOptionPlugin extends Plugin {
    static id = "couponOption";
    resources = {
        builder_options: [
            {
                template: "website_sale_loyalty.couponOption",
                selector: "main:has(.oe_website_sale .wizard)",
                editableOnly: false,
                title: _t("Coupon Snippet Options"),
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(CouponOptionPlugin.id, CouponOptionPlugin);
