import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { HeaderNavbarOption } from "./header_navbar_option";

class HeaderNavbarOptionPlugin extends Plugin {
    static id = "HeaderNavbarOptionPlugin";
    static dependencies = ["customizeWebsite"];

    resources = {
        builder_options: [HeaderNavbarOption],
    };
}

registry.category("website-plugins").add(HeaderNavbarOptionPlugin.id, HeaderNavbarOptionPlugin);
