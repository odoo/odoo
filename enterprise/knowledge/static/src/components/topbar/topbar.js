/** @odoo-module **/

import { browser } from '@web/core/browser/browser'
import { formatDateTime } from '@web/core/l10n/dates';
import { rpc } from "@web/core/network/rpc";
import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { _t } from "@web/core/l10n/translation";

import { Component, onWillStart, useEffect, useRef, useState } from '@odoo/owl';

import { getRandomIcon } from '@knowledge/js/knowledge_utils';
import KnowledgeHierarchy from '@knowledge/components/hierarchy/hierarchy';
import MoveArticleDialog from '@knowledge/components/move_article_dialog/move_article_dialog';
import PermissionPanel from '@knowledge/components/permission_panel/permission_panel';
import { KnowledgeFormStatusIndicator } from "@knowledge/components/form_status_indicator/form_status_indicator";
import { KNOWLEDGE_READONLY_EMBEDDINGS } from "@knowledge/editor/embedded_components/embedding_sets";
import { READONLY_MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { HistoryDialog } from "@html_editor/components/history_dialog/history_dialog";

class KnowledgeTopbar extends Component {
    static template = "knowledge.KnowledgeTopbar";
    static props = {
        ...standardWidgetProps,
    };
    static components = {
        KnowledgeHierarchy,
        KnowledgeFormStatusIndicator,
        PermissionPanel,
    };

    setup() {
        super.setup();
        this.actionService = useService('action');
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        this.uiService = useService('ui');

        this.buttonSharePanel = useRef('sharePanel_button');
        this.optionsBtn = useRef('optionsBtn');

        this.formatDateTime = formatDateTime;

        this.state = useState({
            displayChatter: false,
            displayHistory: false,
            displayPropertyPanel: !this.articlePropertiesIsEmpty,
            addingProperty: false,
            displaySharePanel: false,
        });
        this.commentsService = useService("knowledge.comments");
        this.commentsState = useState(this.commentsService.getCommentsState());

        this.openChat = useOpenChat('res.users');

        onWillStart(async () => {
            this.isInternalUser = await user.hasGroup('base.group_user');
            this.canCreateArticle = await user.checkAccessRight('knowledge.article', 'create');
        });

        useEffect((optionsBtn) => {
            // Refresh "last edited" and "create date" when opening the options
            // panel
            if (optionsBtn) {
                optionsBtn.addEventListener(
                    'shown.bs.dropdown',
                    () => this._setDates()
                );
            }
        }, () => [this.optionsBtn.el]);


        useEffect(() => {
            // When opening an article via the sidebar (or when moving one),
            // display the properties panel if the article has properties and we are not on mobile.
            if (!uiUtils.isSmall() && !this.articlePropertiesIsEmpty) {
                this.addProperties();
            } else if (this.articlePropertiesIsEmpty && this.state.displayPropertyPanel) {
                // We close the panel if the opened article has no properties and the panel was open.
                this.toggleProperties();
            }
            this.state.addingProperty = false;
        }, () => [this.props.record.resId, this.articlePropertiesIsEmpty]);

        useEffect((shareBtn) => {
            if (shareBtn) {
                shareBtn.addEventListener(
                    // Prevent hiding the dropdown when the invite modal is shown
                    'hide.bs.dropdown', (ev) => {
                        if (this.uiService.activeElement !== document) {
                            ev.preventDefault();
                        }
                });
                shareBtn.addEventListener(
                    'shown.bs.dropdown',
                    () => this.state.displaySharePanel = true
                );
                shareBtn.addEventListener(
                    'hidden.bs.dropdown',
                    () => this.state.displaySharePanel = false
                );
            }
        }, () => [this.buttonSharePanel.el]);
    }

    get addFavoriteLabel(){
        return _t("Add to favorites");
    }

    get removeFavoriteLabel(){
        return _t("Remove from favorites");
    }

    get displayCommentsPanelButton() {
        return (
            this.commentsState.displayMode === "panel" ||
            Object.keys(this.commentsState.threadRecords).length
        );
    }

    /**
     * Adds a random cover using unsplash. If unsplash throws an error (service
     * down/keys unset), opens the cover selector instead.
     * @param {Event} event
     */
    async addCover(event) {
        // Disable button to prevent multiple calls
        event.target.classList.add('disabled');
        this.env.ensureArticleName();
        let res = {};
        try {
            res = await rpc(`/knowledge/article/${this.props.record.resId}/add_random_cover`, {
                query: this.props.record.data.name,
                orientation: 'landscape',
            });
        } catch (e) {
            console.error(e);
        }
        if (res.cover_id) {
            await this.props.record.update({cover_image_id: [res.cover_id]});
        } else {
            // Unsplash keys unset or rate limit exceeded
            this.env.openCoverSelector();
        }
        event.target.classList.remove('disabled');
    }

    /**
     * Add a random icon to the article.
     * @param {Event} event
     */
    async addIcon(event) {
        this.props.record.update({icon: await getRandomIcon()});
    }

    _setDates() {
        if (this.props.record.data.create_date && this.props.record.data.last_edition_date) {
            this.state.createDate = this.props.record.data.create_date.toRelative();
            this.state.editionDate = this.props.record.data.last_edition_date.toRelative();
        }
    }

    get articlePropertiesIsEmpty() {
        return this.props.record.data.article_properties.filter((prop) => !prop.definition_deleted).length === 0;
    }

    toggleProperties() {
        this.state.displayPropertyPanel = !this.state.displayPropertyPanel;
        this.env.bus.trigger('KNOWLEDGE:TOGGLE_PROPERTIES', {displayPropertyPanel: this.state.displayPropertyPanel});
        if (this.state.addingProperty) {
            this.state.addingProperty = false;
        }
    }

    addProperties() {
        this.state.displayPropertyPanel = true;
        this.state.addingProperty = true;
        this.env.bus.trigger('KNOWLEDGE:TOGGLE_PROPERTIES', {displayPropertyPanel: true});
    }

    toggleComments() {
        if (this.commentsState.displayMode === "handler") {
            this.commentsState.displayMode = "panel";
        } else {
            this.commentsState.displayMode = "handler";
        }
    }

    toggleFullWidth() {
        this.props.record.update({full_width: !this.props.record.data.full_width});
        browser.dispatchEvent(new Event("resize"));
    }

    /**
     * Copy the current article in private section and open it.
     */
    async cloneArticle() {
        await this.env._saveIfDirty();
        const articleId = await this.orm.call(
            'knowledge.article',
            'action_clone',
            [this.props.record.resId]
        );
        this.env.openArticle(articleId, true);
    }

    /**
     * Use the browser print as wkhtmltopdf sadly does not handle emojis / embed views / ...
     * (Investigation shows that it would be complicated to add that support).
     *
     * We load the printing assets of knowledge before asking the window to "print".
     * These assets are loaded dynamically and not included in the base backend assets because they
     * alter some generic parts of the layout, which other apps may not want.
     *
     * (Note that those assets are never "unloaded", meaning it requires a reload of the webclient
     * to remove them, which is considered acceptable as very niche).
     *
     */
    async exportToPdf() {
        window.print();
    }

    async setLockStatus(newLockStatus) {
        await this.props.record.model.root.isDirty();
        await this.env._saveIfDirty();
        await this.orm.call(
            'knowledge.article',
            `action_set_${newLockStatus ? 'lock' : 'unlock'}`,
            [this.props.record.resId],
        );
        await this.props.record.load();
    }

    /**
     * Show the Dialog allowing to move the current article.
     */
    async onMoveArticleClick() {
        await this.env._saveIfDirty();
        this.dialog.add(MoveArticleDialog, {knowledgeArticleRecord: this.props.record});
    }

    /**
     * Show/hide the chatter. When showing it, it fetches data required for
     * new messages, activities, ...
     */
    toggleChatter() {
        if (this.props.record.resId) {
            this.state.displayChatter = !this.state.displayChatter;
            this.env.bus.trigger('KNOWLEDGE:TOGGLE_CHATTER', {displayChatter: this.state.displayChatter});
        }
    }
    /**
     * Open the history dialog.
     */
    async openHistory() {
        if (this.props.record.resId) {
            this.state.displayHistory = true;
            await this.env.model.root.save();

            const versionedFieldName = 'body';
            const historyMetadata = this.props.record.data["html_field_history_metadata"]?.[versionedFieldName];
            if (historyMetadata) {
                this.dialog.add(
                    HistoryDialog,
                    {
                        recordId: this.props.record.resId,
                        recordModel: this.props.record.resModel,
                        versionedFieldName: versionedFieldName,
                        historyMetadata: historyMetadata,
                        restoreRequested: (html, close) => {
                            const restoredData = {};
                            restoredData[versionedFieldName] = html;
                            this.props.record.update(restoredData);
                            close();
                        },
                        embeddedComponents: [
                            ...READONLY_MAIN_EMBEDDINGS,
                            ...KNOWLEDGE_READONLY_EMBEDDINGS,
                        ],
                    },
                    {
                        onClose: () => this.state.displayHistory = false
                    }
                );
            }
        }
    }

    async unarchiveArticle() {
        await this.orm.call('knowledge.article', 'action_unarchive', [this.props.record.resId]);
        await this.props.record.load();
    }

    /**
     * Set the value of is_article_item for the current record.
     * @param {boolean} newArticleItemStatus: new is_article_item value
     */
    async setIsArticleItem(newArticleItemStatus) {
        await this.props.record.update({is_article_item: newArticleItemStatus});
    }

    async sendToTrash() {
        await this.orm.call('knowledge.article', 'action_send_to_trash', [this.props.record.resId]);
        await this.actionService.doAction(
            await this.orm.call('knowledge.article', 'action_redirect_to_parent', [this.props.record.resId]),
            {stackPosition: 'replaceCurrentAction'}
        );
    }

    /**
     * @param {Event} event
     * @param {Proxy} member
     */
    async _onMemberAvatarClick(event, userId) {
        event.preventDefault();
        event.stopPropagation();
        if (userId) {
            await this.openChat(userId);
        }
    }
}

export const knowledgeTopbar = {
    component: KnowledgeTopbar,
    fieldDependencies: [
        { name: "create_uid", type: "many2one", relation: "res.users" },
        { name: "display_name", type: "char" },
        { name: "html_field_history_metadata", type: "jsonb" },
        { name: "last_edition_uid", type: "many2one", relation: "res.users" },
        { name: "parent_path", type: "char" },
        { name: "root_article_id", type: "many2one", relation: "knowledge.article" },
    ],
};

registry.category('view_widgets').add('knowledge_topbar', knowledgeTopbar);
