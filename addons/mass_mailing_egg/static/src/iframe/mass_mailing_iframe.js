import { parseHTML } from "@html_editor/utils/html";
import { Component, onMounted, status, useRef, useState, useSubEnv } from "@odoo/owl";
import { LazyComponent, loadBundle } from "@web/core/assets";
import { Deferred } from "@web/core/utils/concurrency";
import { uniqueId } from "@web/core/utils/functions";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { registry } from "@web/core/registry";

export class MassMailingIframe extends Component {
    static template = "mass_mailing_egg.MassMailingIframe";
    static components = {
        LazyComponent,
        LocalOverlayContainer,
    };
    static props = {
        config: { type: Object },
        themeOptions: { type: Object },
        readonly: { type: Boolean },
    };

    setup() {
        /**
         * TODO EGGMAIL:
         * handle readonly, builder, no-builder modes
         * => nobuilder must create its own EDITOR
         * => readonly does nothing?
         */
        this.hotkeyService = useService("hotkey");
        this.overlayRef = useChildRef();
        this.iframeRef = useRef("iframeRef");
        useSubEnv({
            localOverlayContainerKey: uniqueId("mass_mailing_iframe"),
        });
        this.state = useState({
            ready: false,
            showFullscreen: false,
        });
        this.iframeLoaded = new Deferred();
        onMounted(() => this.setupIframe());
    }

    async setupIframe() {
        // TODO EGGMAIL: issue: the component is mounted twice, why?
        const iframeDoc = this.iframeRef.el.contentDocument;
        iframeDoc.head.append(this.renderHeadContent());
        iframeDoc.body.append(this.renderBodyContent());
        await this.loadAssetsEditBundle();
        if (status(this) === "destroyed") {
            return;
        }
        // Set `ready` symbol for tours
        this.iframeRef.el.setAttribute("is-ready", "true");
        this.iframeRef.el.contentWindow.addEventListener("beforeUnload", () => {
            this.iframeRef.el.removeAttribute("is-ready");
        });
        this.iframeLoaded.resolve(this.iframeRef.el);
        this.state.ready = true;
    }

    async loadAssetsEditBundle() {
        await Promise.all([
            // TODO EGGMAIL: properly investigate the required style and JS (need bootstrap js? other js?)
            loadBundle("mass_mailing_egg.assets_iframe_style", {
                targetDoc: this.iframeRef.el.contentDocument,
                css: true,
                js: false,
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
            // eslint-disable-next-line no-unsafe-optional-chaining
            ...(this.props.themeOptions.assets?.map((asset) =>
                loadBundle(asset, {
                    targetDoc: this.iframeRef.el.contentDocument,
                })
            ) ?? []),
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
    renderToIframeRealmFragment(template, context = {}) {
        return parseHTML(this.iframeRef.el.contentDocument, renderToString(template, context));
    }

    renderHeadContent() {
        return this.renderToIframeRealmFragment("mass_mailing_egg.IframeHead");
    }

    renderBodyContent() {
        return this.renderToIframeRealmFragment("mass_mailing_egg.IframeBody");
    }

    getBuilderProps() {
        return {
            overlayRef: this.overlayRef,
            iframeLoaded: this.iframeLoaded,
            // TODO EGGMAIL: investigate if the "savePlugin" feature should be plugged to the form view save or should be disabled completely
            snippetsName: "mass_mailing.email_designer_snippets",
            config: {
                ...this.props.config,
            },
            // codeView => make it an available option in the builder (optional), only in debug?
            // getThemeTab => provide DesignTab
            Plugins: registry.category("builder-plugins").getAll(),
            // Plugins => provide plugins selection, properly filter excluded Plugins
            isMobile: false, // TODO EGGMAIL: investigate, is it the mobile display feature or the current page state
            isTranslation: false, // TODO EGGMAIL: investigate, do we need that for mass_mailing?
            toggleMobile: () => {}, // TODO EGGMAIL: is it the mobile display feature?
            editableSelector: ".note-editable",
            toggleFullscreen: () => {
                this.state.showFullscreen = !this.state.showFullscreen;
            },
        };
    }
}
