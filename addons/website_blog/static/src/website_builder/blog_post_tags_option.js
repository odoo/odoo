import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class BlogPostTagsOption extends BaseOptionComponent {
    static template = "website_blog.BlogPostTagsOption";
    static selector = ".o_wblog_post_page_cover[data-res-model='blog.post']";
    static editableOnly = false;

    setup() {
        super.setup();
        this.domState = useDomState((el) => ({
            blogId: parseInt(el.dataset.resId),
        }));
    }
}
