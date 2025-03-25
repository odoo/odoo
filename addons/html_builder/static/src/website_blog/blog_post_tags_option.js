import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class BlogPostTagsOption extends BaseOptionComponent {
    static template = "website_blog.BlogPostTagsOption";
    setup() {
        super.setup();
        this.domState = useDomState((el) => ({
            blogId: parseInt(el.dataset.resId),
        }));
    }
}
