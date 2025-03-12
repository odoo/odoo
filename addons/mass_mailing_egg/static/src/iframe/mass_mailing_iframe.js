import { parseHTML } from "@html_editor/utils/html";
import { Component, onWillUpdateProps, useRef } from "@odoo/owl";
import { LazyComponent, loadBundle } from "@web/core/assets";
import { Deferred } from "@web/core/utils/concurrency";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";

export class MassMailingIframe extends Component {
    static template = "mass_mailing_egg.MassMailingIframe";
    static components = {
        LazyComponent,
    };
    static props = {
        overlayRef: { type: Object },
        config: { type: Object },
        discard: { type: Function },
        onChange: { type: Function },
        reloadEditor: { type: Function },
        save: { type: Function },
        templateHTML: { type: String },
        // TODO EGGMAIL: remove templateStyleAssets if templates never need custom style assets
        templateStyleAssets: { type: Array, optional: true },
    };
    static defaultProps = {
        templateContext: {},
        templateStyleAssets: [],
    };

    setup() {
        this.hotkeyService = useService("hotkey");
        this.interactionService = useService("mass_mailing_egg.interactions");
        this.iframeRef = useRef("iframeRef");
        this.setupIframe();
        onWillUpdateProps((nextProps) => {
            if (this.props.templateHTML !== nextProps.templateHTML) {
                this.setupIframe();
            }
        });
    }

    setupIframe() {
        this.iframeLoaded = new Deferred();
        this.iframeKey = uniqueId("mass_mailing_iframe_");
    }

    async onIframeLoad() {
        const iframeDoc = this.iframeRef.el.contentDocument;
        iframeDoc.head.append(this.renderHeadContent());
        iframeDoc.body.append(this.renderBodyContent());
        await this.loadAssetsEditBundle();
        // Set `ready` symbol for tours
        this.iframeRef.el.setAttribute("is-ready", "true");
        this.iframeRef.el.contentWindow.addEventListener("beforeUnload", () => {
            this.iframeRef.el.removeAttribute("is-ready");
        });
        this.iframeLoaded.resolve(this.iframeRef.el);
    }

    async loadAssetsEditBundle() {
        await Promise.all([
            loadBundle("mass_mailing_egg.assets_iframe_style", {
                targetDoc: this.iframeRef.el.contentDocument,
            }),
            // TODO EGGMAIL: handle dark mode assets
            // TODO EGGMAIL: to remove following 2 assets if interactions are not needed
            loadBundle("mass_mailing_egg.assets_iframe_core", {
                targetDoc: this.iframeRef.el.contentDocument,
            }),
            loadBundle("mass_mailing_egg.assets_iframe_edit", {
                targetDoc: this.iframeRef.el.contentDocument,
            }),
            // TODO EGGMAIL: remove if templates never need custom style assets
            ...this.props.templateStyleAssets.map((asset) =>
                loadBundle(asset, {
                    targetDoc: this.iframeRef.el.contentDocument,
                })
            ),
        ]);
    }

    /**
     * Render a template in the realm of the iframe document, to avoid OWL
     * component validation errors (an Element created from the parent document
     * of an iframe is not an instance of the Element class from the iframe
     * document).
     *
     * @param {String} template
     * @param {Object} context
     * @returns {DocumentFragment}
     */
    renderToIframeRealmFragment(template, context) {
        return parseHTML(renderToString(this.iframeRef.el, template, context));
    }

    renderHeadContent() {
        return this.renderToIframeRealmFragment("mass_mailing_egg.IframeHead");
    }

    renderBodyContent() {
        const fragment = this.renderToIframeRealmFragment("mass_mailing_egg.IframeBody");
        const editable = fragment.querySelector(".note-editable");
        editable.append(parseHTML(this.iframeRef.el.contentDocument, this.props.templateHTML));
        return fragment;
    }

    getBuilderProps() {
        return {
            ...this.props,
            iframeLoaded: this.iframeLoaded,
        };
    }
}
