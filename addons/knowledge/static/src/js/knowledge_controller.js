/** @odoo-module */

import { _t, bus } from 'web.core';
import Dialog from 'web.Dialog';
import FormController from 'web.FormController';
import { MoveArticleToDialog } from './widgets/knowledge_dialogs.js';
import emojis from '@mail/js/emojis';

const disallowedEmojis = ['💩', '👎', '💔', '😭', '😢', '😐', '😕', '😞', '😢', '💀'];
const emojisRandomPickerSource = emojis.filter(emoji => !disallowedEmojis.includes(emoji.unicode));

const KnowledgeArticleFormController = FormController.extend({
    events: Object.assign({}, FormController.prototype.events, {
        'click .o_knowledge_add_icon': '_onAddRandomIcon',
        'click .o_knowledge_add_cover': '_onAddCover',
        'click #knowledge_search_bar': '_onSearch',
        'click .o_breadcrumb_article_name': '_onArticleBreadcrumbClick',
        'change .o_breadcrumb_article_name': '_onRename',
        'click i.o_toggle_favorite': '_onToggleFavorite',
        'input .o_breadcrumb_article_name': '_adjustInputSize',
    }),

    custom_events: Object.assign({}, FormController.prototype.custom_events, {
        create: '_onCreate',
        duplicate: '_onDuplicate',
        move: '_onMove',
        open_move_to_modal: '_onOpenMoveToModal',
        reload_tree: '_onReloadTree',
        emoji_click: '_onEmojiClick',
    }),

    /**
     * Register the fact that the current @see FormController is one from
     * Knowledge in order not to try and search for a matching record for
     * @see KnowledgeService .
     *
     * @override
     */
    init: function (parent, model, renderer, params) {
        /**
         * This property is used to specify that the current form view will
         * get/use records stored in the @see KnowledgeService instead of
         * replacing them (default). TODO ABD: maybe set this as an option of
         * the form view (XML) so that other form views can easily specify that
         * they will get/use records from the KnowledgeService instead of
         * providing them.
         */
        this.ignoreKnowledgeRecordSearch = true;
        this.renderer = renderer;
        this._super.apply(this, arguments);
        this.onFieldSavedListeners = new Map();
    },

    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        return this._super.apply(this, arguments).then(() => {
            this.onFieldSaved('icon', unicode => {
                const { id } = this.getState();
                this.renderer._setEmoji(id, unicode);
            });
        });
    },

    // Listeners:

    _onAddRandomIcon: function() {
        this.trigger_up('field_changed', {
            dataPointID: this.handle,
            changes: {
                'icon': emojisRandomPickerSource[Math.floor(Math.random() * emojisRandomPickerSource.length)].unicode,
            }
        });
    },

    _onAddCover: async function() {
        if (this.mode === 'readonly') {
            await this._setMode('edit');
        }
        this.$('.o_input_file').click();
    },

    /**
     * When the user clicks on a field in readonly mode, a new 'quick_edit' event
     * will be triggered. To prevent the view from switching to the edit mode when
     * the article is locked, we will overwrite the `_onQuickEdit` handler. This
     * function will now ignore the event if the article is locked.
     * @override
     */
    _onQuickEdit: function () {
        const { data } = this.model.get(this.handle);
        if (data.is_locked) {
            return;
        }
        this._super.apply(this, arguments);
    },

    /**
     * Callback function called when the user renames the active article.
     * The function will update the name of the articles in the aside block.
     * @param {Event} event
     */
    _onRename: async function (event) {
        var name = event.currentTarget.value;
        if (name.length === 0) {
            name = _t('New Article');
        }
        const id = await this._getId();
        await this._rename(id, name);
    },

    /**
     * When the user clicks on the name of the article, checks if the article
     * name hasn't been set yet. If it hasn't, it will look for a title in the
     * body of the article and set it as the name of the article.
     * @param {Event} event
     */
     _onArticleBreadcrumbClick: async function (event) {
        const name = event.currentTarget.value;
        if (name === _t('New Article')) {
            const $articleTitle = this.$('.o_knowledge_editor h1');
            if ($articleTitle.text().length !== 0) {
                this.$('.o_breadcrumb_article_name').val($articleTitle.text());
                this.trigger_up('field_changed', {
                    dataPointID: this.handle,
                    changes: {
                        'name': $articleTitle.text(),
                    }
                });
                this._rename(await this._getId(), $articleTitle.text());
            }
        }
    },

    /**
     * @param {Event} event
     */
    _adjustInputSize: function (event) {
        event.target.setAttribute('size', event.target.value.length);
    },

    /**
     * @param {OdooEvent} event
     */
    _onDuplicate: async function (event) {
        const handle = await this.model.duplicateRecord(this.handle);
        const { res_id } = this.model.get(handle);
        this.do_action('knowledge.ir_actions_server_knowledge_home_page', {
            additional_context: { res_id }
        });
    },

    /**
     * @param {OdooEvent} event
     */
    _onCreate: async function (event) {
        await this._create(event.data);
    },

    /**
     * @param {Event} event
     */
    _onMove: function (event) {
        this._confirmMove(event.data);
    },

    /**
     * Opens the "Move To" modal
     * @param {OdooEvent} event
     */
    _onOpenMoveToModal: async function (event) {
        const id = await this._getId();
        const state = this.model.get(this.handle);
        const dialog = new MoveArticleToDialog(this, {}, {
            state: state,
            /**
             * @param {String} value
             */
            onSave: async value => {
                const params = { article_id: id };
                if (typeof value === 'number') {
                    params.target_parent_id = value;
                } else {
                    params.newCategory = value;
                    params.oldCategory = state.data.category;
                }
                this._confirmMove({...params,
                    onSuccess: () => {
                        dialog.close();
                        this.reload();
                    },
                    onReject: () => {}
                });
            }
        });
        dialog.open();
    },

    /**
     * @param {Event} event
     */
    _onReloadTree: function (event) {
        // TODO JBN: Create a widget for the tree and reload it without reloading the whole view.
        this.reload();
    },

    /**
     * @param {Event} event
     */
    _onSearch: function (event) {
        // TODO: change to this.env.services.commandes.openMainPalette when form views are migrated to owl
        bus.trigger("openMainPalette", {
            searchValue: "?",
        });
    },

    /**
     * @param {Event} event
     */
    _onToggleFavorite: async function (event) {
        const id = await this._getId();
        const active = await this._toggleFavorite(id);
        const $target = $(event.target);
        $target.toggleClass('fa-star-o', !active);
        $target.toggleClass('fa-star', active);
        $target.attr('title', active ? _t('Remove from favorites') : _t('Add to favorites'));
        this._rpc({
            route: '/knowledge/tree_panel/favorites',
            params: {
                active_article_id: id,
            }
        }).then(template => {
            const $dom = $(template);
            this.$(".o_favorite_container").replaceWith($dom);
            this.renderer._setTreeFavoriteListener();
            this.renderer._renderEmojiPicker($dom);
        });
   },

    /**
     * @param {Event} event
     */
    _onEmojiClick: async function (event) {
        const { id } = this.getState();
        const { articleId, unicode } = event.data;
        if (articleId === id) {
            this.trigger_up('field_changed', {
                dataPointID: this.handle,
                changes: {
                    icon: unicode
                }
            });
        } else {
            const result = await this._rpc({
                model: 'knowledge.article',
                method: 'write',
                args: [[articleId], { icon: unicode }],
            });
            if (result) {
                this.renderer._setEmoji(articleId, unicode);
            }
        }
    },
    // API calls:

    /**
     * @param {Object} data
     * @param {String} data.category
     * @param {integer} data.target_parent_id
     */
    _create: async function (data) {
        const articleId = await this._rpc({
            model: 'knowledge.article',
            method: 'article_create',
            args: [[]],
            kwargs: {
                is_private: data.category === 'private',
                parent_id: data.target_parent_id ? data.target_parent_id : false
            },
        });
        if (!articleId) {
            return;
        }
        this.do_action('knowledge.ir_actions_server_knowledge_home_page', {
            stackPosition: 'replaceCurrentAction',
            additional_context: {
                res_id: articleId
            }
        });
    },

    /**
     * @param {integer} id - Target id
     * @param {string} name - Target Name
     */
    _rename: async function (id, name) {
        this.$(`.o_knowledge_tree .o_article[data-article-id="${id}"] > .o_article_handle > .o_article_name`).text(name);
        this.$(`.o_breadcrumb_article_name`).val(name);
    },

    /**
     * @param {Object} data
     * @param {integer} data.article_id
     * @param {String} data.oldCategory
     * @param {String} data.newCategory
     * @param {integer} [data.target_parent_id]
     * @param {integer} [data.before_article_id]
     * @param {Function} data.onSuccess
     * @param {Function} data.onReject
     */
    _confirmMove: async function (data) {
        data['params'] = {
            is_private: data.newCategory === 'private'
        };
        if (typeof data.target_parent_id !== 'undefined') {
            data['params'].parent_id = data.target_parent_id;
        }
        if (typeof data.before_article_id !== 'undefined') {
            data['params'].before_article_id = data.before_article_id;
        }
        if (data.newCategory === data.oldCategory) {
            await this._move(data);
        } else {
            let message, confirmation_message;
            if (data.newCategory === 'workspace') {
                message = _t("Are you sure you want to move this article to the Workspace? It will be shared with all internal users.");
                confirmation_message = _t("Move to Workspace");
            } else if (data.newCategory === 'private') {
                message = _t("Are you sure you want to move this to private? Only you will be able to access it.");
                confirmation_message = _t("Set as Private");
            }
            Dialog.confirm(this, message, {
                cancel_callback: data.onReject,
                buttons: [{
                    text: confirmation_message,
                    classes: 'btn-primary',
                    close: true,
                    click: async () => {
                        await this._move(data);
                    }
                }, {
                    text: _t("Discard"),
                    close: true,
                    click: data.onReject,
                }],
            });
        }
    },

    /**
     * @param {Object} data
     * @param {integer} data.article_id
     * @param {Function} data.onSuccess
     * @param {Function} data.onReject
     * @param {Object} data.params
     * @return {Promise}
     */
    _move: function (data) {
        return this._rpc({
            model: 'knowledge.article',
            method: 'move_to',
            args: [data.article_id],
            kwargs: data.params
        }).then(result => {
            if (result) {
                data.onSuccess();
            } else {
                data.onReject();
            }
        }).catch(error => {
            data.onReject();
        })
    },

    /**
     * @param {integer} id - article id
     * @returns {Promise}
     */
    _toggleFavorite: function (id) {
        return this._rpc({
            model: 'knowledge.article',
            method: 'action_toggle_favorite',
            args: [id]
        });
    },

    /**
     * @returns {Array[String]}
     */
    _getFieldsToForceSave: function () {
        return ['full_width', 'icon', 'cover'];
    },

    /**
     * @override
     * @param {Event} event
     */
    _onFieldChanged: async function (event) {
        this._super(...arguments);
        const { changes } = event.data;
        for (const field of this._getFieldsToForceSave()) {
            if (changes.hasOwnProperty(field)) {
                await this.saveRecord(this.handle, {
                    reload: false,
                    stayInEdit: true
                });
                return;
            }
        }
    },

    /**
     * @override
     */
    saveRecord: async function () {
        const modifiedFields = await this._super(...arguments);
        const { data } = this.model.get(this.handle);
        for (const field of modifiedFields) {
            if (this.onFieldSavedListeners.has(field)) {
                this.onFieldSavedListeners.get(field).forEach(listener => {
                    listener.call(this, data[field]);
                });
            }
        }
        return modifiedFields;
    },

    /**
     * @param {String} name - field name
     * @param {Function} callback
     */
    onFieldSaved: function (name, callback) {
        if (this.onFieldSavedListeners.has(name)) {
            this.onFieldSavedListeners.get(name).push(callback);
        } else {
            this.onFieldSavedListeners.set(name, [callback]);
        }
    },

    /**
     * @returns {integer}
     */
    _getId: async function () {
        let state = this.getState();
        if (typeof state.id === 'undefined') {
            await this.saveRecord(this.handle);
            state = this.getState();
        }
        return state.id;
    },
});

export {
    KnowledgeArticleFormController,
};
