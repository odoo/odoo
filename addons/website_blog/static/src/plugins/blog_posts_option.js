import { Plugin } from "@html_editor/plugin";
import { onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { DynamicSnippetOption } from "@html_builder/plugins/dynamic_snippet_option";

class BlogPostsOptionPlugin extends Plugin {
    static id = "BlogPostsOption";
    static dependencies = ["DynamicSnippetOption"];
    resources = {
        builder_options: {
            OptionComponent: BlogPostsOption,
            props: {
                ...this.dependencies.DynamicSnippetOption.getComponentProps(),
                fetchBlogs: this.fetchBlogs.bind(this),
            },
            selector: ".s_dynamic_snippet_blog_posts",
        },
    };
    setup() {
        this.blogs = undefined;
    }
    async fetchBlogs() {
        if (!this.blogs) {
            this.blogs = this._fetchBlogs();
        }
        return this.blogs;
    }
    async _fetchBlogs() {
        // TODO put in an utility function
        const websiteDomain = ['|', ['website_id', '=', false], ['website_id', '=', this.services.website.currentWebsite.id]];
        return this.services.orm.searchRead("blog.blog", websiteDomain, ["id", "name"]);
    }
}

registry
    .category("website-plugins")
    .add(BlogPostsOptionPlugin.id, BlogPostsOptionPlugin);

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
            this.blogState.blogs.push(...await this.props.fetchBlogs());
        });
    }
}
