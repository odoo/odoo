import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BlogPostsOption } from "./blog_posts_option";

class BlogPostsOptionPlugin extends Plugin {
    static id = "blogPostsOption";
    static dependencies = ["dynamicSnippetOption"];
    resources = {
        builder_options: {
            OptionComponent: BlogPostsOption,
            props: {
                ...this.dependencies.dynamicSnippetOption.getComponentProps(),
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

