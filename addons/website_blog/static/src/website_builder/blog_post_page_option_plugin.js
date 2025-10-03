import { registry } from "@web/core/registry";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class BlogPostPageOption extends BaseOptionComponent {
    static id = "blog_post_page_option";
    static template = "website_blog.blogPostPageOption";

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            isOnBlogPage: !!el.querySelector('.o_wblog_homepage_top'),
        }));
    }
}

registry.category("website-options").add(BlogPostPageOption.id, BlogPostPageOption);
