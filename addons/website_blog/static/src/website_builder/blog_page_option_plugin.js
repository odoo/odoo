import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

class BlogPageOption extends Plugin {
    static id = "blogPageOption";
    resources = {
        builder_options: [
            {
                template: "website_blog.BlogPageOption",
                selector: "main:has(#o_wblog_post_main)",
                editableOnly: false,
                title: _t("Blog Page"),
                groups: ["website.group_website_designer"],
            },
        ],
        builder_actions: {
            ToggleRecommendedBlogAction,
            NextArticleAction,
            RecommendedNextArticleAction,
        },
    };
}
class ToggleRecommendedBlogAction extends BuilderAction {
    static id = "toggleRecommendedBlog";
    getValue({ editingElement }) {
        const el = editingElement.querySelector("#o_wblog_post_footer div");
        const id = parseInt(el?.dataset?.recommendedBlogPostId || 0);
        return JSON.stringify({ id });
    }
    isApplied({ editingElement, value, loadResult }) {
        const el = editingElement.querySelector("#o_wblog_post_footer div");
        return parseInt(el.dataset.recommendedBlogPostId || 0);
    }

    async apply({ editingElement, value }) {
        const el = editingElement.querySelector("#wrap");
        await this.services.orm.write("blog.post", [parseInt(el.dataset.resId)], {
            recommended_post_id: JSON.parse(value).id,
        });
        this.config.reloadEditor();
    }
}

class NextArticleAction extends BuilderAction {
    static id = "nextArticle";
    static dependencies = ["builderActions"];

    isApplied({ params }) {
        return this.dependencies.builderActions.getAction("websiteConfig").isApplied({ params });
    }

    async apply(context) {
        await this.dependencies.builderActions.getAction("websiteConfig").apply(context);

        if (context.params.views[0] === "website_blog.opt_blog_post_read_next") {
            const el = context.editingElement.querySelector("#wrap");
            await this.services.orm.write("blog.post", [parseInt(el.dataset.resId)], {
                recommended_post_id: false,
            });
            this.config.reloadEditor();
        }
    }
}

class RecommendedNextArticleAction extends BuilderAction {
    static id = "recommendedNextArticle";
    static dependencies = ["builderActions"];
    isApplied({ params }) {
        return this.dependencies.builderActions.getAction("websiteConfig").isApplied({ params });
    }
    async apply(context) {
        await this.dependencies.builderActions.getAction("websiteConfig").apply(context);

        if (context.params.views[0] === "website_blog.opt_blog_post_read_next_recommended") {
            const el = context.editingElement.querySelector("#wrap");
            const currentPostId = parseInt(el.dataset.resId);

            // Get all blog post IDs in ascending order
            const allPostIds = await this.services.orm.search("blog.post", [], { order: "id asc" });
            const currentIndex = allPostIds.indexOf(currentPostId);
            let nextPostId = null;

            if (allPostIds.length > 1 && currentIndex !== -1) {
                nextPostId = allPostIds[(currentIndex + 1) % allPostIds.length];
            } else {
                nextPostId = allPostIds[0]; // If no next post, loop to the first post
            }

            if (nextPostId) {
                const [nextPost] = await this.services.orm.read(
                    "blog.post",
                    [nextPostId],
                    ["name"]
                );
                await this.services.orm.write("blog.post", [parseInt(el.dataset.resId)], {
                    recommended_post_id: nextPost.id,
                });
                this.config.reloadEditor();
            }
        }
    }
}
registry.category("website-plugins").add(BlogPageOption.id, BlogPageOption);
