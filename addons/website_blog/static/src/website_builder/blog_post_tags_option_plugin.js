import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BlogPostTagsOption } from "./blog_post_tags_option";

class BlogPostTagsOptionPlugin extends Plugin {
    static id = "blogPostTagsOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [BlogPostTagsOption],
    };
}

registry.category("website-plugins").add(BlogPostTagsOptionPlugin.id, BlogPostTagsOptionPlugin);
