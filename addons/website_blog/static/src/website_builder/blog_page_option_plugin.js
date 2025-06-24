import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class BlogPageOption extends BaseOptionComponent {
    static template = "website_blog.BlogPageOption";
    static selector = "main:has(#o_wblog_post_main)";
    static title = _t("Blog Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

    setup() {
        super.setup();
        this.blogState = useDomState((editingElement) => ({
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
        builder_options: [BlogPageOption],
        content_not_editable_selectors: [".o_list_cover"],
        builder_actions: {
            SetRecommendedNextPostAction,
        },
    };
}

export class SetRecommendedNextPostAction extends BuilderAction {
    static id = "setRecommendedNextPost";
    static dependencies = ["savePlugin"];

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

        // Persist changes explicitly as reloadEditor resets unsaved plugin
        // state.
        await this.dependencies.savePlugin.save();
        // Reload required to re-render the view.
        this.config.reloadEditor();
    }

    getValue({ editingElement }) {
        return JSON.stringify({ id: parseInt(editingElement.dataset.nextPostId) || 0 });
    }

    async apply({ value }) {
        const { id } = JSON.parse(value);
        this.updateRecommendedNextPost(id);
    }

    async clean() {
        this.updateRecommendedNextPost(false);
    }
}

registry.category("website-plugins").add(BlogPageOptionPlugin.id, BlogPageOptionPlugin);
