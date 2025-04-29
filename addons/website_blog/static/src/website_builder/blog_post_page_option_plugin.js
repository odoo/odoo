import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class BlogPostPageOptionPlugin extends Plugin {
    static id = "blogPostPageOption";
    resources = {
        builder_options: [
            {
                template: "website_blog.blogPostPageOption",
                selector: "main:has(#o_wblog_index_content)",
                editableOnly: false,
                title: _t("Blogs Page"),
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(BlogPostPageOptionPlugin.id, BlogPostPageOptionPlugin);
