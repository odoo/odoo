import { Plugin } from "@html_editor/plugin";
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { useDomState } from "@html_builder/core/building_blocks/utils";

class BlogPostTagsOptionPlugin extends Plugin {
    static id = "BlogPostTagsOption";
    static dependencies = ["CachedModel"];
    resources = {
        builder_options: {
            selector: ".o_wblog_post_page_cover[data-res-model='blog.post']",
            OptionComponent: BlogPostTagsOption,
            cleanForSave: () => {
                // keep track of temporary edited value
                // clean up temporary edited value
            },
        },
    };
}

registry
    .category("website-plugins")
    .add(BlogPostTagsOptionPlugin.id, BlogPostTagsOptionPlugin);

export class BlogPostTagsOption extends Component {
    static template = "website_blog.BlogPostTagsOption";
    static components = { ...defaultBuilderComponents };
    static props = {
    };
    setup() {
        this.domState = useDomState((el) => {
            return {
                blogId: parseInt(el.dataset.resId),
            };
        });
    }
}
