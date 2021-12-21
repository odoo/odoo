/** @odoo-module */

import { qweb as QWeb, _t } from 'web.core';
import Dialog from 'web.Dialog';
import FormController from 'web.FormController';

const KnowledgeFormController = FormController.extend({
    events: Object.assign({}, FormController.prototype.events, {
        'click .btn-delete': '_onDelete',
        'click .btn-duplicate': '_onDuplicate',
        'click .btn-create': '_onCreate',
        'click .btn-lock': '_onLock',
        'click .btn-move': '_onMove',
        'click .btn-share': '_onShare',
        'click .o_article_create': '_onCreate',
    }),

    // Listeners:

    _onDelete: async function () {
        const { id } = this.getState();
        if (typeof id === 'undefined') {
            return;
        }
        await this._do_delete(id);
    },

    _onDuplicate: async function () {
        const { id } = this.getState();
        if (typeof id === 'undefined') {
            return;
        }
        await this._do_duplicate(id);
    },

    /**
     * @param {Event} event
     */
    _onCreate: async function (event) {
        const $target = $(event.currentTarget);
        if ($target.hasClass('o_article_create')) {
            const $li = $target.closest('li');
            const id = $li.data('article-id');
            await this._do_create(id);
        } else {
            const { id } = this.getState();
            await this._do_create(id);
        }
    },

    _onMove: function () {
        const $content = $(QWeb.render('knowledge.knowledge_move_article_to_modal'));
        const $input = $content.find('input');
        $input.select2({
            ajax: {
                url: '/knowledge/get_articles',
                dataType: 'json',
                /**
                 * @param {String} term
                 * @returns {Object}
                 */
                data: term => {
                    return { query: term, limit: 30 };
                },
                /**
                 * @param {Array[Object]} records
                 * @returns {Object}
                 */
                results: records => {
                    return {
                        results: records.map(record => {
                            return {
                                id: record.id,
                                text: record.name
                            };
                        })
                    };
                }
            },
            /**
             * @param {Object} result
             * @param {integer} result.id
             * @param {string} result.text
             * @returns {String}
             */
            formatResult: result => {
                return '<span class="fa fa-file"></span> ' + _.escape(result.text);
            },
        });
        const dialog = new Dialog(this, {
            title: _t('Move Article To'),
            $content: $content,
            buttons: [{
                text: _t('Save'),
                classes: 'btn-primary',
                click: async () => {
                    const state = this.getState();
                    const src = state.id;
                    const dst = parseInt($input.val());
                    await this._do_move(src, dst);
                    dialog.close();
                }
            }, {
                text: _t('Discard'),
                close: true
            }]
        });
        dialog.open();
    },

    _onNewLink: function () {
        const $content = $(QWeb.render('knowledge.knowledge_add_a_link_modal'));
        const dialog = new Dialog(this, {
            title: _t('Add a Link'),
            $content: $content,
            buttons: [{
                text: _('Save'),
                classes: 'btn-primary',
                click: async () => {
                    console.log('Creating a new link...');
                }
            }, {
                text: _('Discard'),
                click: async () => {
                    console.log('Discard...');
                    dialog.close();
                }
            }]
        });
        dialog.open();
    },

    _onShare: function () {
        const $content = $(QWeb.render('knowledge.knowledge_share_an_article_modal'));
        const dialog = new Dialog(this, {
            title: _t('Share a Link'),
            $content: $content,
            buttons: [{
                text: _('Save'),
                classes: 'btn-primary',
                click: async () => {
                    console.log('sharing the article...');
                }
            }, {
                text: _('Discard'),
                click: async () => {
                    console.log('Discard...');
                    dialog.close();
                }
            }]
        });
        dialog.open();
    },

    /**
     * @param {Event} event
     */
    _onLock: function (event) {
        const $target = $(event.target);
        const $icon = $target.find('i');
        if ($icon.hasClass('fa-lock')) {
            $icon.removeClass('fa-lock');
            $icon.addClass('fa-unlock');
            this._setMode('edit');
        } else {
            $icon.removeClass('fa-unlock');
            $icon.addClass('fa-lock');
            this._setMode('readonly');
        }
    },

    // API calls:

    /**
     * @param {integer} id - Parent id
     */
    _do_create: async function (id) {
        const article = await this._rpc({
            route: `/knowledge/article/create`,
            params: {
                target_parent_id: id
            }
        });
        if (!article) {
            return;
        }
        this._move(
            QWeb.render('knowledge.knowledge_article_template', { article }),
            this.$el.find(`.o_tree [data-article-id="${article.parent_id}"]`)
        );
    },

    /**
     * @param {integer} id - Target id
     */
    _do_delete: async function (id) {
        const result = await this._rpc({
            route: `/knowledge/article/${id}/delete`
        });
        if (result) {
            const $li = this.$el.find(`.o_tree [data-article-id="${id}"]`);
            $li.remove();
        }
    },

    /**
     * @param {integer} id - Target id
     */
    _do_duplicate: async function (id) {
        const result = await this._rpc({
            route: `/knowledge/article/${id}/duplicate`
        });
        console.log('result', result);
    },

    /**
     * @param {integer} src
     * @param {integer} dst
     */
    _do_move: async function (src, dst) {
        const result = await this._rpc({
            route: `/knowledge/article/${src}/move`,
            params: {
                target_parent_id: dst
            }
        });
        if (result) {
            this._move(
                this.$el.find(`.o_tree [data-article-id="${src}"]`),
                this.$el.find(`.o_tree [data-article-id="${dst}"]`)
            );
        }
    },

    // Helpers:

    /**
     * @param {jQuery} $li
     * @param {jQuery} $parent
    */
    _move: function ($li, $parent) {
        if ($parent.length === 0) {
            console.log('no parent');
            return
        }
        let $ul = $parent.find('ul:first');
        if ($ul.length === 0) {
            $ul = $('<ul>');
            $parent.append($ul);
        }
        $ul.append($li);
    },

    /**
     * @override
     */
    _setMode: function () {
        return this._super.apply(this, arguments).then(() => {
            this.renderer.initTree();
        });
    },
});

export {
    KnowledgeFormController,
};