import { registry } from "@web/core/registry";
import { DynamicSnippetBlogPostsOption } from "./dynamic_snippet_blog_posts_option";

export class DynamicSnippetBlogPostsCarouselOption extends DynamicSnippetBlogPostsOption {
    static id = "dynamic_snippet_blog_posts_carousel_option";
    static template = "website_blog.DynamicSnippetBlogPostsCarouselOption";
}

registry
    .category("website-options")
    .add(DynamicSnippetBlogPostsCarouselOption.id, DynamicSnippetBlogPostsCarouselOption);
