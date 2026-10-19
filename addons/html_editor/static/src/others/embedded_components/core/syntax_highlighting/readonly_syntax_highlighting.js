import { Component, onMounted, onWillStart, t, useProps, xml } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import { DEFAULT_LANGUAGE_ID, getPreValue, highlightPre } from "./syntax_highlighting_utils";

export class ReadonlySyntaxHighlightingComponent extends Component {
    props = useProps({
        value: t.string(),
        languageId: t.string(),
        host: t.object(),
    });
    // The host is the `pre`. There's no need for a template but Owl requires it.
    static template = xml`<span/>`;

    setup() {
        onWillStart(() =>
            loadBundle(
                `html_editor.assets_prism${cookie.get("color_scheme") === "dark" ? "_dark" : ""}`,
                { targetDoc: this.props.host.ownerDocument }
            )
        );
        onMounted(() => {
            const owlRoot = [...(this.props.host.children || [])].find(
                (child) => child.nodeName === "OWL-ROOT"
            );
            highlightPre(owlRoot || this.props.host, this.props.value, this.props.languageId);
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
