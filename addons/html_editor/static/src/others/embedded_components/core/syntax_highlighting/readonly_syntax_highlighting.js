import { Component, onMounted, xml } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import { DEFAULT_LANGUAGE_ID, getPreValue, highlightPre } from "./syntax_highlighting_utils";

export class ReadonlySyntaxHighlightingComponent extends Component {
    static props = {
        value: { type: String },
        languageId: { type: String },
        host: { type: Object },
    };
    // The host is the `pre`. There's no need for a template but Owl requires it.
    static template = xml`<span/>`;

    setup() {
        loadBundle("html_editor.assets_prism").then(() =>
            highlightPre(this.props.host, this.props.value, this.props.languageId)
        );
        onMounted(() => {
            // Load the CSS.
            const theme = cookie.get("color_scheme") === "dark" ? "okaida" : "default";
            const prismStyleLink = document.createElement("link");
            prismStyleLink.rel = "stylesheet";
            prismStyleLink.href = `/web/static/lib/prismjs/themes/${theme}.css`;
            this.props.host.ownerDocument.head.append(prismStyleLink);
        });
    }
}

export const readonlySyntaxHighlightingEmbedding = {
    name: "readonlySyntaxHighlighting",
    Component: ReadonlySyntaxHighlightingComponent,
    getProps: (host) => ({
        host,
        languageId: host.dataset.languageId || DEFAULT_LANGUAGE_ID,
        value: getPreValue(host),
    }),
};
