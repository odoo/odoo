import { Component } from "@odoo/owl";

export class ViewPlaceholderComponent extends Component {
    static template = "website_knowledge.ViewPlaceholder";
    static props = {};

    setup() {
        super.setup();
        this.url = `/knowledge/article/${this.env.articleId}`;
    }
}

export const viewPlaceholderEmbedding = {
    name: "view",
    Component: ViewPlaceholderComponent,
};
