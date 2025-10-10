import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class CouponOption extends BaseOptionComponent {
    static template = "website_sale_loyalty.couponOption";
    static selector = "main:has(.oe_website_sale .wizard)";
    static title = _t("Coupon Snippet Options");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class CouponOptionPlugin extends Plugin {
    static id = "couponOption";
    resources = {
        builder_options: [CouponOption],
    };
}

registry.category("website-plugins").add(CouponOptionPlugin.id, CouponOptionPlugin);
