import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class BlogPostPageOption extends BaseOptionComponent {
    static template = "website_blog.blogPostPageOption";
    static selector = "main:has(#o_wblog_index_content)";
    static title = _t("Blogs Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class BlogPostPageOptionPlugin extends Plugin {
    static id = "blogPostPageOption";
    resources = {
        builder_options: [BlogPostPageOption],
    };
}

registry.category("website-plugins").add(BlogPostPageOptionPlugin.id, BlogPostPageOptionPlugin);
