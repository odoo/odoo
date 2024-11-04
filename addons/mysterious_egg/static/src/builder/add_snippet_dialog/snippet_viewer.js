import { Component, markup } from "@odoo/owl";

export class SnippetViewer extends Component {
    static template = "mysterious_egg.SnippetViewer";

    getSnippetColumns() {
        const snippets = this.props.state.snippets;

        const columns = [[], []];
        for (const index in snippets) {
            if (index % 2 === 0) {
                columns[0].push(snippets[index]);
            } else {
                columns[1].push(snippets[index]);
            }
        }
        return columns;
    }

    onClick(snippet) {
        this.props.selectSnippet(snippet);
    }

    getContent(elem) {
        if (!elem) {
            return markup("<div>plop</div>");
        }
        return markup(elem.outerHTML);
    }
}
