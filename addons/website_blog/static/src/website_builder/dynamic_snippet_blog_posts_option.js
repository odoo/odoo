import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { registry } from "@web/core/registry";
import {
    dynamicContentOfDynamicSnippet,
    getSharedSnippetArg,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";

export class DynamicSnippetBlogPostsOption extends BaseOptionComponent {
    static id = "dynamic_snippet_blog_posts_option";
    static template = "website_blog.DynamicSnippetBlogPostsOption";

    setup() {
        super.setup();
        this.dynamicOptionParams = useDynamicSnippetOption();
        this.templateKeyState = useDomState((el) => ({
            templateKey: getSharedSnippetArg(
                dynamicContentOfDynamicSnippet(el),
                "content_template"
            ),
        }));
    }
    showPictureSizeOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_big_picture",
            "website_blog.dynamic_filter_template_blog_post_horizontal",
            "website_blog.dynamic_filter_template_blog_post_card",
        ].includes(this.templateKeyState.templateKey);
    }
    showTeaserOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_list",
            "website_blog.dynamic_filter_template_blog_post_card",
        ].includes(this.templateKeyState.templateKey);
    }
    showDateOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_list",
            "website_blog.dynamic_filter_template_blog_post_horizontal",
            "website_blog.dynamic_filter_template_blog_post_card",
            "website_blog.dynamic_filter_template_blog_post_single_full",
            "website_blog.dynamic_filter_template_blog_post_single_aside",
            "website_blog.dynamic_filter_template_blog_post_single_circle",
        ].includes(this.templateKeyState.templateKey);
    }
    showCategoryOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_list",
            "website_blog.dynamic_filter_template_blog_post_horizontal",
            "website_blog.dynamic_filter_template_blog_post_card",
            "website_blog.dynamic_filter_template_blog_post_single_full",
            "website_blog.dynamic_filter_template_blog_post_single_aside",
            "website_blog.dynamic_filter_template_blog_post_single_circle",
            "website_blog.dynamic_filter_template_blog_post_single_badge",
        ].includes(this.templateKeyState.templateKey);
    }
    showNewTagOption() {
        return (
            this.templateKeyState.templateKey ===
            "website_blog.dynamic_filter_template_blog_post_single_badge"
        );
    }
    showHoverEffectOption() {
        return (
            this.templateKeyState.templateKey ===
            "website_blog.dynamic_filter_template_blog_post_big_picture"
        );
    }
    showCoverImageOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_single_aside",
            "website_blog.dynamic_filter_template_blog_post_single_circle",
        ].includes(this.templateKeyState.templateKey);
    }
}

registry
    .category("website-options")
    .add(DynamicSnippetBlogPostsOption.id, DynamicSnippetBlogPostsOption);
