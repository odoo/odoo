declare module "plugins" {
    import { DynamicSnippetBlogPostsOptionPlugin } from "addons/website_blog/static/src/website_builder/dynamic_snippet_blog_posts_option_plugin";

    interface SharedMethods {
        dynamicSnippetBlogPostsOption: SharedOf<typeof DynamicSnippetBlogPostsOptionPlugin>;
    }
}
