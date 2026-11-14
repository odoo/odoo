import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { renderToMarkup } from "@web/core/utils/render";

export class InstagramCarousel extends DynamicSnippetCarousel {
    static selector = ".s_dynamic_snippet_instagram";

    setup() {
        super.setup();
        // Display the counts like Instagram does: "12", "1.2K", "25.3K"...
        this.countFormatter = new Intl.NumberFormat(user.lang, {
            notation: "compact",
            maximumFractionDigits: 1,
        });
    }

    async fetchData() {
        const { posts, ...profile } = await this.waitFor(
            this.rpc("/website/snippet/instagram_feed", {
                account_id: parseInt(this.el.dataset.instagramAccountId),
                limit: parseInt(this.el.dataset.numberOfRecords),
            })
        );
        this.data = posts.map((post) =>
            renderToMarkup("website.s_dynamic_snippet_instagram.post", {
                post,
                profile,
                // Like Instagram, do not display the counts that are 0, nor the
                // likes that are hidden by the owner (no `like_count`).
                likes: post.like_count && this.countFormatter.format(post.like_count),
                comments: post.comments_count && this.countFormatter.format(post.comments_count),
            })
        );
    }
}

registry.category("public.interactions").add("website.instagram_carousel", InstagramCarousel);

registry.category("public.interactions.preview").add("website.instagram_carousel", {
    Interaction: InstagramCarousel,
});
