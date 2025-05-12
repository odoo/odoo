import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class WebsiteMembersPageOption extends Plugin {
    static id = "websiteMembersPageOption";
    resources = {
        builder_options: [
            {
                template: "website_membership.MembersPageOption",
                selector: "main:has(#oe_structure_website_membership_index_1)",
                title: _t("Members Page"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(WebsiteMembersPageOption.id, WebsiteMembersPageOption);
