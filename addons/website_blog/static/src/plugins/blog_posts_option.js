import { onWillStart, useState } from "@odoo/owl";
import { DynamicSnippetOption } from "@html_builder/website_builder/plugins/options/dynamic_snippet_option";

export class BlogPostsOption extends DynamicSnippetOption {
    static template = "website_blog.BlogPostsOption";
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
