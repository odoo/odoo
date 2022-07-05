
/** @odoo-module */

import { qweb, _t } from 'web.core';
import Dialog from "web.Dialog";

import { ContentsContainerBehavior } from './knowledge_behaviors.js';
import { KnowledgeToolbar } from './knowledge_toolbars.js';

const ArticlesStructureBehaviorMixin = {
    //--------------------------------------------------------------------------
    // Articles Structure - BUSINESS LOGIC
    //--------------------------------------------------------------------------

    /**
     * Updates the article structure.
     * This will display the children of this article.
     * We only take the direct children if 'this.onlyDirectChildren' is True.
     *
     * This block is used by the /articles_structure and /articles_index commands and their
     * respective toolbars through a system of Mixin to avoid code duplication.
     *
     * This mixin only needs those parameters set to be able to function:
     * - this.articleId - the id of the concerned article
     * - this.onlyDirectChildren - controls if we only display one level of depth or ALL children
     * - this.articlesStructureAnchor - the 'o_knowledge_articles_structure_wrapper' linked to the
     *   behavior or toolbar
     * - (direct access to the '_rpc' and 'do_action' methods).
     *
     * Small design effect note:
     * We use a fake promise that is resolved after 500ms when updating the Articles Structure.
     * The allows avoiding the search_read completing very fast and creating a "flicker effect".
     */
    _updateArticlesStructure: async function () {
        this.minimumWait = this.minimumWait !== undefined ? this.minimumWait : 500;

        const articlesStructureElement = this.articlesStructureAnchor.getElementsByClassName('o_knowledge_articles_structure_content');

        articlesStructureElement[0].innerHTML = '<i class="fa fa-refresh fa-spin ml-3 mb-3"/>';

        const domain = [[
            'parent_id',
            this.onlyDirectChildren ? '=' : 'child_of',
            this.articleId
        ]]

        const minimumWaitPromise = new Promise(resolve => setTimeout(resolve, this.minimumWait));
        const articlesChildrenPromise = this._rpc({
            model: 'knowledge.article',
            method: 'search_read',
            fields: ['id', 'display_name', 'parent_id'],
            orderBy: [{name: 'sequence', asc: true}],
            domain: domain,
        });

        const [ _, articlesChildren ] = await Promise.all([
            minimumWaitPromise,
            articlesChildrenPromise]
        );

        const articlesStructure = this.buildArticlesStructure(
            this.articleId, articlesChildren);

        const updatedStructure = qweb.render('knowledge.articles_structure', {
            'articles': articlesStructure
        });

        articlesStructureElement[0].innerHTML = updatedStructure;

        $(this.articlesStructureAnchor).on(
            'click',
            '.o_knowledge_article_structure_link',
            this._onArticleLinkClick.bind(this)
        );
    },

    /**
     * Transforms the flat search_read result into a parent/children articles hierarchy.
     *
     * @param {Integer} parent
     * @param {Array} allArticles
     * @returns {Array} articles structure
     */
    buildArticlesStructure: function (parent, allArticles) {
        return allArticles
            .filter((article) => article.parent_id && article.parent_id[0] == parent)
            .map((article) => {
                return {
                    id: article.id,
                    name: article.display_name,
                    children: this.buildArticlesStructure(article.id, allArticles),
                }
            });
    },

    //--------------------------------------------------------------------------
    // Articles Structure - HANDLERS
    //--------------------------------------------------------------------------

    /**
     * Opens the article in the side tree menu.
     *
     * @param {Event} event
     */
     _onArticleLinkClick: async function (event) {
        event.preventDefault();

        const actionPromise = this.do_action('knowledge.ir_actions_server_knowledge_home_page', {
            stackPosition: 'replaceCurrentAction',
            additional_context: {
                res_id: parseInt(event.target.getAttribute('data-oe-nodeid'))
            }
        });

        await actionPromise.catch(() => {
            Dialog.alert(this,
                _t("This article was deleted or you don't have the rights to access it."), {
                title: _t('Error'),
            });
        });
    },
};

/**
 * A behavior for the /articles_structure command @see Wysiwyg.
 * It creates a listing of children of this article.
 *
 * It is used by 2 different commands:
 * - /articles_structure that only list direct children
 * - /articles_index that lists all children
 *
 * It is an extension of @see ContentsContainerBehavior
 */
const ArticlesStructureBehavior = ContentsContainerBehavior.extend(ArticlesStructureBehaviorMixin, {
    //--------------------------------------------------------------------------
    // 'ContentsContainerBehavior' overrides
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
    },

    /**
     * Re-apply contenteditable="false" that is turned on automatically by the base editor code.
     * This avoids having our custom links opening the editor toolbar on click.
     *
     * @override
     */
    applyAttributes: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.anchor.querySelectorAll('a').forEach(element => {
                element.setAttribute('contenteditable', 'false');
            });
        }
    },

    /**
     * Adds the Article Click listener to open the associated article.
     *
     * @override
     */
     applyListeners: async function () {
        this._super.apply(this, arguments);

        if (this.mode === 'edit') {
            $(this.anchor).data('articleId', this.articleId);
        }

        if (this.mode === 'edit' && !$(this.anchor).hasClass('o_knowledge_articles_structure_loaded')) {
            this.articlesStructureAnchor = this.anchor;
            this.onlyDirectChildren = $(this.anchor).hasClass('o_knowledge_articles_structure_only_direct_children');
            await this._updateArticlesStructure();
            $(this.anchor).addClass('o_knowledge_articles_structure_loaded');
        } else {
            $(this.anchor).on(
                'click',
                '.o_knowledge_article_structure_link',
                this._onArticleLinkClick.bind(this)
            );
        }
    },

    /**
     * @override
     */
    disableListeners: function () {
        this._super.apply(this, arguments);
        $(this.anchor).off('click', '.o_knowledge_article_structure_link');
    },

    //--------------------------------------------------------------------------
    // Proxies
    //--------------------------------------------------------------------------

    /**
     * Since 'ContentsContainerBehavior' extends 'Class' and not Widget, we need to go through
     * our handler to proxy the do_action calls. As the handler properly extends Widget.
     */
    do_action: async function () {
        return this.handler.do_action.apply(this.handler, arguments);
    },

    /**
     * Since 'ContentsContainerBehavior' extends 'Class' and not Widget, we need to go through
     * our handler to proxy the _rpc calls. As the handler properly extends Widget.
     */
    _rpc: async function () {
        return this.handler._rpc.apply(this.handler, arguments);
    },
});

/**
 * Toolbar for the /articles_structure command
 */
 const ArticlesStructureToolbar = KnowledgeToolbar.extend(ArticlesStructureBehaviorMixin, {
    /**
     * Recover the eventual related record from @see KnowledgeService
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.articlesStructureAnchor = this.container;
    },

    /**
     * @override
     */
    _setupButton: function (button) {
        this._super.apply(this, arguments);

        if (button.dataset.call === 'update_articles_structure') {
            button.addEventListener("click", this._onUpdateArticlesStructureClick.bind(this));
        }
    },

    _onUpdateArticlesStructureClick: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this.articleId = parseInt($(this.container).data('articleId'));
        this.onlyDirectChildren = $(this.container).hasClass(
            'o_knowledge_articles_structure_only_direct_children');

        this._updateArticlesStructure();
    }
});

export { ArticlesStructureBehavior, ArticlesStructureToolbar };
