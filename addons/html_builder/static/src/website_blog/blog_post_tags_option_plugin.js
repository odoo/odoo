import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BlogPostTagsOption } from "./blog_post_tags_option";

class BlogPostTagsOptionPlugin extends Plugin {
    static id = "blogPostTagsOption";
    static dependencies = ["cachedModel"];
    resources = {
        builder_options: {
            selector: ".o_wblog_post_page_cover[data-res-model='blog.post']",
            OptionComponent: BlogPostTagsOption,
            cleanForSave: () => {
                // keep track of temporary edited value
                // clean up temporary edited value
            },
            editableOnly: false,
        },
    };
}

registry.category("website-plugins").add(BlogPostTagsOptionPlugin.id, BlogPostTagsOptionPlugin);
