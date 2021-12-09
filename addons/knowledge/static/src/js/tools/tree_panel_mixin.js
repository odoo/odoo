/** @odoo-module **/

export default {
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * Renders the tree listing all articles.
     * To minimize loading time, the function will initially load the root articles.
     * The other articles will be loaded lazily: The user will have to click on
     * the carret next to an article to load and see their children.
     * The id of the unfolded articles will be cached so that they will
     * automatically be displayed on page load.
     * @param {integer} active_article_id
     * @param {String} route
     */
    _renderTree: async function (active_article_id, route) {
        const $container = this.$('.o_knowledge_tree');
        const portalReadonlyMode = $container.data('portalReadonlyMode');
        let unfoldedArticles = localStorage.getItem('unfoldedArticles');
        unfoldedArticles = unfoldedArticles ? unfoldedArticles.split(";").map(Number) : false;
        return this._rpc({
            route: route,
            params: {
                active_article_id: active_article_id,
                unfolded_articles: unfoldedArticles,
            }
        }).then(htmlTree => {
            $container.empty();
            $container.append(htmlTree);
            if (!portalReadonlyMode) {
                this._setTreeListener();
                this._renderEmojiPicker();
            }
            this._setTreeFavoriteListener();
        }).catch(error => {
            $container.empty();
        });
    },

    /**
     * Initializes the drag-and-drop behavior of the favorite.
     * Once this function is called, the user will be able to reorder their favorites.
     * When a favorite is reordered, the script will send an rpc call to the server
     * and the drag-and-drop behavior will be deactivated while the request is pending.
     * - If the rpc call succeeds, the drag-and-drop behavior will be reactivated.
     * - If the rpc call fails, the change will be undo and the drag-and-drop
     *   behavior will be reactivated.
     * Unfortunately, `sortable` can only restore one transformation. Disabling
     * the drag-and-drop behavior will ensure that the list structure can be restored
     * if something went wrong.
     */
    _setTreeFavoriteListener: function () {
        const $sortable = this.$('.o_tree_favorite');
        $sortable.sortable({
            axis: 'y',
            items: 'li',
            cursor: 'grabbing',
            forcePlaceholderSize: true,
            placeholder: 'o_placeholder',
            /**
             * @param {Event} event
             * @param {Object} ui
             */
            stop: (event, ui) => {
                const favorite_ids = $sortable.find('.o_article').map(function () {
                    return $(this).data('favorite-article-id');
                }).get();
                $sortable.sortable('disable');
                this._rpc({
                    route: '/web/dataset/resequence',
                    params: {
                        model: "knowledge.article.favorite",
                        ids: favorite_ids,
                        offset: 1,
                    }
                }).then(() => {
                    $sortable.sortable('enable');
                }).catch(() => {
                    $sortable.sortable('cancel');
                    $sortable.sortable('enable');
                });
            },
        });
    },

    /**
     * Callback function called when the user clicks on the carret of an article
     * The function will load the children of the article and append them to the
     * dom. Then, the id of the unfolded article will be added to the cache.
     * (see: `_renderTree`).
     * @param {Event} event
     */
    _onFold: async function (event) {
        event.stopPropagation();
        const $button = $(event.currentTarget);
        const $icon = $button.find('i');
        const $li = $button.closest('li');
        const $ul = $li.find('ul');
        let unfoldedArticles = localStorage.getItem('unfoldedArticles');
        unfoldedArticles = unfoldedArticles ? unfoldedArticles.split(";") : [];
        const articleId = $li.data('articleId').toString();
        if ($ul.is(':visible')) {
            if (unfoldedArticles.indexOf(articleId) !== -1) {
                unfoldedArticles.splice(unfoldedArticles.indexOf(articleId), 1);
            }
            $icon.removeClass('fa-caret-down');
            $icon.addClass('fa-caret-right');
        } else {
            if ($ul.length === 0) {
                // Call the children content
                const children = await this._rpc({
                    route: '/knowledge/tree_panel/children',
                    params: {
                        parent_id: $li.data('articleId')
                    }
                });
                $li.append($('<ul/>').append(children));
            }
            if (unfoldedArticles.indexOf(articleId) === -1) {
                unfoldedArticles.push(articleId);
            }
            $icon.removeClass('fa-caret-right');
            $icon.addClass('fa-caret-down');
        }
        $ul.toggle();
        localStorage.setItem('unfoldedArticles', unfoldedArticles.join(";"));
    }
};

