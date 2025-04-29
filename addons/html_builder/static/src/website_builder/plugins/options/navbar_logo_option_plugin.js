import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";

class NavbarLogoOptionPlugin extends Plugin {
    static id = "navbarLogoOptionPlugin";
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_NEXT, {
                template: "website.NavbarLogoOption",
                selector: "#wrapwrap > header nav.navbar .navbar-brand",
                title: _t("Navbar Logo"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(NavbarLogoOptionPlugin.id, NavbarLogoOptionPlugin);
