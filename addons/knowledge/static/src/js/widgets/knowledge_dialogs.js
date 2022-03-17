odoo.define('knowledge.dialogs', function (require) {
'use strict';

const Dialog = require('web.Dialog');
const { _t } = require('web.core');

const MoveArticleToDialog = Dialog.extend({
    template: 'knowledge.knowledge_move_article_to_modal',
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} options
     * @param {Object} props
     */
    init: function (parent, options, props) {
        // Set default options:
        options.title = options.title || _t('Move an Article');
        options.buttons = options.buttons || [{
            text: _t('Ok'),
            classes: 'btn-primary',
            click: this.save.bind(this)
        }, {
            text: _t('Cancel'),
            close: true
        }];
        this._super(...arguments);
        this.props = props;
        // Set template variables:
        const { state } = props;
        this.article_name = state.data.name;
    },

    /**
     * @override
     * @returns
     */
    start: async function () {
        const result = await this._super(...arguments);
        this.initSelect2();
        return result;
    },

    /**
     * @returns {JQuery}
     */
    getInput: function () {
        return this.$el.find('input');
    },

    /**
     * @returns {String}
     */
    getLoggedUserPicture: function () {
        const { context } = this.props.state;
        const origin = window.location.origin;
        return `${origin}/web/image?model=res.users&field=avatar_128&id=${context.uid}`;
    },

    initSelect2: function () {
        const cache = {
            results: [{
                text: _t('Categories'),
                children: [{
                    id: 'private',
                    text: _t('Private'),
                    selected: true
                }, {
                    id: 'workspace',
                    text: _t('Workspace')
                }]
            }]
        };

        const $input = this.getInput();
        $input.select2({
            data: cache,
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
                    const { state } = this.props;
                    const results = await this._rpc({
                        model: 'knowledge.article',
                        method: 'search_read',
                        kwargs: {
                            fields: ['id', 'icon', 'name'],
                            domain: ['&',
                                ['id', '!=', state.data.id],
                                ['name', '=ilike', `%${term}%`],
                            ],
                        },
                    });
                    params.success({ term, results });
                },
                /**
                 * @param {Object} data
                 * @returns {Object}
                 */
                processResults: function (data) {
                    const records = { results: [] };
                    for (const result of cache.results) {
                        if (typeof result.children === 'undefined') {
                            records.results.push(result);
                            continue;
                        }
                        const children = result.children.filter(child => {
                            const text = child.text.toLowerCase();
                            const term = data.term.toLowerCase();
                            return text.indexOf(term) >= 0;
                        });
                        if (children.length > 0) {
                            records.results.push({...result, children});
                        }
                    }
                    if (data.results.length > 0) {
                        records.results.push({
                            text: _t('Articles'),
                            children: data.results.map(record => {
                                return {
                                    id: record.id,
                                    icon: record.icon,
                                    text: record.name,
                                }
                            })
                        });
                    }
                    return records;
                },
            },
            /**
             * @param {Object} data
             * @param {JQuery} container
             * @param {Function} escapeMarkup
             */
            formatSelection: (data, container, escapeMarkup) => {
                const markup = [];
                if (data.id === 'private') {
                    const src = escapeMarkup(this.getLoggedUserPicture());
                    markup.push(`<img src="${src}" class="rounded-circle mr-1"/>`);
                } else if (typeof data.icon !== 'undefined') {
                    markup.push(`<i class="fa fa-w ${escapeMarkup(data.icon)} mr-1"/>`);
                }
                markup.push(escapeMarkup(data.text));
                return markup.join('');
            },
            /**
             * @param {Object} result
             * @param {JQuery} container
             * @param {Object} query
             * @param {Function} escapeMarkup
             */
            formatResult: (result, container, query, escapeMarkup) => {
                const { text } = result;
                const markup = [];
                Select2.util.markMatch(text, query.term, markup, escapeMarkup);
                if (result.id === 'private') {
                    const src = escapeMarkup(this.getLoggedUserPicture());
                    markup.unshift(`<img src="${src}" class="rounded-circle mr-1"/>`);
                } else if (typeof result.icon !== 'undefined') {
                    markup.unshift(`<i class="fa fa-w ${escapeMarkup(result.icon)} mr-1"/>`);
                }
                return markup.join('');
            },
        });
    },

    /**
     * @override
     */
    save: function () {
        const $input = this.getInput();
        const data = $input.select2('data');
        this.props.onSave(data.id);
    },
});

return {
    MoveArticleToDialog,
};
});
