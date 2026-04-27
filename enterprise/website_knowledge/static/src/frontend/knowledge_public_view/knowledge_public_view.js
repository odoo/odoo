import {
    Component,
    markup,
    onMounted,
    onPatched,
    onWillPatch,
    onWillUnmount,
    useExternalListener,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useBus } from "@web/core/utils/hooks";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";
import { KNOWLEDGE_PUBLIC_EMBEDDINGS } from "@website_knowledge/frontend/editor/embedded_components/embedding_sets";
import { PublicHtmlViewer } from "@website_knowledge/frontend/editor/html_viewer/public_html_viewer";

export class KnowledgePublicFormResizer extends Component {
    static props = {};
    static template = "website_knowledge.knowledgePublicFormResizer";

    /**
     * Enables the user to resize the aside block.
     * Note: When the user grabs the resizer, a new listener will be attached
     * to the document. The listener will be removed as soon as the user releases
     * the resizer to free some resources.
     */
    resizeSidebar() {
        const onPointerMove = throttleForAnimation((event) => {
            event.preventDefault();
            this.env.bus.trigger("WEBSITE_KNOWLEDGE:SET_SIDEBAR_SIZE", {
                sidebarSize: event.pageX,
            });
        });
        const onPointerUp = () => {
            document.removeEventListener("pointermove", onPointerMove);
            document.body.style.cursor = "auto";
            document.body.style.userSelect = "auto";
        };
        // Add style to root element because resizing has a transition delay,
        // meaning that the cursor is not always on top of the resizer.
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        document.addEventListener("pointermove", onPointerMove);
        document.addEventListener("pointerup", onPointerUp, { once: true });
    }
}

export class KnowledgePublic extends Component {
    static components = {
        // Deprecated
        HtmlViewer: PublicHtmlViewer,
        KnowledgePublicFormResizer,
    };
    static props = {
        resId: { type: Number, optional: true },
        showSidebar: { type: Boolean },
        // Deprecated
        record: { type: Object, optional: true },
    };
    static template = "website_knowledge.knowledgePublic";

    setup() {
        this.treeRef = useRef("tree");
        this.storageKey = "knowledge.unfolded.ids";
        this.unfoldedArticlesIds =
            localStorage.getItem(this.storageKey)?.split(";").map(Number) || [];
        // Debounce the search articles method to reduce the number of rpcs
        this.searchArticles = debounce(this.searchArticles, 500);
        if (this.props.record?.resId) {
            // Deprecated
            this.props.record.data.body = markup(this.props.record.data.body);
        }
        // Sidebar handling TODO @engagement TODO ABD
        // refactor to use an OWL component instead of backend rendering
        // -> should rpc for new article data when clicking in the sidebar
        // instead of reloading everything
        this.state = useState({
            tree: undefined,
            sidebarSize: 300,
            showAsideMobile: false,
        });
        useBus(this.env.bus, "WEBSITE_KNOWLEDGE:SET_SIDEBAR_SIZE", (ev) => {
            this.state.sidebarSize = ev.detail.sidebarSize;
        });
        const headerToggleAsideButton = document.querySelector(".o_header_toggle_aside_button");
        if (headerToggleAsideButton) {
            useExternalListener(headerToggleAsideButton, "click", this.toggleAsideMobile);
        }
        this.keepLastRender = new KeepLast();
        this.renderTree();
        this.boundLoadMoreArticles = this.loadMoreArticles.bind(this);
        this.boundFoldArticle = this.foldArticle.bind(this);
        useSubEnv({
            articleId: this.resId,
        });
        onMounted(() => {
            this.addLoadMoreHandlers();
            this.addFoldHandlers();
        });
        onPatched(() => {
            this.addLoadMoreHandlers();
            this.addFoldHandlers();
        });
        onWillPatch(() => {
            this.removeLoadMoreHandlers();
            this.removeFoldHandlers();
        });
        onWillUnmount(() => {
            this.removeLoadMoreHandlers();
            this.removeFoldHandlers();
        });
    }

    get resId() {
        return this.props.resId || this.props.record?.resId;
    }

    addLoadMoreHandlers() {
        for (const loadMoreEl of this.treeRef.el?.querySelectorAll(
            ".o_knowledge_article_load_more"
        ) || []) {
            loadMoreEl.addEventListener("click", this.boundLoadMoreArticles);
        }
    }

    removeLoadMoreHandlers() {
        for (const loadMoreEl of this.treeRef.el?.querySelectorAll(
            ".o_knowledge_article_load_more"
        ) || []) {
            loadMoreEl.removeEventListener("click", this.boundLoadMoreArticles);
        }
    }

    addFoldHandlers(el = undefined) {
        const targetEl = el || this.treeRef.el;
        for (const loadMoreEl of targetEl?.querySelectorAll(".o_article_caret") || []) {
            loadMoreEl.addEventListener("click", this.boundFoldArticle);
        }
    }

    removeFoldHandlers() {
        for (const loadMoreEl of this.treeRef.el?.querySelectorAll(".o_article_caret") || []) {
            loadMoreEl.addEventListener("click", this.boundFoldArticle);
        }
    }

    /**
     * Callback function called when the user clicks on the caret of an article
     * The function will load the children of the article and append them to the
     * dom. Then, the id of the unfolded article will be added to the cache.
     * (see: `_renderTree`).
     * @param {Event} event
     */
    async foldArticle(event) {
        event.stopPropagation();
        const buttonEl = event.currentTarget;

        const iconEl = buttonEl.querySelector("i");
        const liEl = buttonEl.closest("li");
        const articleId = parseInt(liEl.dataset.articleId);
        const ulEl = liEl.querySelector("ul");
        if (iconEl.classList.contains("fa-caret-down")) {
            ulEl.classList.add("d-none");
            if (this.unfoldedArticlesIds.indexOf(articleId) !== -1) {
                this.unfoldedArticlesIds.splice(this.unfoldedArticlesIds.indexOf(articleId), 1);
            }
            iconEl.classList.remove("fa-caret-down");
            iconEl.classList.add("fa-caret-right");
        } else {
            if (ulEl) {
                // Show hidden children
                ulEl.classList.remove("d-none");
            } else {
                let childrenEls;
                try {
                    childrenEls = await this.loadChildrenArticles(parseInt(liEl.dataset.articleId));
                } catch (error) {
                    // Article is not accessible anymore, remove it from the sidebar
                    liEl.remove();
                    throw error;
                }
                const newUlEl = document.createElement("ul");
                childrenEls = new DOMParser().parseFromString(childrenEls, "text/html").body
                    .childNodes;
                childrenEls.forEach((child) => {
                    newUlEl.appendChild(child);
                });
                this.addFoldHandlers(newUlEl);
                liEl.appendChild(newUlEl);
            }
            if (this.unfoldedArticlesIds.indexOf(articleId) === -1) {
                this.unfoldedArticlesIds.push(articleId);
            }
            iconEl.classList.remove("fa-caret-right");
            iconEl.classList.add("fa-caret-down");
        }
        localStorage.setItem(this.storageKey, this.unfoldedArticlesIds.join(";"));
    }

    /**
     * @deprecated
     */
    getConfig() {
        const config = {
            value: this.props.record?.data.body ?? "",
            embeddedComponents: [...KNOWLEDGE_PUBLIC_EMBEDDINGS],
        };
        return config;
    }

    async loadMoreArticles(ev) {
        ev.preventDefault();
        const rpcParams = {
            active_article_id: this.resId || false,
            parent_id: ev.target.dataset["parentId"] || false,
            limit: ev.target.dataset["limit"],
            offset: ev.target.dataset["offset"] || 0,
        };

        const addedArticles = await rpc("/knowledge/public_sidebar/load_more", rpcParams);
        const listRoot = ev.target.closest("ul");
        // remove existing "Load more" link
        ev.target.remove();
        // remove the 'forced' displayed active article
        const forcedDisplayedActiveArticle = listRoot.querySelector(
            ".o_knowledge_article_force_show_active_article"
        );
        if (forcedDisplayedActiveArticle) {
            forcedDisplayedActiveArticle.remove();
        }
        // insert the returned template
        listRoot.insertAdjacentHTML("beforeend", addedArticles);
        this.addLoadMoreHandlers();
    }

    async loadChildrenArticles(parentId) {
        return rpc("/knowledge/public_sidebar/children", { parent_id: parentId });
    }

    /**
     * Renders the tree listing all articles.
     * To minimize loading time, the function will initially load the root
     * articles.
     * The other articles will be loaded lazily: The user will have to click on
     * the caret next to an article to load and see their children.
     * The id of the unfolded articles will be cached so that they will
     * automatically be displayed on page load.
     */
    async renderTree() {
        const params = new URLSearchParams(document.location.search);
        if (params.get("auto_unfold")) {
            this.unfoldedArticlesIds.push(this.resId);
        }
        try {
            this.state.tree = markup(
                await this.keepLastRender.add(
                    rpc("/knowledge/public_sidebar", {
                        active_article_id: this.resId,
                        unfolded_articles_ids: this.unfoldedArticlesIds,
                    })
                )
            );
        } catch {
            this.state.tree = undefined;
        }
    }

    /**
     * @deprecated
     */
    resizeSidebar() {}

    async searchArticles(ev) {
        ev.preventDefault();
        const searchTerm = ev.target.value;
        if (!searchTerm) {
            await this.renderTree();
            return;
        }
        try {
            this.state.tree = markup(
                await this.keepLastRender.add(
                    rpc("/knowledge/public_sidebar", {
                        search_term: searchTerm,
                        active_article_id: this.resId,
                    })
                )
            );
        } catch {
            this.state.tree = undefined;
        }
    }

    toggleAsideMobile() {
        this.state.showAsideMobile = !this.state.showAsideMobile;
    }
}

registry.category("public_components").add("knowledge.public_view", KnowledgePublic);
registry
    .category("public_components")
    .add("website_knowledge.public_form_resizer", KnowledgePublicFormResizer);
