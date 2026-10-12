import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";
import { BlogPostsMixin } from "./blog_posts_mixin";

const BlogPostsBase = BlogPostsMixin(DynamicSnippet);

export class BlogPosts extends BlogPostsBase {
    static selector = ".s_dynamic_snippet_blog_posts";
}

registry.category("public.interactions.edit").add("website_blog.blog_posts_base", {
    Interaction: BlogPostsBase,
    isAbstract: true,
});

registry.category("public.interactions").add("website_blog.blog_posts", BlogPosts);

registry.category("public.interactions.edit").add("website_blog.blog_posts", {
    Interaction: BlogPosts,
});

registry.category("public.interactions.preview").add("website_blog.blog_posts", {
    Interaction: BlogPosts,
});
