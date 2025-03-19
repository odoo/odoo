import { Component } from "@odoo/owl";
import { useBuilderComponents, useDomState } from "@html_builder/core/utils";

export class BlogPostTagsOption extends Component {
    static template = "website_blog.BlogPostTagsOption";
    setup() {
        useBuilderComponents();
        this.domState = useDomState((el) => {
            return {
                blogId: parseInt(el.dataset.resId),
            };
        });
    }
}
