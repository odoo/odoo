import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { FooterCopyrightOption } from "@website/builder/plugins/options/footer_copyright_option";

class FooterCopyrightOptionPlugin extends Plugin {
    static id = "footerCopyrightOption";

    resources = {
        builder_options: [
            {
                OptionComponent: FooterCopyrightOption,
                selector: ".o_footer_copyright",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(FooterCopyrightOptionPlugin.id, FooterCopyrightOptionPlugin);
