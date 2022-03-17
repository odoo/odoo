odoo.define('knowledge.knowledge_frontend', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');

var QWeb = core.qweb;

publicWidget.registry.KnowledgeWidget = publicWidget.Widget.extend({
    selector: '.o_knowledge_form_view',
    xmlDependencies: ['/knowledge/static/src/xml/knowledge_templates.xml'],
    events: {
        'keyup #knowledge_search': '_searchArticles',
        'click .o_article_caret': '_onFold',
        'click .o_favorites_toggle_button': '_toggleFavourite',
    },

    _searchArticles: function (e) {
        const $tree = $('.o_tree');
        const search = $('#knowledge_search');
        this._traverse($tree, $li => {
            const keyword = search.val().toLowerCase();
            if ($li.text().toLowerCase().indexOf(keyword) >= 0) {
                $li.show();
            }
            else {
                $li.hide();
            }
        })
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

    _toggleFavourite: async function (e) {
        const toggleWidget = $(e.currentTarget);
        const article = await this._rpc({
            route: '/article/toggle_favourite',
            params: {
                article_id: toggleWidget.data('articleId')
            }
        });
        toggleWidget.find('i').toggleClass("fa-star", article.is_favourite).toggleClass("fa-star-o", !article.is_favourite);
        // Add/Remove the article to/from the favourite in the sidebar
        const $favourites = $(this.target).find('.o_tree_favourite');
        let hasFavourites = true;
        if (article.is_favourite) {
            $favourites.append($(QWeb.render("knowledge.knowledge_article_template_frontend", {"article": article})));
        } else {
            $favourites.find(`li[data-article-id="${article.id}"]`).remove();
            hasFavourites = $favourites.find('li').length > 0;
        }
        // if (hasFavourites) {
        $favourites.closest('section').toggleClass('d-none', !hasFavourites);
        const hasDocuments = hasFavourites || $(this.target).find('.o_tree_workspace').find('li').length > 0;
        $favourites.closest('.o_knowledge_aside').toggleClass('d-none', !hasDocuments).toggleClass('d-flex', hasDocuments);
        //}
    }
});
});
