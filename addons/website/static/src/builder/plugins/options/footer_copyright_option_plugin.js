import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { FooterCopyrightOption } from "@website/builder/plugins/options/footer_copyright_option";

class FooterCopyrightOptionPlugin extends Plugin {
    static id = "footerCopyrightOption";
    static dependencies = ["HeaderNavbarOptionPlugin", "customizeWebsite"];

    resources = {
        builder_options: [
            {
                props: {
                    getCurrentActiveViews: () => this.dependencies.HeaderNavbarOptionPlugin.getCurrentActiveViews(this.keys),
                },
                OptionComponent: FooterCopyrightOption,
                selector: ".o_footer_copyright",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };

    setup() {
        this.keys = [
            "website.footer_custom",
            "website.template_footer_descriptive",
            "website.template_footer_centered",
            "website.template_footer_links",
            "website.template_footer_minimalist",
            "website.template_footer_contact",
            "website.template_footer_call_to_action",
            "website.template_footer_headline",
            'website.template_footer_mega',
            'website.template_footer_mega_columns',
        ];
    }
}

registry
    .category("website-plugins")
    .add(FooterCopyrightOptionPlugin.id, FooterCopyrightOptionPlugin);
