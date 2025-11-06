declare module "plugins" {
    import { DynamicSnippetBlogPostsOptionShared } from "../website_builder/dynamic_snippet_blog_posts_option_plugin";

    interface SharedMethods {
        dynamicSnippetBlogPostsOption: DynamicSnippetBlogPostsOptionShared;
    }
}
