import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { FooterTemplateChoice } from "@website/builder/plugins/options/footer_template_option";

export class WebsiteSaleFooterOptionPlugin extends Plugin {
    static id = "websiteSaleFooterOption";

    resources = {
        footer_templates_providers: () => [
            {
                key: "website_sale",
                Component: FooterTemplateChoice,
                props: {
                    title: _t("eCommerce"),
                    view: "website_sale.template_footer_website_sale",
                    varName: "website_sale",
                    imgSrc: "/website_sale/static/src/img/snippets_options/footer_template_website_sale.svg",
                },
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteSaleFooterOptionPlugin.id, WebsiteSaleFooterOptionPlugin);
