/** @odoo-module */

import core from 'web.core';
import FormRenderer from 'web.FormRenderer';

const KnowledgeFormRenderer = FormRenderer.extend({
    className: 'o_knowledge_form_view',
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .o_article_caret': '_onFold',
        'click .o_article_dropdown i': '_onIconClick',
        'click .o_article_name': '_onOpen',
    }),

    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super(...arguments);
        this.breadcrumbs = params.breadcrumbs;
    },

    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        core.bus.on('DOM_updated', this, () => {
            console.log('dom update');
        });
        return this._super.apply(this, arguments).then(() => {
            return this.initTree();
        });
    },

    initTree: function () {
        const aside = this.$el.find('.o_sidebar');
        return this._rpc({
            route: '/knowledge/get_tree',
            params: {}
        }).then(res => {
            aside.empty();
            aside.append(res);
            this.createTree();
        }).catch(error => {
            aside.empty();
        });
    },

    createTree: function () {
        this.$el.find('.o_tree').nestedSortable({
            axis: 'y',
            handle: 'div',
            items: 'li',
            listType: 'ul',
            toleranceElement: '> div',
            forcePlaceholderSize: true,
            opacity: 0.6,
            placeholder: 'o_placeholder',
            tolerance: 'pointer',
            helper: 'clone',
            /**
             * @param {Event} event
             * @param {Object} ui
             */
            relocate: (event, ui) => this._onArticleMove(event, ui)
        });

        // We connect the trees:

        this.$el.find('.o_tree.o_tree_workspace').nestedSortable(
            'option',
            'connectWith',
            '.o_tree.o_tree_private'
        );

        this.$el.find('.o_tree.o_tree_private').nestedSortable(
            'option',
            'connectWith',
            '.o_tree.o_tree_workspace'
        );

        // Highlight the active record:

        const $div = this.$el.find(`[data-article-id="${this.state.res_id}"] > div`);
        if ($div.length === 0) {
            return
        }
        $div.addClass('font-weight-bold');
        $div.addClass('bg-light');
    },

    /**
     * When the user moves an article
     * @param {Event} event
     * @param {Object} ui
     */
    _onArticleMove: async function (event, ui) {
        // TODO DBE OR JBN: Dropping an element to the last position in private root does not fire this event, it should
        const params = {};
        const key = 'article-id';
        const $li = $(ui.item);
        const $parent = $li.parents('li');
        if ($parent.length !== 0) {
            params.target_parent_id = $parent.data(key);
        } else {
            console.log('no parent');
        }
        const $sibling = $li.next();
        if ($sibling.length !== 0) {
            params.before_article_id = $sibling.data(key);
        }
        if ($li.closest('ul.o_tree_private').length !== 0) {
            params.private = true;
        }
        const result = await this._rpc({
            route: `/knowledge/article/${$li.data(key)}/move`,
            params
        });
        if (result) {
            const $tree = $li.closest('.o_tree');
            this._refreshIcons($tree);
        }
    },

    /**
     * When the user clicks on the caret to hide and show some files
     * @param {Event} event
     */
    _onFold: function (event) {
        event.stopPropagation();
        const $button = $(event.currentTarget);
        const $icon = $button.find('i');
        const $li = $button.closest('li');
        const $ul = $li.find('ul');
        if ($ul.length !== 0) {
            $ul.toggle();
            if ($ul.is(':visible')) {
                $icon.removeClass('fa-caret-right');
                $icon.addClass('fa-caret-down');
            } else {
                $icon.removeClass('fa-caret-down');
                $icon.addClass('fa-caret-right');
            }
        }
    },

    /**
     * When the user clicks on a new icon
     * @param {Event} event
     */
    _onIconClick: async function (event) {
        event.stopPropagation();
        const $target = $(event.target);
        const $li = $target.closest('li');
        const id = $li.data('article-id');
        const name = $target.data('icon-name');
        const result = await this._rpc({
            model: 'knowledge.article',
            method: 'write',
            args: [[id], { icon: name }],
        });
        if (result) {
            this.$el.find(`[data-article-id="${id}"]`).each(function() {
                const $icon = $(this).find('.o_article_icon:first i');
                $icon.removeClass();
                $icon.addClass(`fa fa-fw ${name}`);
            });
        }
    },

    /**
     * Opens the selected record.
     * @param {Event} event
     */
    _onOpen: async function (event) {
        event.stopPropagation();
        const $li = $(event.target).closest('li');
        this.do_action('knowledge.action_home_page', {
            additional_context: {
                res_id: $li.data('article-id')
            }
        });
    },

    /**
     * Refresh the icons
     * @param {jQuery} $tree
     */
    _refreshIcons: function ($tree) {
        this._traverse($tree, $li => {
            if ($li.has('ol').length > 0) {
                // todo
            } else {
                // todo
            }
        });
    },

    /**
     * @override
     * @returns {Promise}
     */
    _renderView: async function () {
        const result = await this._super.apply(this, arguments);
        this._renderBreadcrumb();
        return result;
    },

    _renderBreadcrumb: function () {
        const items = this.breadcrumbs.map(payload => {
            const $a = $('<a href="#"/>');
            $a.text(payload.title);
            $a.click(() => {
                this.trigger_up('breadcrumb_clicked', payload);
            });
            const $li = $('<li class="breadcrumb-item"/>');
            $li.append($a);
            return $li;
        });
        const $container = this.$el.find('.breadcrumb');
        $container.prepend(items);
    },

    /**
     * Helper function to traverses the nested list (dfs)
     * @param {jQuery} $tree
     * @param {Function} callback
     */
    _traverse: function ($tree, callback) {
        const stack = $tree.children('li').toArray();
        while (stack.length > 0) {
            const $li = $(stack.shift());
            const $ul = $li.children('ul');
            callback($li);
            if ($ul.length > 0) {
                stack.unshift(...$ul.children('li').toArray());
            }
        }
    },
});

export {
    KnowledgeFormRenderer,
};
