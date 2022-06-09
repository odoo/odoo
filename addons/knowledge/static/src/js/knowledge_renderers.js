/** @odoo-module */

import PermissionPanelWidget from './widgets/knowledge_permission_panel.js';
import EmojiPickerWidget from './widgets/knowledge_emoji_picker.js';
import FormRenderer from 'web.FormRenderer';
import KnowledgeTreePanelMixin from '@knowledge/js/tools/tree_panel_mixin';
import { qweb as QWeb } from 'web.core';

import { ChatterContainer } from '@mail/components/chatter_container/chatter_container';
import { ComponentWrapper } from 'web.OwlCompatibility';

class ChatterContainerWrapperComponent extends ComponentWrapper {}

const KnowledgeArticleFormRenderer = FormRenderer.extend(KnowledgeTreePanelMixin, {
    className: 'o_knowledge_form_view',
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .btn-chatter.active': '_onCloseChatter',
        'click .btn-chatter:not(.active)': '_onOpenChatter',
        'click .btn-create': '_onBtnCreateClick',
        'click .btn-duplicate': '_onBtnDuplicateClick',
        'click .btn-move': '_onBtnMoveClick',
        'click .breadcrumb a[data-controller-id]': '_onBreadcrumbItemClick',
        'click .o_article_caret': '_onFold',
        'click .o_article_name': '_onOpen',
        'click .o_article_create': '_onBtnArticleCreateClick',
        'click .o_section_create': '_onBtnSectionCreateClick',
        'click .o_knowledge_share_panel': '_preventDropdownClose',
        'click .o_knowledge_more_options_panel': '_preventDropdownClose',
    }),
    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super(...arguments);
        this.breadcrumbs = params.breadcrumbs;
        /**
         * Manually set values for the chatter props as it is custom handled
         * and not loaded with the view (oe_chatter is not used in Knowledge,
         * the chatter is only rendered when the user clicks on the button).
         */
        this.chatterFields = {
            // `knowledge.article` has `mail.activity.mixin`
            hasActivities: true,
            hasFollowers: true,
            hasMessageIds: true,
        };
    },
    /**
     * Called when the chatter triggers a reload on the Form view with the
     * param 'keepChanges=true'. In this case, we only need to update the
     * chatter.
     *
     * @returns {Promise}
     */
    updateChatter: function () {
        if (this._chatterContainerComponent && this.state.res_id) {
            const props = this._makeChatterContainerProps();
            return this._chatterContainerComponent.update(props);
        }
        this._closeChatter();
        return Promise.resolve();
    },
    /**
     * @private
     */
    _closeChatter: function () {
        const chatter = this.el.querySelector('.o_knowledge_chatter_container');
        while (chatter.firstChild) {
            chatter.removeChild(chatter.firstChild);
        }
        if (this._chatterContainerComponent) {
            this._chatterContainerComponent.destroy();
            this._chatterContainerComponent = undefined;
        }
    },
    /**
     * @param {Event} event
     */
    _onBreadcrumbItemClick: function (event) {
        const $target = $(event.target);
        this.trigger_up('breadcrumb_clicked', {
            controllerID: $target.data('controller-id'),
        });
    },
    /**
     * Callback function called when the user clicks on the '+' sign of an article
     * list item. The callback function will create a new article under the target article.
     * @param {Event} event
     */
    _onBtnArticleCreateClick: function (event) {
        const $target = $(event.currentTarget);
        const $li = $target.closest('li');
        this.trigger_up('create', {
            target_parent_id: $li.data('article-id')
        });
    },
    /**
     * @param {Event} event
     */
    _onBtnChatterClick: function (event) {
        const $chatter = $('.o_knowledge_chatter');
        $chatter.toggleClass('d-none');
        $('.btn-chatter').toggleClass('active');
    },
    /**
     * @param {Event} event
     */
    _onBtnCreateClick: function (event) {
        this.trigger_up('create', {
            category: 'private'
        });
    },
    /**
     * @param {Event} event
     */
    _onBtnDuplicateClick: function (event) {
        event.preventDefault();
        this.trigger_up('duplicate', {});
    },
    /**
     * @param {Event} event
     */
    _onBtnMoveClick: function (event) {
        event.preventDefault();
        this.trigger_up('open_move_to_modal', {});
    },
    /**
     * Callback function called when the user clicks on the '+' sign of a section
     * (workspace, private, shared). The callback function will create a new article
     * on the root of the target section.
     * @param {Event} event
     */
    _onBtnSectionCreateClick: function (event) {
        const $target = $(event.currentTarget);
        const $section = $target.closest('.o_section');
        this.trigger_up('create', {
            category: $section.data('section')
        });
    },
    /**
     * Update the btn-chatter appearance and hide the chatter section in the
     * view. Closes the chatter.
     *
     * @private
     */
    _onCloseChatter: function () {
        this.el.querySelector('.o_knowledge_chatter').classList.add('d-none');
        this.el.querySelector('.btn-chatter').classList.remove('active');
        this._closeChatter();
    },
    /**
     * Opens the selected record.
     * @param {Event} event
     */
    _onOpen: async function (event) {
        event.stopPropagation();
        const $li = $(event.target).closest('li');
        this.do_action('knowledge.ir_actions_server_knowledge_home_page', {
            stackPosition: 'replaceCurrentAction',
            additional_context: {
                res_id: $li.data('article-id')
            }
        });
    },
    /**
     * Update tbe btn-chatter appearance and show the chatter section in the
     * view. Open the chatter.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onOpenChatter: async function (ev) {
        ev.stopPropagation();
        if (this.state.res_id) {
            this.el.querySelector('.o_knowledge_chatter').classList.remove('d-none');
            this.el.querySelector('.btn-chatter').classList.add('active');
            await this._renderChatter();
        }
    },
    /**
     * By default, Bootstrap closes automatically the dropdown menu when the user
     * clicks inside it. To avoid that behavior, we will add a new event listener
     * on the dropdown menu that will prevent the click event from bubbling up and
     * triggering the listener closing the dropdown menu.
     * @param {Event} event
     */
    _preventDropdownClose: function (event) {
        event.stopPropagation();
    },
    _renderArticleEmoji: function () {
        const { data } = this.state;
        const $dropdown = this.$('.o_knowledge_icon > .o_article_emoji_dropdown');
        $dropdown.attr('data-article-id', this.state.res_id);
        $dropdown.find('.o_article_emoji').text(data.icon || '');
    },
    /**
     * Renders the breadcrumb
     */
    _renderBreadcrumb: function () {
        const items = this.breadcrumbs.map(payload => {
            return QWeb.render('knowledge.knowledge_breadcrumb_item', { payload });
        });
        this.$('.breadcrumb').prepend(items);
    },
    /**
     * Render and mount the chatter of the current record.
     *
     * @private
     * @returns {Promise}
     */
    _renderChatter: async function () {
        if (!this.state.res_id) {
            return;
        }
        this._closeChatter();
        const props = this._makeChatterContainerProps();
        this._chatterContainerComponent = new ChatterContainerWrapperComponent(
            this,
            ChatterContainer,
            props
        );
        const target = this.el.querySelector('.o_knowledge_chatter_container');
        await this._chatterContainerComponent.mount(target);
    },

    /**
     * Attaches an emoji picker widget to every emoji dropdown of the container.
     * Note: The widget will be attached to the view when the user clicks on
     * the dropdown menu for the first time.
     * @param {JQuery} [$container]
     */
    _renderEmojiPicker: function ($container) {
        $container = $container || this.$el;
        $container.find('.o_article_emoji_dropdown').one('click', event => {
            const $dropdown = $(event.currentTarget);
            const picker = new EmojiPickerWidget(this, {
                article_id: $dropdown.data('article-id')
            });
            picker.attachTo($dropdown);
        });
    },
    /**
     * Renders the permission panel
     */
    _renderPermissionPanel: function () {
        this.$('.btn-share').one('click', event => {
            const $container = this.$('.o_knowledge_permission_panel');
            const panel = new PermissionPanelWidget(this, {
                article_id: this.state.data.id,
                user_permission: this.state.data.user_permission
            });
            panel.attachTo($container);
        });
    },
    /**
     * @override
     * @returns {Promise}
     */
    _renderView: async function () {
        const result = await this._super.apply(this, arguments);
        this._renderBreadcrumb();
        await this._renderTree(this.state.res_id, '/knowledge/tree_panel');
        this._renderArticleEmoji();
        this._renderPermissionPanel();
        this._setResizeListener();
        return result;
    },
    /**
     * @param {integer} id - Article id
     * @param {String} unicode
     */
    _setEmoji: function (id, emoji) {
        const emojis = this.$(`.o_article_emoji_dropdown[data-article-id="${id}"] > .o_article_emoji`);
        emojis.text(emoji || '');
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
        const $resizer = this.$('.o_knowledge_article_form_resizer');
        $resizer.on('pointerdown', event => {
            event.preventDefault();
            $(document).on('pointermove', onPointerMove);
            $(document).one('pointerup', onPointerUp);
        });
    },
    /**
     * Initializes the drag-and-drop behavior of the tree listing all articles.
     * Once this function is called, the user will be able to move an article
     * in the tree hierarchy by dragging an article around.
     * When an article is moved, the script will send an rpc call to the server
     * and the drag-and-drop behavior will be deactivated while the request is pending.
     * - If the rpc call succeeds, the drag-and-drop behavior will be reactivated.
     * - If the rpc call fails, the change will be undo and the drag-and-drop
     *   behavior will be reactivated.
     * Unfortunately, `nestedSortable` can only restore one transformation. Disabling
     * the drag-and-drop behavior will ensure that the tree structure can be restored
     * if something went wrong.
     */
    _setTreeListener: function () {
        const $sortable = this.$('.o_tree');
        $sortable.nestedSortable({
            axis: 'y',
            handle: 'div',
            items: 'li',
            listType: 'ul',
            toleranceElement: '> div',
            forcePlaceholderSize: true,
            opacity: 0.6,
            placeholder: 'bg-info',
            tolerance: 'pointer',
            helper: 'clone',
            cursor: 'grabbing',
            cancel: '.readonly',
            /**
             * @param {Event} event
             * @param {Object} ui
             */
            stop: (event, ui) => {
                $sortable.sortable('disable');

                const $li = $(ui.item);
                const $section = $li.closest('section');
                const $parent = $li.parentsUntil('.o_tree', 'li');

                const data = {
                    article_id: $li.data('article-id'),
                    oldCategory: $li.data('category'),
                    newCategory: $section.data('section')
                };

                if ($parent.length > 0) {
                    data.target_parent_id = $parent.data('article-id');
                }
                const $next = $li.next();
                if ($next.length > 0) {
                    data.before_article_id = $next.data('article-id');
                }
                $li.siblings('.o_knowledge_empty_info').addClass('d-none');
                this.$('.o_knowledge_empty_info:only-child').removeClass('d-none');
                this.trigger_up('move', {...data,
                    onSuccess: () => {
                        const id = $li.data('parent-id');
                        if (typeof id !== 'undefined') {
                            const $parent = this.$(`.o_article[data-article-id="${id}"]`);
                            if (!$parent.children('ul').is(':parent')) {
                                const $caret = $parent.find('> .o_article_handle > .o_article_caret');
                                $caret.remove();
                            }
                        }
                        if ($parent.length > 0) {
                            const $handle = $parent.children('.o_article_handle:first');
                            if ($handle.children('.o_article_caret').length === 0) {
                                const $caret = $(QWeb.render('knowledge.knowledge_article_caret', {}));
                                $handle.prepend($caret);
                            }
                        }
                        $li.data('parent-id', $parent.data('article-id'));
                        $li.attr('data-parent-id', $parent.data('article-id'));
                        $li.data('category', data.newCategory);
                        $li.attr('data-category', data.newCategory);
                        let $children = $li.find('.o_article');
                        $children.each((_, child) => {
                            $(child).data('category', data.newCategory);
                            $(child).attr('data-category', data.newCategory);
                        });
                        $sortable.sortable('enable');
                    },
                    onReject: () => {
                        /**
                         * When a move between two connected nestedSortable
                         * trees is canceled, more than one operation may be
                         * undone (library bug). To bypass sortable('cancel'),
                         * the last moved $item is returned at its original
                         * location (which may have to be restored too if it was
                         * cleaned), and a 'change' event is triggered from that
                         * rectified position for consistency (see the
                         * nestedSortable library).
                         */
                        const $item = ui.item.data('nestedSortableItem');
                        if ($item.domPosition.prev) {
                            // Restore $item position after its previous sibling
                            $item.domPosition.prev.after($item.currentItem[0]);
                        } else {
                            // Restore $item as the first child of the parent ul
                            $item.domPosition.parent.prepend($item.currentItem[0]);
                            if (!$item.domPosition.parent.parentElement) {
                                // The ul was cleaned from the document since it
                                // was empty, so it has to be restored too
                                const offsetParent = $item.offsetParent[0];
                                offsetParent.append($item.domPosition.parent);
                            }
                        }
                        // For consistency with the nestedSortable library,
                        // trigger the 'change' event from the moved $item
                        $item._trigger('change', null, $item._uiHash());
                        $sortable.sortable('enable');
                        this.$('.o_knowledge_empty_info').addClass('d-none');
                        this.$('.o_knowledge_empty_info:only-child').removeClass('d-none');
                    }
                });
            },
        });

        // Allow drag and drop between sections:

        this.$('section[data-section="workspace"] .o_tree').nestedSortable(
            'option',
            'connectWith',
            'section[data-section="private"] .o_tree'
        );
        this.$('section[data-section="private"] .o_tree').nestedSortable(
            'option',
            'connectWith',
            'section[data-section="workspace"] .o_tree'
        );
        // connectWith both workspace and private sections:
        this.$('section[data-section="shared"] .o_tree').nestedSortable(
            'option',
            'connectWith',
            'section[data-section="workspace"] .o_tree, section[data-section="private"] .o_tree'
        );
    },
});

export {
    KnowledgeArticleFormRenderer,
};
