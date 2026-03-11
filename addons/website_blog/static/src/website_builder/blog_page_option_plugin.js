import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BlogPageOption extends BaseOptionComponent {
    static id = "blog_page_option";
    static template = "website_blog.BlogPageOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isNextPostRecommended: !!editingElement.querySelector(
                "[data-is-next-post-recommended]"
            ),
        }));
    }
}

export class BlogPageOptionPlugin extends Plugin {
    static id = "blogPageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        content_not_editable_selectors: [".o_list_cover"],
        builder_actions: {
            SetRecommendedNextPostAction,
        },
    };
}

export class SetRecommendedNextPostAction extends BuilderAction {
    static id = "setRecommendedNextPost";
    static dependencies = ["savePlugin"];

    setup() {
        this.reload = {};
    }

    /**
     * Updates the recommended next post and reloads the editor.
     *
     * @param {number|false} id - ID of the recommended post, or false to unset
     */
    async updateRecommendedNextPost(id) {
        const { website, orm } = this.services;
        const { mainObject } = website.currentWebsite.metadata;

        await orm.write(mainObject.model, [mainObject.id], {
            recommended_next_post_id: id,
        });
    }

    getValue({ editingElement }) {
        return JSON.stringify({ id: parseInt(editingElement.dataset.nextPostId) || 0 });
    }

    async apply({ value }) {
        const { id } = JSON.parse(value);
        await this.updateRecommendedNextPost(id);
    }

    async clean() {
        await this.updateRecommendedNextPost(false);
    }
}

registry.category("website-options").add(BlogPageOption.id, BlogPageOption);
registry.category("website-plugins").add(BlogPageOptionPlugin.id, BlogPageOptionPlugin);
