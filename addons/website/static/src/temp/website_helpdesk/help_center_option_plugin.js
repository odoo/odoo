import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class HelpCenterPageOptionPlugin extends Plugin {
    static id = "helpCenterPageOption";
    resources = {
        builder_options: [
            {
                template: "website_helpdesk.helpCenterPageOption",
                selector: "main:has(ul.o_whelpdesk_topbar_filters)",
                editableOnly: false,
                title: _t("Help Center Page"),
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(HelpCenterPageOptionPlugin.id, HelpCenterPageOptionPlugin);
