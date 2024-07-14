/** @odoo-module **/

import { Component } from '@odoo/owl';
import { renderToElement } from "@web/core/utils/render";
import { Wysiwyg } from '@web_editor/js/wysiwyg/wysiwyg';
import { PromptEmbeddedViewNameDialog } from '@knowledge/components/prompt_embedded_view_name_dialog/prompt_embedded_view_name_dialog';
import {
    isSelectionInSelectors,
    preserveCursor,
    setCursorEnd,
} from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { VideoSelectorDialog } from '@knowledge/components/video_selector_dialog/video_selector_dialog';
import { ArticleSelectionBehaviorDialog } from '@knowledge/components/behaviors/article_behavior_dialog/article_behavior_dialog';
import {
    encodeDataBehaviorProps,
} from "@knowledge/js/knowledge_utils";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { KnowledgeMediaDialog } from '@knowledge/components/media_dialog/knowledge_media_dialog';

patch(Wysiwyg.prototype, {
    /**
     * @override
     */
    async resetEditor() {
        await super.resetEditor(...arguments);
        this.$editable[0].dispatchEvent(new Event('mount_knowledge_behaviors'));
    },
    /**
     * @override
     */
    _getEditorOptions() {
        const finalOptions = super._getEditorOptions(...arguments);
        const onHistoryResetFromSteps = finalOptions.onHistoryResetFromSteps;
        finalOptions.onHistoryResetFromSteps = () => {
            onHistoryResetFromSteps();
            if (this._onHistoryResetFromSteps) {
                this._onHistoryResetFromSteps();
            }
        };
        return {
            allowCommandFile: true,
            ...finalOptions,
        };
    },
    /**
     * @override
     * @returns {Array[Object]}
     */
    _getPowerboxOptions() {
        const options = super._getPowerboxOptions();
        const {commands, categories} = options;
        categories.push({ name: _t('Media'), priority: 50 });
        commands.push({
            category: _t('Media'),
            name: _t('Article'),
            priority: 10,
            description: _t('Link an article'),
            fontawesome: 'fa-file',
            isDisabled: () => this.options.isWebsite || this.options.inIframe,
            callback: () => {
                this._insertArticleLink();
            },
        });

        if (this.options.knowledgeCommands) {
            categories.push(
                { name: _t('Knowledge'), priority: 11 },
                { name: _t('Knowledge Databases'), priority: 10 }
            );

            commands.push({
                category: _t('Knowledge'),
                name: _t('File'),
                priority: 20,
                description: _t('Upload a file'),
                fontawesome: 'fa-file',
                isDisabled: () => isSelectionInSelectors('.o_knowledge_behavior_anchor') || !this.options.allowCommandFile,
                callback: () => {
                    this.openMediaDialog({
                        noVideos: true,
                        noImages: true,
                        noIcons: true,
                        noDocuments: true,
                        MediaDialog: KnowledgeMediaDialog,
                    });
                }
            }, {
                category: _t('Knowledge'),
                name: _t('Clipboard'),
                priority: 10,
                description: _t('Add a clipboard section'),
                fontawesome: 'fa-pencil-square',
                isDisabled: () => isSelectionInSelectors('.o_knowledge_behavior_anchor'),
                callback: () => {
                    this._insertTemplate();
                },
            }, {
                category: _t('Knowledge'),
                name: _t('Table Of Content'),
                priority: 30,
                description: _t('Highlight the structure of this article'),
                fontawesome: 'fa-bookmark',
                isDisabled: () => isSelectionInSelectors('.o_knowledge_behavior_anchor, table'),
                callback: () => {
                    this._insertTableOfContent();
                },
            }, {
                category: _t('Knowledge Databases'),
                name: _t('Item Kanban'),
                priority: 40,
                description: _t('Insert a Kanban view of article items'),
                fontawesome: 'fa-th-large',
                isDisabled: () => isSelectionInSelectors('.o_knowledge_behavior_anchor, .o_editor_banner, table'),
                callback: () => {
                    const restoreSelection = preserveCursor(this.odooEditor.document);
                    const viewType = 'kanban';
                    this._openEmbeddedViewDialog(viewType, async (name) => {
                        await this.orm.call(
                            'knowledge.article',
                            'create_default_item_stages',
                            [[this.options.recordInfo.res_id]],
                        );
                        this._insertEmbeddedView('knowledge.knowledge_article_item_action_stages', undefined, viewType, name, restoreSelection, {
                            active_id: this.options.recordInfo.res_id,
                            default_parent_id: this.options.recordInfo.res_id,
                            default_is_article_item: true,
                        });
                    }, restoreSelection);
                }
            }, {
                category: _t('Knowledge Databases'),
                name: _t('Item Cards'),
                priority: 39,
                description: _t('Insert a Card view of article items'),
                fontawesome: 'fa-address-card',
                isDisabled: () => isSelectionInSelectors('.o_editor_banner, .o_knowledge_behavior_anchor, table'),
                callback: () => {
                    const restoreSelection = preserveCursor(this.odooEditor.document);
                    const viewType = 'kanban';
                    this._openEmbeddedViewDialog(viewType, name => {
                        this._insertEmbeddedView('knowledge.knowledge_article_item_action', undefined, viewType, name, restoreSelection, {
                            active_id: this.options.recordInfo.res_id,
                            default_parent_id: this.options.recordInfo.res_id,
                            default_is_article_item: true,
                        });
                    }, restoreSelection);
                }
            }, {
                category: _t('Knowledge Databases'),
                name: _t('Item List'),
                priority: 50,
                description: _t('Insert a List view of article items'),
                fontawesome: 'fa-th-list',
                isDisabled: () => isSelectionInSelectors('.o_editor_banner, .o_knowledge_behavior_anchor, table'),
                callback: () => {
                    const restoreSelection = preserveCursor(this.odooEditor.document);
                    const viewType = 'list';
                    this._openEmbeddedViewDialog(viewType, name => {
                        this._insertEmbeddedView('knowledge.knowledge_article_item_action', undefined, viewType, name, restoreSelection, {
                            active_id: this.options.recordInfo.res_id,
                            default_parent_id: this.options.recordInfo.res_id,
                            default_is_article_item: true,
                        });
                    }, restoreSelection);
                }
            }, {
                category: _t('Knowledge Databases'),
                name: _t('Item Calendar'),
                priority: 29,
                description: _t('Insert a Calendar view of article items'),
                fontawesome: 'fa-calendar-plus-o',
                isDisabled: () => isSelectionInSelectors('.o_knowledge_behavior_anchor, table'),
                callback: this._insertItemCalendar.bind(this),
            }, {
                category: _t('Knowledge'),
                name: _t('Index'),
                priority: 60,
                description: _t('Show nested articles'),
                fontawesome: 'fa-list',
                isDisabled: () => isSelectionInSelectors('.o_knowledge_behavior_anchor, table'),
                callback: () => {
                    this._insertArticlesStructure(false);
                }
            }, {
                category: _t('Media'),
                name: _t('Video'),
                priority: 70,
                description: _t('Insert a Video'),
                fontawesome: 'fa-play',
                callback: () => {
                    const restoreSelection = preserveCursor(this.odooEditor.document);
                    this._openVideoSelectorDialog(media => {
                        this._insertVideo(media, restoreSelection);
                    });
                }
            });
        }
        return {...options, commands, categories};
    },
    /**
     * mail is a dependency of Knowledge and @see MailIceServer are a model from
     * mail. When Knowledge is installed, this is always true, meaning that
     * portal users have access to the collaborative mode.
     * @override
     */
    _hasICEServers() {
        return true;
    },
    /**
     * Notify @see FieldHtmlInjector that behaviors need to be injected
     * @see KnowledgeBehavior
     *
     * @param {Element} anchor blueprint for the behavior to be inserted
     * @param {Function} restoreSelection Instructions on where to insert it
     * @param {Function} insert Instructions on how to insert it if it needs
     *                   custom handling
     */
    _notifyNewBehavior(anchor, restoreSelection, insert = null) {
        const type = Array.from(anchor.classList).find(className => className.startsWith('o_knowledge_behavior_type_'));
        this.$editable[0].dispatchEvent(new CustomEvent('mount_knowledge_behaviors', { detail: { behaviorData: {
            anchor,
            behaviorType: type,
            shouldSetCursor: true,
            restoreSelection,
            behaviorStatus: 'new',
            insert,
        }}}));
    },
    /**
     * Insert a /toc block (table of content)
     */
    _insertTableOfContent: function () {
        const restoreSelection = preserveCursor(this.odooEditor.document);
        const tableOfContentBlock = renderToElement('knowledge.AbstractBehaviorBlueprint', {
            behaviorType: "o_knowledge_behavior_type_toc",
        });
        this._notifyNewBehavior(tableOfContentBlock, restoreSelection);
    },
    /**
     * Insert a /structure block.
     * It will list all the articles that are direct children of this one.
     * @param {boolean} childrenOnly
     */
    _insertArticlesStructure: function () {
        const restoreSelection = preserveCursor(this.odooEditor.document);
        const articlesStructureBlock = renderToElement('knowledge.ArticlesStructureBehaviorBlueprint');
        this._notifyNewBehavior(articlesStructureBlock, restoreSelection);
    },
    /**
     * Insert a /clipboard block
     */
    _insertTemplate() {
        const restoreSelection = preserveCursor(this.odooEditor.document);
        const templateBlock = renderToElement('knowledge.AbstractBehaviorBlueprint', {
            behaviorType: "o_knowledge_behavior_type_template",
        });
        this._notifyNewBehavior(templateBlock, restoreSelection);
    },
    /**
     * Insert a /article block (through a dialog)
     */
    _insertArticleLink: function () {
        const restoreSelection = preserveCursor(this.odooEditor.document);
        Component.env.services.dialog.add(ArticleSelectionBehaviorDialog, {
            title: _t('Link an Article'),
            confirmLabel: _t('Insert Link'),
            articleSelected: article => {
                const articleLinkBlock = renderToElement('knowledge.ArticleBehaviorBlueprint', {
                    href: '/knowledge/article/' + article.articleId,
                    data: encodeDataBehaviorProps({
                        article_id: article.articleId,
                        display_name: article.displayName,
                    }),
                });
                const nameNode = document.createTextNode(article.display_name);
                articleLinkBlock.appendChild(nameNode);
                this._notifyNewBehavior(articleLinkBlock, restoreSelection);
            },
            parentArticleId: this.options.recordInfo.res_model === 'knowledge.article' ? this.options.recordInfo.res_id : undefined
        }, {
            onClose: () => {
                restoreSelection();
            }
        });
    },
    /**
     * Inserts a view in the editor
     * @param {String} [actWindowId] - action xml id (specify either this or
     *                 the object)
     * @param {Object} [actWindowObject] - ActionDescription as specified by
     *                 @see action_service
     * @param {String} viewType - View type
     * @param {String} name - Name
     * @param {Function} restoreSelection - function to restore the selection
     *                   to insert the embedded view where the user typed the
     *                   command.
     * @param {Object} context - Context
     * @param {Object} additionalProps - props to pass to the view when loading
     *                 it.
     */
    _insertEmbeddedView: async function (
        actWindowXMLId, actWindowObject, viewType, name, restoreSelection,
        context={}, additionalViewProps=undefined
    ) {
        const actionWindow = actWindowXMLId ? { action_xml_id: actWindowXMLId } : { act_window: actWindowObject };
        const props = {
            ...actionWindow,
            display_name: name,
            view_type: viewType,
            context,
        };
        if (additionalViewProps) {
            props.additionalViewProps = additionalViewProps;
        }
        const behaviorProps = encodeDataBehaviorProps(props);
        const embeddedViewBlock = renderToElement('knowledge.EmbeddedViewBehaviorBlueprint', {
            behaviorProps,
            action_help: actionWindow.act_window?.help,
        });
        this._notifyNewBehavior(embeddedViewBlock, restoreSelection);
        this.env.model.root.update({'full_width': true});
    },
    /**
     * Inserts a video in the editor
     * @param {Object} media
     * @param {function} restoreSelection
     */
    _insertVideo: function (media, restoreSelection) {
        const videoBlock = renderToElement('knowledge.VideoBehaviorBlueprint', {
            behaviorProps: encodeDataBehaviorProps({
                videoId: media.videoId,
                platform: media.platform,
                params: media.params || {}
            })
        });
        this._notifyNewBehavior(videoBlock, restoreSelection);
    },
    /**
     * Insert a behaviorBlueprint programatically. If the wysiwyg is a part of a
     * collaborative peer to peer connection, ensure that the behaviorBlueprint
     * is properly appended even when the content is reset by the collaboration.
     *
     * @param {HTMLElement} behaviorBlueprint element to append to the editable
     */
    appendBehaviorBlueprint(behaviorBlueprint) {
        const restoreSelection = () => {
            // Set the cursor to the end of the article by not normalizing the position.
            // By not normalizing we ensure that we will use the articleś body as the container
            // and not an invisible character.
            return setCursorEnd(this.odooEditor.editable, false);
        }
        const insert = (anchor) => {
            const fragment = this.odooEditor.document.createDocumentFragment();
            // Add a P after the Behavior to be able to continue typing
            // after it
            const p = this.odooEditor.document.createElement('p');
            p.append(this.odooEditor.document.createElement('br'));
            fragment.append(anchor, p);
            const insertedNodes = this.odooEditor.execCommand('insert', fragment);
            if (insertedNodes) {
                insertedNodes[0].scrollIntoView();
                return insertedNodes;
            }
        };
        // Clone behaviorBlueprint to be sure that the nodes are not modified
        // during the first insertion attempt and that the correct nodes
        // are inserted the second time.
        this._notifyNewBehavior(behaviorBlueprint.cloneNode(true), restoreSelection, (anchor) => {
            const insertedNodes = insert(anchor);
            this._onHistoryResetFromSteps = () => {
                this._notifyNewBehavior(behaviorBlueprint.cloneNode(true), restoreSelection, insert);
                this._onHistoryResetFromSteps = undefined;
            };
            return insertedNodes;
        });
        if (behaviorBlueprint.classList.contains('o_knowledge_behavior_type_embedded_view')) {
            this.env.model.root.update({'full_width': true});
        }
    },
    /**
     * Notify a new @see FileBehavior when selecting a file in a
     * @see MediaDialog
     * @see KnowledgeMediaDialog
     *
     * @override
     */
    _onMediaDialogSave(params, element) {
        if (!element?.querySelector('.o_knowledge_behavior_anchor')) {
            return super._onMediaDialogSave(...arguments);
        }
        params.restoreSelection();
        this._notifyNewBehavior(element, params.restoreSelection);
    },
    /**
     * Inserts the dialog allowing the user to specify name for the embedded view.
     * @param {String} viewType
     * @param {Function} save
     */
    _openEmbeddedViewDialog: function (viewType, save, onClose) {
        Component.env.services.dialog.add(PromptEmbeddedViewNameDialog, {
            isNew: true,
            viewType: viewType,
            save: save
        }, {
            onClose: onClose || (() => {}),
        });
    },

    /**
     * Inserts an item calendar view
     */
    _insertItemCalendar: function () {
        const { ItemCalendarPropsDialog } = odoo.loader.modules.get("@knowledge/components/item_calendar_props_dialog/item_calendar_props_dialog");
        const restoreSelection = preserveCursor(this.odooEditor.document);
        // Shows a dialog allowing the user to set the itemCalendarProps
        // (properties used by the itemCalendar view)
        Component.env.services.dialog.add(ItemCalendarPropsDialog, {
            isNew: true,
            knowledgeArticleId: this.options.recordInfo.res_id,
            saveItemCalendarProps: (name, itemCalendarProps) => {
                this._insertEmbeddedView('knowledge.knowledge_article_action_item_calendar', undefined, 'calendar', name, restoreSelection, {
                    active_id: this.options.recordInfo.res_id,
                    default_parent_id: this.options.recordInfo.res_id,
                    default_icon: '📄',
                    default_is_article_item: true,
                }, {
                    itemCalendarProps,
                });
            }
        }, {
            onClose: () => {
                restoreSelection();
            }
        });
    },

    /**
     * Inserts a dialog allowing the user to insert a video
     * @param {function} save
     */
    _openVideoSelectorDialog: function (save) {
        Component.env.services.dialog.add(VideoSelectorDialog, { save });
    }
});
