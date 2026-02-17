import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { HeaderTopOptions } from "./header_top_options";

export class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";
    static dependencies = ["customizeWebsite", "menuDataPlugin"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: [
            {
                Component: HeaderTopOptions,
                editableOnly: false,
                selector: "#wrapwrap > header",
                props: {
                    openEditMenu: () => this.dependencies.menuDataPlugin.openEditMenu(),
                },
            },
        ],
    };
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
