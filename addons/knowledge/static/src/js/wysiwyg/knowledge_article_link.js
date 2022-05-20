/** @odoo-module **/
"use strict";

import Dialog from 'web.Dialog';
import { _t } from 'web.core';

const KnowledgeArticleLinkModal = Dialog.extend({
    template: 'knowledge.wysiwyg_article_link_modal',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/knowledge/static/src/xml/knowledge_editor.xml']
    ),
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        // Set default options:
        options.title = options.title || _t('Link an Article');
        options.buttons = options.buttons || [{
            text: _t('Insert Link'),
            classes: 'btn-primary',
            click: this.save.bind(this)
        }, {
            text: _t('Cancel'),
            close: true
        }];
        this._super(...arguments);
    },

    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        return this._super.apply(this, arguments).then(() => {
            this.initSelect2();
        });
    },

    /**
     * @returns {JQuery}
     */
    getInput: function () {
        return this.$el.find('input');
    },

    initSelect2: function () {
        const $input = this.getInput();
        $input.select2({
            containerCssClass: 'o_knowledge_select2',
            dropdownCssClass: 'o_knowledge_select2',
            ajax: {
                /**
                 * @param {String} term
                 * @returns {Object}
                 */
                data: term => {
                    return { term };
                },
                /**
                 * @param {Object} params - parameters
                 */
                transport: async params => {
                    const { term } = params.data;
                    const results = await this._rpc({
                        model: 'knowledge.article',
                        method: 'search_read',
                        kwargs: {
                            fields: ['id', 'display_name', 'root_article_id'],
                            domain: [['name', '=ilike', `%${term}%`]],
                        },
                    });
                    params.success({ results });
                },
                /**
                 * @param {Object} data
                 * @returns {Object}
                 */
                processResults: data => {
                    return {
                        results: data.results.map(record => {
                            return {
                                id: record.id,
                                display_name: record.display_name,
                                subject: record.root_article_id[1],
                            };
                        })
                    };
                },
            },
            /**
             * @param {Object} data
             * @param {JQuery} container
             * @param {Function} escapeMarkup
             */
            formatSelection: (data, container, escapeMarkup) => {
                return escapeMarkup(data.display_name);
            },
            /**
             * @param {Object} result
             * @param {JQuery} container
             * @param {Object} query
             * @param {Function} escapeMarkup
             */
            formatResult: (result, container, query, escapeMarkup) => {
                const { display_name, subject } = result;
                const markup = [];
                window.Select2.util.markMatch(display_name, query.term, markup, escapeMarkup);
                if (subject !== display_name) {
                    markup.push(`<span class="test-ellipsis small">  -  ${escapeMarkup(subject)}</span>`);
                }
                return markup.join('');
            },
        });
    },

    save: function () {
        const $input = this.getInput();
        const data = $input.select2('data');
        this.trigger('save', data);
    },
});

export {
    KnowledgeArticleLinkModal
};
