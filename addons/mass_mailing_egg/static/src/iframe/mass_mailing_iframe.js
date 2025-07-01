import { parseHTML } from "@html_editor/utils/html";
import {
    Component,
    onMounted,
    onWillDestroy,
    status,
    useEffect,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { LazyComponent, loadBundle } from "@web/core/assets";
import { Deferred } from "@web/core/utils/concurrency";
import { uniqueId } from "@web/core/utils/functions";
import { useChildRef, useForwardRefToParent, useService } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { Editor } from "@html_editor/editor";

const IFRAME_VALUE_SELECTOR = ".o_mass_mailing_value";

export class MassMailingIframe extends Component {
    static template = "mass_mailing_egg.MassMailingIframe";
    static components = {
        LazyComponent,
        LocalOverlayContainer,
    };
    static props = {
        config: { type: Object },
        themeOptions: { type: Object },
        onIframeLoad: { type: Function },
        iframeRef: { type: Function },
        showThemeSelector: { type: Boolean },
        readonly: { type: Boolean, optional: true },
        onEditorLoad: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
    };
    static defaultProps = {
        onEditorLoad: () => {},
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
        this.iframeRef = useForwardRefToParent("iframeRef");
        useSubEnv({
            localOverlayContainerKey: uniqueId("mass_mailing_iframe"),
        });
        this.state = useState({
            ready: false,
        });
        this.iframeLoaded = new Deferred();
        onMounted(() => {
            if (this.iframeRef.el.contentDocument.readyState === "complete") {
                this.setupIframe();
            } else {
                // Browsers like Firefox only make iframe document available after dispatching "load"
                this.iframeRef.el.addEventListener("load", () => this.setupIframe(), {
                    once: true,
                });
            }
        });
        useEffect(
            () => {
                this.iframeLoaded.then(() => {
                    if (status(this) === "destroyed") {
                        return;
                    }
                    this.iframeRef.el.contentDocument.body.classList[
                        this.state.showFullscreen ? "add" : "remove"
                    ]("o_mass_mailing_iframe_fullscreen");
                });
            },
            () => [this.state.showFullscreen]
        );
        if (!this.props.readonly && this.props.themeOptions.withBuilder) {
            this.state.showFullscreen = false;
        } else if (!this.props.readonly) {
            this.editor = new Editor(this.props.config, this.env.services);
            this.props.onEditorLoad(this.editor);
            onWillDestroy(() => {
                this.editor.destroy(true);
            });
            this.setupBasicEditor();
        }
    }

    async setupIframe() {
        // TODO EGGMAIL: issue: the component is mounted twice, why?
        await this.loadAssetsEditBundle();
        if (status(this) === "destroyed") {
            return;
        }
        const htmlResizeObserver = new ResizeObserver(() => {
            const height = Math.trunc(
                this.iframeRef.el.contentDocument.body
                    .querySelector(IFRAME_VALUE_SELECTOR)
                    .getBoundingClientRect().height
            );
            this.iframeRef.el.style.height = height + "px";
            // this.iframeRef.el.style.height = height + "px";
            // console.log('coucou');
            // debugger;
        });
        // Set `ready` symbol for tours
        this.iframeRef.el.contentDocument.head.appendChild(this.renderHeadContent());
        this.iframeRef.el.contentDocument.body.appendChild(this.renderBodyContent());
        htmlResizeObserver.observe(
            this.iframeRef.el.contentDocument.body.querySelector(IFRAME_VALUE_SELECTOR)
        );
        if (this.props.readonly) {
            this.retargetLinks(
                this.iframeRef.el.contentDocument.querySelector(IFRAME_VALUE_SELECTOR)
            );
        }
        this.iframeRef.el.setAttribute("is-ready", "true");
        this.iframeRef.el.contentWindow.addEventListener("beforeUnload", () => {
            this.iframeRef.el.removeAttribute("is-ready");
        });
        this.iframeLoaded.resolve(this.iframeRef.el);
        this.props.onIframeLoad(this.iframeLoaded);
        this.state.ready = true;
    }

    async setupBasicEditor() {
        await this.iframeLoaded;
        if (status(this) === "destroyed") {
            return;
        }
        this.editor.attachTo(
            this.iframeRef.el.contentDocument.body.querySelector(IFRAME_VALUE_SELECTOR)
        );
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

    onBlur(ev) {
        if (!this.props.readonly) {
            this.props.onBlur(ev);
        }
    }

    /**
     * Render a template in the realm of the iframe document, to avoid OWL
     * component validation errors (an Element created from the parent document
     * of an iframe is not an instance of the Element class from the iframe
     * document).
     *
     * @param {String} template
     * @returns {DocumentFragment}
     */
    renderToIframeRealmFragment(template) {
        return parseHTML(this.iframeRef.el.contentDocument, renderToString(template, this));
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
            // Plugins => provide plugins selection, properly filter excluded Plugins
            isMobile: false, // TODO EGGMAIL: investigate, is it the mobile display feature or the current page state
            toggleMobile: () => {}, // TODO EGGMAIL: is it the mobile display feature?
            editableSelector: IFRAME_VALUE_SELECTOR,
            toggleFullscreen: () => {
                this.state.showFullscreen = !this.state.showFullscreen;
            },
            onEditorLoad: this.props.onEditorLoad,
        };
    }

    /**
     * Ensure all links are opened in a new tab.
     */
    retargetLinks(container) {
        for (const link of container.querySelectorAll("a")) {
            this.retargetLink(link);
        }
    }

    retargetLink(link) {
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noreferrer");
    }
}
