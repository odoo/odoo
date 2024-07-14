/** @odoo-module */

import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { useService } from "@web/core/utils/hooks";
import { renderToMarkup } from "@web/core/utils/render";
import {
    useEffect,
    useState,
    onMounted,
    onWillStart,
} from "@odoo/owl";
import {
    BehaviorToolbar,
    BehaviorToolbarButton,
} from "@knowledge/components/behaviors/behavior_toolbar/behavior_toolbar";
import { useRefWithSingleCollaborativeChild } from "@knowledge/js/knowledge_utils";


/**
 * It creates a listing of children of this article.
 *
 * It is used by 2 different commands:
 * - /index that only list direct children
 * - /outline that lists all children
 */
export class ArticlesStructureBehavior extends AbstractBehavior {
    static components = {
        BehaviorToolbar,
        BehaviorToolbarButton,
    };
    static props = {
        ...AbstractBehavior.props,
        content: { type: Object, optional: true },
    };
    static template = "knowledge.ArticlesStructureBehavior";

    setup () {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService('action');
        this.childrenSelector = 'o_knowledge_articles_structure_children_only';
        this.state = useState({
            // Used for the loading animation on the refresh button
            refreshing: false,
            // Specify when the content is ready to be inserted
            changeContent: false,
            // Used to change the display value of the "Show All" button
            showAllChildren: !this.props.content || !this.props.content.includes(this.childrenSelector),
        });
        // Used during the loading of a new content (for rpc queries and
        // rendering)
        this.showAllChildren = this.state.showAllChildren;
        // Register changes in Elements of the content, the purpose is to
        // maintain maximum one OL element as the only child of content.
        this.articlesStructureContent = useRefWithSingleCollaborativeChild(
            "articlesStructureContent",
            (element) => {
                if (element) {
                    // The content OL element has the class which tells if it
                    // contains articles sub-children or not, update the state in
                    // consequence.
                    this.state.showAllChildren = !element.classList.contains(this.childrenSelector);
                } else {
                    // The default state when the content is empty is to show
                    // all articles sub-children.
                    this.state.showAllChildren = true;
                }
            }
        );

        onWillStart(async () => {
            // Populate content with the prop coming from the blueprint if
            // possible.
            this.content = this.props.content || await this._renderArticlesStructure();
        });

        if (!this.props.readonly) {
            let mounted = false;
            useEffect(() => {
                // Nothing to do onMounted
                if (!mounted) {
                    mounted = true;
                    return;
                }
                // Update the content when clicking on a button of the toolbar
                if (this.state.changeContent) {
                    this._appendArticlesStructureContent();
                    this.editor.historyStep();
                    this.state.changeContent = false;
                }
            }, () => [this.state.changeContent]);
        } else {
            onMounted(() => {
                this._appendArticlesStructureContent();
            });
        }

        useEffect(() => {
            const onClick = this._onArticleLinkClick.bind(this);
            const links = this.props.anchor.querySelectorAll('.o_knowledge_article_structure_link');
            links.forEach(link => link.addEventListener('click', onClick));
            return () => {
                links.forEach(link => link.removeEventListener('click', onClick));
            };
        });

        useEffect(() => {
            const onDrop = event => {
                event.preventDefault();
                event.stopPropagation();
            };
            this.props.anchor.addEventListener('drop', onDrop);
            return () => {
                this.props.anchor.removeEventListener('drop', onDrop);
            };
        });
    }

    //--------------------------------------------------------------------------
    // TECHNICAL
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    extraRender() {
        super.extraRender();
        this._appendArticlesStructureContent();
        // Migration to the new system (the childrenSelector class is
        // used on the content node instead of the anchor).
        if (this.props.anchor.classList.contains(this.childrenSelector)) {
            this.props.anchor.classList.toggle(this.childrenSelector);
            this.articlesStructureContent.el.querySelectorAll(':scope > ol').forEach((ol) => {
                ol.classList.toggle(this.childrenSelector);
            });
        }
    }

    //--------------------------------------------------------------------------
    // BUSINESS
    //--------------------------------------------------------------------------

    _appendArticlesStructureContent() {
        const parser = new DOMParser();
        // this.content always comes from the database, or from a sanitized
        // collaborative step (DOMPurify).
        this.articlesStructureContent.el.replaceChildren(...parser.parseFromString(this.content, 'text/html').body.children);
    }

    /**
     * Transforms the flat search_read result into a parent/children articles hierarchy.
     *
     * @param {Integer} parentId
     * @param {Array} allArticles
     * @returns {Array[Object]} articles structure
     */
    _buildArticlesStructure (parentId, allArticles) {
        const articles = [];
        for (const article of allArticles) {
            if (article.parent_id && article.parent_id === parentId) {
                articles.push({
                    id: article.id,
                    name: article.display_name,
                    child_ids: this._buildArticlesStructure(article.id, allArticles),
                });
            }
        }
        return articles;
    }

    /**
     * @returns {Array[Object]}
     */
    async _fetchAllArticles (articleId) {
        const domain = [
            ['parent_id', !this.showAllChildren ? '=' : 'child_of', articleId],
            ['is_article_item', '=', false]
        ];
        const { records } = await this.orm.webSearchRead('knowledge.article', domain, {
            specification: {
                display_name: {},
                parent_id: {},
            },
            order: 'sequence',
        });
        return records;
    }

    /**
     * @returns {HTMLElement}
     */
    async _renderArticlesStructure () {
        const articleId = this.props.record.resId;
        const allArticles = await this._fetchAllArticles(articleId);
        return renderToMarkup('knowledge.ArticlesStructureContent', {
            'articles': this._buildArticlesStructure(articleId, allArticles),
            'showAllChildren': this.showAllChildren,
        });
    }

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    /**
     * Opens the article in the side tree menu.
     *
     * @param {Event} event
     */
    async _onArticleLinkClick (event) {
        event.preventDefault();
        this.actionService.doAction('knowledge.ir_actions_server_knowledge_home_page', {
            additionalContext: {
                res_id: parseInt(event.target.getAttribute('data-oe-nodeid'))
            }
        });
    }

    /**
     * @param {Event} event
     */
    async _onRefreshBtnClick (event) {
        event.stopPropagation();
        // Patch the Behavior to show that it is loading.
        this.state.refreshing = true;
        this.content = await this._renderArticlesStructure();
        // Patch the Behavior to show that the loading is finished and the
        // content is ready
        this.state.refreshing = false;
        this.state.changeContent = true;
    }

    /**
     * @param {Event} event
     */
    async _onSwitchMode (event) {
        this.showAllChildren = !this.state.showAllChildren;
        await this._onRefreshBtnClick(event);
    }
}
