import { DynamicSnippetBlogPostsOptionPlugin } from "../website_builder/dynamic_snippet_blog_posts_option_plugin";

declare module "plugins" {
    interface SharedMethods {
        dynamicSnippetBlogPostsOption: SharedOf<typeof DynamicSnippetBlogPostsOptionPlugin>;
    }
}
