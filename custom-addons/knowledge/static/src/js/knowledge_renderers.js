/** @odoo-module */

import { FormRenderer } from '@web/views/form/form_renderer';
import { KnowledgeCoverDialog } from '@knowledge/components/knowledge_cover/knowledge_cover_dialog';
import { useService } from "@web/core/utils/hooks";
import { useChildSubEnv, useEffect, useExternalListener, useRef } from "@odoo/owl";

export class KnowledgeArticleFormRenderer extends FormRenderer {

    //--------------------------------------------------------------------------
    // Component
    //--------------------------------------------------------------------------
    setup() {
        super.setup();

        this.actionService = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.userService = useService("user");

        this.root = useRef('compiled_view_root');

        useChildSubEnv({
            openCoverSelector: this.openCoverSelector.bind(this),
            config: this.env.config,
            _resizeNameInput: this._resizeNameInput.bind(this),
            toggleFavorite: this.toggleFavorite.bind(this),
            _saveIfDirty: this._saveIfDirty.bind(this),
        });

        useExternalListener(document, "click", event => {
            if (event.target.classList.contains("o_nocontent_create_btn")) {
                this.env.createArticle("private");
            }
        });

        useEffect((isInEdition, root) => {
            if (root && isInEdition) {
                const element = root.el.querySelector(".o_knowledge_editor .note-editable[contenteditable]");
                if (element) {
                    element.focus();
                    document.dispatchEvent(new Event("selectionchange", {}));
                }
            }
        }, () => [
            this.props.record.isInEdition,
            this.root,
            this.props.record.resId
        ]);
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

    /**
     * Resize the name input by updating the value of the span hidden behind
     * the input.
     */
    _resizeNameInput(name) {
        this.root.el.querySelector('.o_breadcrumb_article_name_container > span').innerText = name;
    }

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
