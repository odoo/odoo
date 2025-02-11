import { Plugin } from "@html_editor/plugin";
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { useDomState } from "@html_builder/core/building_blocks/utils";

class BlogPostTagsOptionPlugin extends Plugin {
    static id = "BlogPostTagsOption";
    resources = {
        builder_options: {
            selector: ".o_wblog_post_page_cover[data-res-model='blog.post']",
            OptionComponent: BlogPostTagsOption,
            props: {
                useModelEditState: this.useModelEditState.bind(this),
            },
            cleanForSave: () => {
                // keep track of temporary edited value
                // clean up temporary edited value
            },
        },
    };
    setup() {
        this.temporaryCache = new Cache(() => ({ selection: undefined }), JSON.stringify);
    }
    destroy() {
        this.temporaryCache.invalidate();
    }
    useModelEditState({ model, recordId }) {
        return this.temporaryCache.read({ model, recordId });
    }
}

registry
    .category("website-plugins")
    .add(BlogPostTagsOptionPlugin.id, BlogPostTagsOptionPlugin);

export class BlogPostTagsOption extends Component {
    static template = "website_blog.BlogPostTagsOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        useModelEditState: Function,
    };
    setup() {
        this.domState = useDomState((el) => {
            return {
                blogId: parseInt(el.dataset.resId),
            };
        });
    }
}
