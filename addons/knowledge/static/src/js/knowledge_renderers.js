/** @odoo-module */

import FormRenderer from 'web.FormRenderer';

const KnowledgeFormRenderer = FormRenderer.extend({
    className: 'o_knowledge_form_view',
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .o_article_caret': '_onFold',
        'click .o_article_dropdown i': '_onIconClick',
        'click .o_article_name': '_onOpen',
        'click .o_article_create, .o_section_create': '_onCreate'
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
        return this._super.apply(this, arguments).then(() => {
            return this.initTree();
        });
    },

    initTree: function () {
        const $container = this.$el.find('.o_knowledge_tree');
        return this._rpc({
            route: '/knowledge/get_tree',
            params: {
                res_id: this.state.res_id
            }
        }).then(res => {
            $container.empty();
            $container.append(res);
            // TODO: add active_article class on the article.id == this.state.res_id ??
            this._setTreeListener();
        }).catch(error => {
            $container.empty();
        });
    },

    _setTreeListener: function () {
        const $sortable = this.$el.find('.o_tree');
        $sortable.nestedSortable({
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
            cursor: 'grabbing',
            start: (event, ui) => {
                this.$el.find('aside').toggleClass('dragging', true);
            },
            /**
             * @param {Event} event
             * @param {Object} ui
             */
            stop: (event, ui) => {
                $sortable.sortable('disable');
                this.$el.find('aside').toggleClass('dragging', false);

                const $li = $(ui.item);
                const $section = $li.closest('section');
                const $parent = $li.parentsUntil('.o_tree', 'li');

                const data = {
                    article_id: $li.data('article-id'),
                    category: $section.data('section')
                };

                if ($parent.length > 0) {
                    data.target_parent_id = $parent.data('article-id');
                    const $next = $li.next();
                    if ($next.length > 0) {
                        data.before_article_id = $next.data('article-id');
                    }
                }

                this.trigger_up('move', {...data,
                    onSuccess: () => {
                        $sortable.sortable('enable');
                    },
                    onReject: () => {
                        $sortable.sortable('cancel');
                        $sortable.sortable('enable');
                    }
                });
            },
        });

        // Allow drag and drop between sections:

        const selectors = [
            'section[data-section="workspace"] .o_tree',
            'section[data-section="shared"] .o_tree',
            'section[data-section="private"] .o_tree'
        ];

        selectors.forEach(selector => {
            // Note: An element can be connected to one selector at most.
            this.$el.find(selector).nestedSortable(
                'option',
                'connectWith',
                `.o_tree:not(${selector})`
            );
        });
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
     * @param {Event} event
     */
    _onCreate: function (event) {
        const $target = $(event.currentTarget);
        if ($target.hasClass('o_section_create')) {
            const $section = $target.closest('.o_section');
            this.trigger_up('create', {
                category: $section.data('section')
            });
        } else if ($target.hasClass('o_article_create')) {
            const $li = $target.closest('li');
            this.trigger_up('create', {
                target_parent_id: $li.data('article-id')
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
        this._setResizeListener();
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
     * Enables the user to resize the aside block.
     * Note: When the user grabs the resizer, a new listener will be attached
     * to the document. The listener will be removed as soon as the user releases
     * the resizer to free some resources.
     */
    _setResizeListener: function () {
        /**
         * @param {PointerEvent} event
         */
        const onPointerMove = _.throttle(event => {
            event.preventDefault();
            this.el.style.setProperty('--default-sidebar-size', `${event.pageX}px`);
        }, 100);
        /**
         * @param {PointerEvent} event
         */
        const onPointerUp = event => {
            $(document).off('pointermove', onPointerMove);
        };
        const $resizer = this.$el.find('.o_knowledge_resizer');
        $resizer.on('pointerdown', event => {
            event.preventDefault();
            $(document).on('pointermove', onPointerMove);
            $(document).one('pointerup', onPointerUp);
        });
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
