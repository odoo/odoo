import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class BlogPostTagsOption extends BaseOptionComponent {
    static id = "blog_post_tags_option";
    static template = "website_blog.BlogPostTagsOption";

    setup() {
        super.setup();
        this.domState = useDomState((el) => {
            const coverEl = el.querySelector(
                ".o_wblog_post_page_cover[data-res-model='blog.post']"
            );
            return {
                blogId: parseInt(coverEl.dataset.resId),
            };
        });
    }
}

registry.category("website-options").add(BlogPostTagsOption.id, BlogPostTagsOption);
