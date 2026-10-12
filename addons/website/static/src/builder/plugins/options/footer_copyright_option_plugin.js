import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";

class FooterCopyrightOptionPlugin extends Plugin {
    static id = "footerCopyrightOption";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        auto_unfold_container_providers: { selector: ".o_footer_copyright", target: "footer" },
    };
}

registry
    .category("website-plugins")
    .add(FooterCopyrightOptionPlugin.id, FooterCopyrightOptionPlugin);
