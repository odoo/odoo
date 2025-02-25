import { onWillStart, useState } from "@odoo/owl";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { DynamicSnippetOption } from "@html_builder/plugins/dynamic_snippet_option";

export class BlogPostsOption extends DynamicSnippetOption {
    static template = "website_blog.BlogPostsOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        ...DynamicSnippetOption.props,
        fetchBlogs: Function,
    };
    setup() {
        super.setup();
        this.modelNameFilter = "blog.post";
        this.blogState = useState({
            blogs: [],
        });
        onWillStart(async () => {
            this.blogState.blogs.push(...(await this.props.fetchBlogs()));
        });
    }
}
