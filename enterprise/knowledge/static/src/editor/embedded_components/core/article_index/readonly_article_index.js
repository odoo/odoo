import { Component } from "@odoo/owl";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { ArticleIndexList } from "@knowledge/editor/embedded_components/core/article_index/article_index_list";

export class ReadonlyEmbeddedArticleIndexComponent extends Component {
    static props = {
        articles: { type: Object, optional: true },
        showAllChildren: { type: Boolean, optional: true },
    };
    static defaultProps = {
        showAllChildren: true,
    };
    static template = "knowledge.ReadonlyEmbeddedArticleIndex";
    static components = { ArticleIndexList };
}

export const readonlyArticleIndexEmbedding = {
    name: "articleIndex",
    Component: ReadonlyEmbeddedArticleIndexComponent,
    getProps: (host) => {
        return {
            ...getEmbeddedProps(host),
        };
    },
};
