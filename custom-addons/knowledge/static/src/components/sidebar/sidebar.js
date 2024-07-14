/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ArticleSelectionBehaviorDialog } from '@knowledge/components/behaviors/article_behavior_dialog/article_behavior_dialog';
import { ArticleTemplatePickerDialog } from "@knowledge/components/article_template_picker_dialog/article_template_picker_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    KnowledgeSidebarFavoriteSection,
    KnowledgeSidebarPrivateSection,
    KnowledgeSidebarSharedSection,
    KnowledgeSidebarWorkspaceSection
} from "./sidebar_section";
import { throttleForAnimation } from "@web/core/utils/timing";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";

import { Component, onWillStart, reactive, useRef, useState, useChildSubEnv } from "@odoo/owl";

export const SORTABLE_TOLERANCE = 10;

/**
 * Main Sidebar component. Its role is mainly to fetch and manage the articles
 * to show and allow to reorder them. It updates the info of the current
 * article each time the props are updated.
 * The articles are stored in the state and have the following shape:
 * - {string} category,
 * - {array} child_ids,
 * - {string} icon,
 * - {boolean} is_article_item,
 * - {boolean} is_locked,
 * - {boolean} is_user_favorite,
 * - {string} name,
 * - {number} parent_id,
 * - {boolean} user_can_write,
 * - {boolean} has_article_children,
 */
export class KnowledgeSidebar extends Component {
    static props = {
        record: Object,
    };
    static template = "knowledge.Sidebar";
    static components = {
        KnowledgeSidebarFavoriteSection,
        KnowledgeSidebarPrivateSection,
        KnowledgeSidebarSharedSection,
        KnowledgeSidebarWorkspaceSection,
    };
    
    setup() {
        super.setup();

        this.actionService = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.userService = useService("user");

        this.favoriteTree = useRef("favoriteTree");
        this.mainTree = useRef("mainTree");

        this.currentData = {};

        this.storageKeys = {
            size: "knowledge.sidebarSize",
            unfoldedArticles: "knowledge.unfolded.ids",
            unfoldedFavorites: "knowledge.unfolded.favorite.ids",
        };

        // Get set of unfolded ids and sync it with the local storage (any
        // change will trigger a write in the local storage)
        this.unfoldedArticlesIds = reactive(
            new Set(localStorage.getItem(this.storageKeys.unfoldedArticles)?.split(";").map(Number)),
            () => localStorage.setItem(this.storageKeys.unfoldedArticles, Array.from(this.unfoldedArticlesIds).join(";"))
        );
        this.unfoldedFavoritesIds = reactive(
            new Set(localStorage.getItem(this.storageKeys.unfoldedFavorites)?.split(";").map(Number)),
            () => localStorage.setItem(this.storageKeys.unfoldedFavorites, Array.from(this.unfoldedFavoritesIds).join(";"))
        );

        useChildSubEnv({
            fold: this.fold.bind(this),
            getArticle: this.getArticle.bind(this),
            model: this.props.record.model,
            unfold: this.unfold.bind(this),
        });

        this.state = useState({
            dragging: false,
            sidebarSize: localStorage.getItem(this.storageKeys.size) || 300,
        });

        this.loadArticles();

        // Resequencing of the favorite articles
        useNestedSortable({
            ref: this.favoriteTree,
            elements: ".o_tree > li",
            edgeScrolling: {
                speed: 10,
                threshold: 15,
            },
            tolerance: SORTABLE_TOLERANCE,
            onDrop: ({element, next}) => {
                const articleId = parseInt(element.dataset.articleId);
                const beforeId = next ? parseInt(next.dataset.articleId) : false;
                this.resequenceFavorites(articleId, beforeId);
            },
        });

        // Resequencing and rehierarchisation of articles
        useNestedSortable({
            ref: this.mainTree,
            groups: () => this.isInternalUser ? ".o_section" : ".o_section[data-section='private']",
            connectGroups: () => this.isInternalUser,
            nest: true,
            preventDrag: (el) => el.classList.contains("readonly"),
            tolerance: SORTABLE_TOLERANCE,
            onDragStart: () => this.state.dragging = true,
            onDragEnd: () => this.state.dragging = false,
            /**
             * @param {DOMElement} element - dropped element
             * @param {DOMElement} next - element before wich the element was dropped
             * @param {DOMElement} group - inital (=current) group of the dropped element
             * @param {DOMElement} newGroup - group in which the element was dropped
             * @param {DOMElement} parent - parent element of where the element was dropped
             * @param {DOMElement} placeholder - hint element showing the current position
             */
            onDrop: async ({element, next, group, newGroup, parent, placeholder}) => {
                const article = this.getArticle(parseInt(element.dataset.articleId));
                // Dropped on trash, move the article to the trash
                if (newGroup.classList.contains("o_knowledge_sidebar_trash")) {
                    this.moveToTrash(article);
                    return;
                }
                const parentId = parent ? parseInt(parent.dataset.articleId) : false;
                // Dropped on restricted position (child of readonly or shared root)
                if (placeholder.classList.contains('bg-danger')) {
                    this.rejectDrop(article, parentId);
                    return;
                }
                const currentPosition = {
                    category: article.category,
                    parentId: article.parent_id,
                    beforeArticleId: parseInt(element.nextElementSibling?.dataset.articleId) || false,
                };
                const newPosition = {
                    category: newGroup.dataset.section,
                    parentId: parentId,
                    beforeArticleId: parseInt(next?.dataset.articleId) || false,
                };
                this.moveArticle(article, currentPosition, newPosition);
            },
            /**
             * @param {DOMElement} element - moved element
             * @param {DOMElement} parent - parent element of where the element was moved
             * @param {DOMElement} group - inital (=current) group of the moved element
             * @param {DOMElement} newGroup - group in which the element was moved
             * @param {DOMElement} prevPos.parent - element's parent before the move
             * @param {DOMElement} placeholder - hint element showing the current position
             */
            onMove: ({element, parent, group, newGroup, prevPos, placeholder}) => {
                if (prevPos.parent) {
                    const prevParent = this.getArticle(parseInt(prevPos.parent.dataset.articleId));
                    // Remove caret if article has no child
                    if (!prevParent.has_article_children ||
                        prevParent.child_ids.length === 1 &&
                        prevParent.child_ids[0] === parseInt(element.dataset.articleId)
                    ) {
                        prevPos.parent.classList.remove('o_article_has_children');
                    }
                }
                if (parent) {
                    // Cannot add child to readonly articles, unless it is the
                    // current parent.
                    const currentParentId = element.parentElement.parentElement.dataset.articleId;
                    const targetParentId = parent.dataset.articleId;
                    if (currentParentId !== targetParentId && parent.classList.contains('readonly')) {
                        placeholder.classList.add('bg-danger');
                        return;
                    }
                    // Add caret
                    parent.classList.add('o_article_has_children');
                } else if (newGroup.dataset.section === "shared") {
                    // Drop in "shared" is not allowed, but resequencing shared articles is
                    const article = this.getArticle(parseInt(element.dataset.articleId));
                    if (!(article.category === 'shared' && !article.parent_id)) {
                        placeholder.classList.add('bg-danger');
                        return;
                    }
                }
                placeholder.classList.remove('bg-danger');
            },
        });

        onWillStart(async () => {
            this.isInternalUser = await this.userService.hasGroup('base.group_user');
        });

        useRecordObserver(async (record) => {
            const nextDataParentId = record.data.parent_id ? record.data.parent_id[0] : false;
            // During the first load, `loadArticles` is still pending and the component is in its
            // loading state. However, because of OWL reactive implementation (uses a Proxy),
            // record data still has to be read in order to subscribe to later changes, even if
            // nothing is done with that data on the first call. This subscription is what allows
            // this callback to be called i.e. when the name of the article is changed, reflecting
            // the change in the sidebar. See useRecordObserver, effect, reactive implementations
            // for further details.
            const article = this.getArticle(record.resId) || {
                id: record.resId,
                name: record.data.name,
                icon: record.data.icon,
                category: record.data.category,
                parent_id: nextDataParentId,
                is_locked: record.data.is_locked,
                user_can_write: record.data.user_can_write,
                is_article_item: record.data.is_article_item,
                is_user_favorite: record.data.is_user_favorite,
                child_ids: [],
            };
            if (this.state.articles[record.resId]) {
                if (record.data.is_article_item !== article.is_article_item) {
                    if (record.data.is_article_item) {
                        // Article became item, remove it from the sidebar
                        this.removeArticle(article);
                    } else {
                        // Item became article, add it in the sidebar
                        this.insertArticle(article, {
                            parentId: article.parent_id
                        });
                        this.showArticle(article);
                    }
                }
                if (record.data.is_user_favorite !== article.is_user_favorite) {
                    if (record.data.is_user_favorite) {
                        // Add the article to the favorites tree
                        this.state.favoriteIds.push(article.id);
                    } else {
                        // Remove the article from the favorites tree
                        this.state.favoriteIds.splice(this.state.favoriteIds.indexOf(article.id), 1);
                    }
                }
                if ((nextDataParentId !== article.parent_id || record.data.category !== article.category) &&
                    (record.data.parent_id !== this.currentData.parent_id || record.data.category !== this.currentData.category)) {
                    // Article changed position ("Moved to")
                    if (!this.getArticle(nextDataParentId)) {
                        // Parent is not loaded, reload the tree to show moved
                        // article in the sidebar
                        await this.loadArticles();
                        this.showArticle(this.getArticle(record.resId));
                    } else {
                        this.repositionArticle(article, {
                            parentId: nextDataParentId,
                            category: record.data.category,
                        });
                    }
                }
                // Update values used to display the current article in the sidebar
                Object.assign(article, {
                    name: record.data.name,
                    icon: record.data.icon,
                    is_locked: record.data.is_locked,
                    user_can_write: record.data.user_can_write,
                    is_article_item: record.data.is_article_item,
                    is_user_favorite: record.data.is_user_favorite,
                });
            } else if (!this.state.loading) {  // New article, add it in the state and sidebar
                if (record.data.is_user_favorite) {
                    // Favoriting an article that is not shown in the main
                    // tree (hidden child, item, or child of restricted)
                    this.state.favoriteIds.push(record.resId);
                }
                this.state.articles[article.id] = article;
                // Don't add new items in the sidebar
                if (!record.data.is_article_item) {
                    await this.insertArticle(article, {
                        category: article.category,
                        parentId: article.parent_id,
                    });
                    // Make sure the article is visible
                    this.showArticle(article);
                    if (nextDataParentId && this.getArticle(nextDataParentId)?.is_user_favorite) {
                        this.unfold(nextDataParentId, true);
                    }
                }
            }

            this.currentData = {
                parent_id: record.data.parent_id,
                category: record.data.category,
            };
        });
        this.env.bus.addEventListener("knowledge.sidebar.insertNewArticle", async ({ detail }) => {
            if (this.getArticle(detail.articleId)) {
                // Article already in the sidebar
                return;
            }
            const parent = detail.parentId ? this.getArticle(detail.parentId) : false;
            const newArticle = {
                id: detail.articleId,
                name: detail.name,
                icon: detail.icon,
                parent_id: parent ? parent.id : false,
                category: parent ? parent.category : false,
                is_locked: false,
                user_can_write: true,
                is_article_item: false,
                is_user_favorite: false,
                child_ids: [],
            };
            this.state.articles[newArticle.id] = newArticle;
            await this.insertArticle(newArticle, {
                parentId: newArticle.parent_id,
                category: parent ? parent.category : false
            });
        });
    }

    /**
     * Open the templates dialog
     */
    browseTemplates() {
        this.dialog.add(ArticleTemplatePickerDialog, {
            onLoadTemplate: async articleTemplateId => {
                await this.actionService.doAction("knowledge.ir_actions_server_knowledge_home_page", {
                    stackPosition: "replaceCurrentAction",
                    additionalContext: {
                        res_id: await this.orm.call("knowledge.article", "create_article_from_template", [
                            articleTemplateId
                        ])
                    }
                });
            }
        });
    }

    /**
     * Change the category of an article, and of all its descendants.
     * @param {Object} article
     * @param {String} category
     */
    async changeCategory(article, category) {
        article.category = category;
        if (article.id === this.props.record.id) {
            // Reload current record to propagate changes
            if (await this.props.record.isDirty()) {
                await this.props.record.save();
            } else {
                await this.props.record.model.load();
            }
        }
        for (const childId of article.child_ids) {
            this.changeCategory(this.getArticle(childId), category);
        }
    }

    /**
     * Create a new article (and open it).
     * @param {String} - category
     * @param {integer} - targetParentId
     */
    createArticle(category, targetParentId) {
        try {
            this.env.createArticle(category, targetParentId);
        } catch {
            // Could not create article, reload tree in case some permission changed
            this.loadArticles();
        }
    }

    /**
     * Fold an article.
     * @param {integer} articleId: id of article
     * @param {boolean} isFavorite: whether to fold in favorite tree
     */
    fold(articleId, isFavorite) {
        if (isFavorite) {
            this.unfoldedFavoritesIds.delete(articleId);
        } else {
            this.unfoldedArticlesIds.delete(articleId);
        }
    }

    /**
     * Get the article stored in the state given its id.
     * @param {integer} articleId - Id of the article 
     * @returns {Object} article
     */
    getArticle(articleId) {
        return this.state.articles[articleId];
    }

    /**
     * Get the array of article ids stored in the state from the given category
     * (eg. this.state.workspaceIds for workspace).
     * @param {String} category
     * @returns {Array} array of articles ids
     */
    getCategoryIds(category) {
        return this.state[`${category}Ids`];
    }

    /**
     * Insert the given article at the given position in the sidebar.
     * @param {Object} article - article stored in the state
     * @param {Object} position
     * @param {integer} position.beforeArticleId
     * @param {String} position.category
     * @param {integer} position.parentId
     *  
     */
    async insertArticle(article, position) {
        if (position.parentId) {
            const parent = this.getArticle(position.parentId);
            if (parent) {
                // Make sure the existing children are loaded if parent has any
                if (!this.unfoldedArticlesIds.has(parent.id)) {
                    await this.unfold(parent.id, false);
                    if (parent.child_ids.includes(article.id)) {
                        return;
                    }
                }
                // Position it at the right position w.r. to the other children
                // if the parent is not yet aware of the child article (eg when
                // moving, the article is moved in frontend, then if the user
                // confirms, the article is moved in backend)
                if (position.beforeArticleId) {
                    parent.child_ids.splice(parent.child_ids.indexOf(position.beforeArticleId), 0, article.id);
                } else {
                    parent.child_ids.push(article.id);
                }
                parent.has_article_children = true;
            }
        } else {
            // Add article in the list of articles of the new category, at the right position
            const categoryIds = this.getCategoryIds(position.category);
            if (categoryIds) {
                if (position.beforeArticleId) {
                    categoryIds.splice(categoryIds.indexOf(position.beforeArticleId), 0, article.id);
                } else {
                    categoryIds.push(article.id);
                }
            }
        }
    }

    /**
     * Check if the given article is an ancestor of the active one.
     * @param {integer} articleId
     * @returns {Boolean}
     */
    isAncestor(articleId) {
        let article = this.getArticle(this.props.record.resId);
        while (article) {
            if (article.id === articleId) {
                return true;
            }
            article = this.getArticle(article.parent_id);
        }
        return false;
    }

    /**
     * Load the articles to show in the sidebar and store them in the state.
     * One loops through the articles fetched to create a mapping id:article
     * that allows easy access of the articles, add the articles in their correct categories
     * and add their children. One uses the parent_id field to fill the 
     * child_ids arrays because a simple read of the child_ids field would
     * return items (which should not be included in the sidebar), and the
     * articles would not be sorted correctly.
     */
    async loadArticles() {
        this.state.loading = true;
        // Remove already loaded articles
        Object.assign(this.state, {
            articles: {},
            favoriteIds: [],
            workspaceIds: [],
            sharedIds: [],
            privateIds: [],
        });
        const res = await this.orm.call(
            this.props.record.resModel,
            "get_sidebar_articles",
            [this.props.record.resId],
            { unfolded_ids: [...this.unfoldedArticlesIds, ...this.unfoldedFavoritesIds] }
        );
        const children = {};
        for (const article of res.articles) {
            this.state.articles[article.id] = {
                ...article,
                child_ids: children[article.id] ? children[article.id] : [],
            };
            // Items could be shown in the favorite tree as root articles, but
            // they should not be shown as children of other articles
            if (!article.is_article_item) {
                if (article.parent_id) {
                    const parent = this.getArticle(article.parent_id);
                    if (parent) {
                        parent.child_ids.push(article.id);
                    } else {
                        // Store children temporarily to add them to the parent
                        // when the parent will be added to the state in this loop.
                        if (children[article.parent_id]) {
                            children[article.parent_id].push(article.id);
                        } else {
                            children[article.parent_id] = [article.id];
                        }
                    }
                } else {
                    this.getCategoryIds(article.category).push(article.id);
                }
            }
        }
        this.state.favoriteIds = res.favorite_ids;
        this.showArticle(this.getArticle(this.props.record.resId));
        this.state.loading = false;
        this.resetUnfoldedArticles();
    }

    /**
     * Load the children of a given article
     * @param {object} article
     */
    async loadChildren(article) {
        const children = await this.orm.searchRead(
            this.props.record.resModel,
            [['parent_id', '=', article.id], ['is_article_item', '=', false]],
            ['name', 'icon', 'is_locked', 'user_can_write', 'has_article_children'],
            {
                'load': 'None',
                'order': 'sequence, id',
            }
        );
        for (const child of children) {
            article.child_ids.push(child.id);
            if (this.getArticle(child.id)) {
                // Article was already loaded (if it is in the favorites)
                continue;
            }
            this.state.articles[child.id] = {
                ...child,
                parent_id: article.id,
                child_ids: [],
                category: article.category,
                is_article_item: false,
                is_user_favorite: false,
            };
        }
    }

    /**
     * Try to move the given article to the given position (change its parent/
     * category/sequence) and update its position in the sidebar.
     * If the move will change the permissions of the article, show a
     * confirmation dialog.
     * @param {Object} article
     * @param {Object} currentPosition
     * @param {integer} position.beforeArticleId 
     * @param {String} position.category
     * @param {integer} position.parentId
     * @param {Object} newPosition
     * @param {integer} newPosition.beforeArticleId 
     * @param {String} newPosition.category
     * @param {integer} newPosition.parentId
     */
    async moveArticle(article, currentPosition, newPosition) {
        const confirmMove = async (article, position) => {
            if (this.props.record.resId === article.id && await this.props.record.isDirty()) {
                await this.props.record.save();
            }
            try {
                await this.orm.call(
                    this.props.record.resModel,
                    'move_to',
                    [article.id],
                    {
                        category: position.category,
                        parent_id: position.parentId,
                        before_article_id: position.beforeArticleId,
                    }
                );
            } catch (error) {
                // Reload the article tree to show potential modifications
                // done by another user that could cause the failure.
                this.loadArticles();
                throw error;
            }
            // Reload the current record if it was moved to propagate changes
            // (needed for example to remove the properties)
            if (article.id === this.props.record.resId) {
                await this.props.record.model.load();
            }
        };

        // Move the article in the sidebar
        this.repositionArticle(article, newPosition);
        // Permissions won't change, no need to ask for confirmation
        if (currentPosition.category === newPosition.category) {
            confirmMove(article, newPosition);
        } else {
            // Show confirmation dialog, and move article back to its original
            // position if the user cancels the move 
            const emoji = article.icon || '';
            const name = article.name;
            let message;
            let confirmLabel;
            if (newPosition.category === 'workspace') {
                message = _t(
                    'Are you sure you want to move "%s%s" to the Workspace? It will be shared with all internal users.',
                    emoji,
                    name || _t("Untitled")
                );
                confirmLabel = _t("Move to Workspace");
            } else if (newPosition.category === 'private') {
                message = _t(
                    'Are you sure you want to move "%s%s" to private? Only you will be able to access it.',
                    emoji,
                    name || _t("Untitled")
                );
                confirmLabel = _t("Move to Private");
            } else if (newPosition.category === 'shared' && newPosition.parentId) {
                const parent = this.getArticle(newPosition.parentId);
                const parentEmoji = parent.icon || '';
                const parentName = parent.name || '';
                message = _t(
                    'Are you sure you want to move "%s%s" under "%s%s"? It will be shared with the same persons.',
                    emoji,
                    name || _t("Untitled"),
                    parentEmoji,
                    parentName || _t("Untitled")
                );
            }
            this.dialog.add(ConfirmationDialog, {
                body: message,
                confirmLabel: confirmLabel,
                confirm: () => confirmMove(article, newPosition),
                cancel: () => {
                    // Move article back to its postion
                    this.repositionArticle(article, currentPosition);
                },
            });
        } 
    }

    /**
     * Move an article to the trash, and remove it from the sidebar.
     * @param {Object} article
     */
    async moveToTrash(article) {
        try {
            await this.orm.call(
                "knowledge.article",
                "action_send_to_trash",
                [article.id],
            );
        } catch {
            await this.loadArticles();
            return;
        }
        // If the article moved to the trash is an ancestor of the active
        // article, redirect to first accessible article.
        if (this.isAncestor(article.id)) {
            this.actionService.doAction(
                await this.orm.call('knowledge.article', 'action_home_page', [false]),
                {stackPosition: 'replaceCurrentAction'}
            );
        } else {
            this.removeArticle(article);
            this.removeFavorite(article);
        }
    }

    /**
     * Open the command palette if the user is an internal user, and open the
     * article selection dialog if the user is a portal user
     */
    onSearchBarClick() {
        if (this.isInternalUser) {
            this.env.services.command.openMainPalette({searchValue: '?'});
        } else {
            this.dialog.add(
                ArticleSelectionBehaviorDialog,
                {
                    title: _t('Search an Article...'),
                    confirmLabel: _t('Open'),
                    articleSelected: (article) => this.env.openArticle(article.articleId),
                }
            );
        }
    }

    /**
     * Show a dialog explaining why the given article cannot be moved to the
     * target position.
     * @param {article}
     * @param {parentId}
     */
    rejectDrop(article, parentId) {
        let message;
        if (parentId) {
            const parent = this.getArticle(parentId);
            message = _t(
                'Could not move "%s%s" under "%s%s", because you do not have write permission on the latter.',
                article.icon || "",
                article.name,
                parent.icon || "",
                parent.name
            );
        } else {
            message = _t(
                'Could not move "%s%s" in the shared section. Only shared articles can be moved in this section.',
                article.icon || "",
                article.name
            );
        }
        this.dialog.add(ConfirmationDialog, {
            confirmLabel: _t("Close"),
            title: _t("Move cancelled"),
            body: message,
        });
    }

    /**
     * Remove the given article from the sidebar.
     * @param {Object} article
     */
    removeArticle(article) {
        if (article.parent_id) {
            // Remove article from array of children of its parent
            const parent = this.getArticle(article.parent_id);
            if (parent) {
                const articleIdx = parent.child_ids.indexOf(article.id);
                if (articleIdx !== -1) {
                    parent.child_ids.splice(parent.child_ids.indexOf(article.id), 1);
                    // Removed last child of the parent article
                    if (!parent.child_ids.length) {
                        this.fold(parent.id);
                        this.fold(parent.id, true);
                        parent.has_article_children = false;
                    }
                }
            }
        } else {
            // Remove article from list of articles category
            const categoryIds = this.getCategoryIds(article.category);
            const articleIdx = categoryIds.indexOf(article.id);
            if (articleIdx !== -1) {
                categoryIds.splice(articleIdx, 1);
            }
        }
    }

    /**
     * Remove the given article from the list of favorites.
     * @param {Object} article
     */
    removeFavorite(article) {
        const favoriteIdx = this.state.favoriteIds.indexOf(article.id);
        if (favoriteIdx !== -1) {
            this.state.favoriteIds.splice(favoriteIdx, 1);
        }
     }

    /**
     * Change the position of an article in the sidebar.
     * @param {Object} article
     * @param {Object} position
     * @param {integer} position.beforeArticleId 
     * @param {String} position.category
     * @param {integer} position.parentId
     */
    async repositionArticle(article, position) {
        this.removeArticle(article);
        await this.insertArticle(article, position);
        // Change the parent of the article
        if (article.parent_id !== position.parentId) {
            article.parent_id = position.parentId;
        }
        // Change category of article and every descendant
        if (article.category !== position.category) {
            this.changeCategory(article, position.category);
        }
        // Make sure the article is visible
        this.showArticle(article);
    }

    /**
     * Updates the sequence of favorite articles for the current user.
     * @param {integer} articleId - Id of the moved favorite article
     * @param {integer} beforeId - Id of the favorite article after
     *      which the article is moved
     */
    resequenceFavorites(articleId, beforeId) {
        this.state.favoriteIds.splice(this.state.favoriteIds.indexOf(articleId), 1);
        if (beforeId) {
            this.state.favoriteIds.splice(this.state.favoriteIds.indexOf(beforeId), 0, articleId);
        } else {
            this.state.favoriteIds.push(articleId);
        }
        this.orm.call("knowledge.article.favorite", "resequence_favorites", [false], {
            article_ids: this.state.favoriteIds,
        });
    }

    /**
     * User could have unfolded ids in its local storage of articles that are
     * not shown in its sidebar anymore (trashed, converted to items, hidden,
     * permission change). This method will reset the list of ids in the local
     * storage using only the articles that are shown to the user, so that we
     * do not load the articles using a list containing a lot of useless ids. 
     */
    resetUnfoldedArticles() {
        this.unfoldedArticlesIds.forEach(id => {
            if (!this.getArticle(id)) {
                this.unfoldedArticlesIds.delete(id);
            }
        });
        this.unfoldedFavoritesIds.forEach(id => {
            if (!this.getArticle(id)) {
                this.unfoldedFavoritesIds.delete(id);
            }
        });
    }

    /**
     * Resize the sidebar horizontally.
     */
    resize() {
        const onPointerMove = throttleForAnimation(event => {
            event.preventDefault();
            this.state.sidebarSize = event.pageX;
        });
        const onPointerUp = () => {
            document.removeEventListener('pointermove', onPointerMove);
            document.body.style.cursor = "auto";
            document.body.style.userSelect = "auto";
            localStorage.setItem(this.storageKeys.size, this.state.sidebarSize);
        };
        // Add style to root element because resizing has a transition delay,
        // meaning that the cursor is not always on top of the resizer.
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        document.addEventListener('pointermove', onPointerMove);
        document.addEventListener('pointerup', onPointerUp, {once: true});
    }

    /**
     * Make sure the given article is shown in the sidebar by unfolding every
     * article until a root article is met.
     * @param {object} article - article to show in the sidebar
     */
    showArticle(article) {
        while (article && article.parent_id && article.parent_id in this.state.articles) {
            // Unfold in the main tree, without loading the children
            this.unfold(article.parent_id, false);
            article = this.getArticle(article.parent_id);
        }
    }

    /** Unfold an article.
     * @param {integer} articleId: id of article
     * @param {boolean} isFavorite: whether to unfold in favorite tree
     */        
    async unfold(articleId, isFavorite) {
        const article = this.getArticle(articleId);
        // Load the children of the article if it has not been unfolded yet
        if (article.has_article_children && !article.child_ids.length) {
            await this.loadChildren(article);
        }
        if (isFavorite) {
            this.unfoldedFavoritesIds.add(articleId);
        } else {
            this.unfoldedArticlesIds.add(articleId);
        }
    }
}
