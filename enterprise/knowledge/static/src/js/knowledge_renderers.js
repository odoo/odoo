/** @odoo-module */

import { FormRenderer } from '@web/views/form/form_renderer';
import { KnowledgeCoverDialog } from '@knowledge/components/knowledge_cover/knowledge_cover_dialog';
import { useService } from "@web/core/utils/hooks";
import { useChildSubEnv, useExternalListener, useRef } from "@odoo/owl";

export class KnowledgeArticleFormRenderer extends FormRenderer {

    //--------------------------------------------------------------------------
    // Component
    //--------------------------------------------------------------------------
    setup() {
        super.setup();

        this.actionService = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");

        this.root = useRef('compiled_view_root');

        useChildSubEnv({
            openCoverSelector: this.openCoverSelector.bind(this),
            config: this.env.config,
            toggleFavorite: this.toggleFavorite.bind(this),
            _saveIfDirty: this._saveIfDirty.bind(this),
        });

        useExternalListener(document, "click", event => {
            if (event.target.classList.contains("o_nocontent_create_btn")) {
                this.env.createArticle("private");
            }
        });
    }


    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    openCoverSelector() {
        this.dialog.add(KnowledgeCoverDialog, {
            articleCoverId: this.props.record.data.cover_image_id[0],
            articleName: this.props.record.data.name || "",
            save: (id) => this.props.record.update({cover_image_id: [id]})
        });
    }

    get resId() {
        return this.props.record.resId;
    }

    /**
     * Add/Remove article from favorites and reload the favorite tree.
     * One does not use "record.update" since the article could be in readonly.
     * @param {event} Event
     */
    async toggleFavorite(event) {
        // Save in case name has been edited, so that this new name is used
        // when adding the article in the favorite section.
        await this._saveIfDirty();
        await this.orm.call(this.props.record.resModel, "action_toggle_favorite", [[this.resId]]);
        // Load to have the correct value for 'is_user_favorite'.
        await this.props.record.load();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    async _saveIfDirty() {
        if (await this.props.record.isDirty()) {
            await this.props.record.save();
        }
    }

    _scrollToElement(container, element) {
        const rect = element.getBoundingClientRect();
        container.scrollTo(rect.left, rect.top);
    }
}
