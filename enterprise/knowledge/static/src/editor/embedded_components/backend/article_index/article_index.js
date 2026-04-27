import { onWillStart, useState } from "@odoo/owl";
import {
    getEmbeddedProps,
    useEmbeddedState,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import {
    EmbeddedComponentToolbar,
    EmbeddedComponentToolbarButton,
} from "@html_editor/others/embedded_components/core/embedded_component_toolbar/embedded_component_toolbar";
import { useService } from "@web/core/utils/hooks";
import { ReadonlyEmbeddedArticleIndexComponent } from "@knowledge/editor/embedded_components/core/article_index/readonly_article_index";
import { KeepLast } from "@web/core/utils/concurrency";

export class EmbeddedArticleIndexComponent extends ReadonlyEmbeddedArticleIndexComponent {
    static template = "knowledge.EmbeddedArticleIndex";
    static components = {
        ...ReadonlyEmbeddedArticleIndexComponent.components,
        EmbeddedComponentToolbar,
        EmbeddedComponentToolbarButton,
    };
    static props = {
        ...ReadonlyEmbeddedArticleIndexComponent.props,
        host: { type: Object },
    };

    setup() {
        this.orm = useService("orm");
        this.embeddedState = useEmbeddedState(this.props.host);
        this.keepLastFetch = new KeepLast();
        this.state = useState({
            loading: false,
        });
        onWillStart(async () => {
            if (this.embeddedState.articles === undefined) {
                this.loadArticleIndex({ firstLoad: true });
            }
        });
    }

    /**
     * @param {integer} resId
     * @param {Boolean} showAllChildren
     * @returns {Array[Object]}
     */
    async fetchAllArticles(resId, showAllChildren) {
        const domain = [
            ["parent_id", !showAllChildren ? "=" : "child_of", resId],
            ["is_article_item", "=", false],
        ];
        const { records } = await this.orm.webSearchRead("knowledge.article", domain, {
            specification: {
                display_name: {},
                parent_id: {},
            },
            order: "sequence",
        });
        return records;
    }

    async loadArticleIndex({ showAllChildren = undefined, firstLoad = false } = {}) {
        this.state.loading = true;
        if (showAllChildren === undefined) {
            showAllChildren = this.embeddedState.showAllChildren;
        }
        const resId = this.env.model.root.resId;
        const promise = this.fetchAllArticles(resId, showAllChildren);
        const articles = await this.keepLastFetch.add(promise);
        if (firstLoad && this.embeddedState.articles !== undefined) {
            // Articles were provided by a collaborator before
            // the first load was finished, discard loaded articles.
            this.state.loading = false;
            return;
        }
        /**
         * @param {integer} parentId
         * @returns {Object}
         */
        const buildIndex = (parentId) => {
            return articles
                .filter((article) => {
                    return article.parent_id && article.parent_id === parentId;
                })
                .map((article) => {
                    return {
                        id: article.id,
                        name: article.display_name,
                        childIds: buildIndex(article.id),
                    };
                });
        };
        this.state.loading = false;
        this.embeddedState.showAllChildren = showAllChildren;
        this.embeddedState.articles = buildIndex(resId);
    }

    async onSwitchModeBtnClick() {
        this.loadArticleIndex({
            showAllChildren: !this.embeddedState.showAllChildren,
        });
    }

    async onRefreshBtnClick() {
        this.loadArticleIndex();
    }
}

export const articleIndexEmbedding = {
    name: "articleIndex",
    Component: EmbeddedArticleIndexComponent,
    getStateChangeManager: (config) => {
        return new StateChangeManager(config);
    },
    getProps: (host) => {
        return {
            host,
            ...getEmbeddedProps(host),
        };
    },
};
