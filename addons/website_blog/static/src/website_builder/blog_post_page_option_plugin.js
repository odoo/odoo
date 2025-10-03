import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";

/**
 * Builder option component for blog index pages (both "All blogs" and specific
 * blog pages).
 */
export class BlogPostPageOption extends BaseOptionComponent {
    static id = "blog_post_page_option";
    static template = "website_blog.blogPostPageOption";

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            // True when viewing a specific blog page, allows to show some
            // options not needed on the "All blogs" page (detected via the
            // `o_wblog_single_blog_top` class, only added on specific blogs).
            isOnBlogPage: !!el.querySelector(".o_wblog_single_blog_top"),
        }));
    }
}

registry.category("website-options").add(BlogPostPageOption.id, BlogPostPageOption);
