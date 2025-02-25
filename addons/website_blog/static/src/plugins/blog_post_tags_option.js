import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { useDomState } from "@html_builder/core/building_blocks/utils";

export class BlogPostTagsOption extends Component {
    static template = "website_blog.BlogPostTagsOption";
    static components = { ...defaultBuilderComponents };
    static props = {
    };
    setup() {
        this.domState = useDomState((el) => {
            return {
                blogId: parseInt(el.dataset.resId),
            };
        });
    }
}
