import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class BlogPostTagsOption extends BaseOptionComponent {
    static id = "blog_post_tags_option";
    static template = "website_blog.BlogPostTagsOption";

    setup() {
        super.setup();
        this.domState = useDomState((el) => ({
            blogId: parseInt(el.dataset.resId),
        }));
    }
}

registry.category("builder-options").add(BlogPostTagsOption.id, BlogPostTagsOption);
