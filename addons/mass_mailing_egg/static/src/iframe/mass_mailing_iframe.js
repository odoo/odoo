import { parseHTML } from "@html_editor/utils/html";
import {
    Component,
    markup,
    onMounted,
    onWillDestroy,
    onWillUpdateProps,
    status,
    useEffect,
    useRef,
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
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { closestScrollableY } from "@web/core/utils/scrolling";
import { _t } from "@web/core/l10n/translation";
import { MassMailingMobilePreviewDialog } from "../mobile_preview_dialog/mobile_preview_dialog";

const IFRAME_VALUE_SELECTOR = ".o_mass_mailing_value";

export class MassMailingIframe extends Component {
    static template = "mass_mailing_egg.MassMailingIframe";
    static components = {
        LazyComponent,
        LocalOverlayContainer,
    };
    static props = {
        config: { type: Object },
        themeOptions: { type: Object, optional: true },
        iframeRef: { type: Function, optional: true },
        showThemeSelector: { type: Boolean, optional: true },
        onIframeLoad: { type: Function, optional: true },
        showCodeView: { type: Boolean, optional: true },
        toggleCodeView: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
        onEditorLoad: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
        extraClass: { type: String, optional: true},
    };
    static defaultProps = {
        onEditorLoad: () => {},
        themeOptions: {},
    };

    setup() {
        /**
         * TODO EGGMAIL:
         * handle readonly, builder, no-builder modes
         * => nobuilder must create its own EDITOR
         * => readonly does nothing?
         */
        this.hotkeyService = useService("hotkey");
        this.dialog = useService("dialog");
        this.overlayRef = useChildRef();
        this.iframeRef = useForwardRefToParent("iframeRef");
        this.sidebarRef = useRef("sidebarRef");
        useSubEnv({
            localOverlayContainerKey: uniqueId("mass_mailing_iframe"),
        });
        this.state = useState({
            isMobile: false,
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
        onWillUpdateProps((nextProps) => {
            if (nextProps.showCodeView) {
                this.state.showFullscreen = false;
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
        const iframeResize = () => {
            const iframe = this.iframeRef.el;
            if (this.state.showFullscreen) {
                iframe.style.height = "100%";
            } else {
                const height = Math.trunc(
                    iframe.contentDocument.body
                        .querySelector(IFRAME_VALUE_SELECTOR)
                        .getBoundingClientRect().height
                );
                iframe.style.height = height + "px";
            }
        };
        const sidebarResize = () => {
            const sidebar = this.sidebarRef.el;
            const iframe = this.iframeRef.el;
            if (!sidebar) {
                return;
            }
            if (this.state.showFullscreen) {
                sidebar.style.top = "0";
                sidebar.style.height = "100%";
            } else if (this.env.inDialog) {
                // TODO EGGMAIL: test this for marketing automation
                const scrollableY = closestScrollableY(sidebar);
                if (scrollableY) {
                    const rect = scrollableY.getBoundingClientRect();
                    sidebar.style.height = `${rect.height}px`;
                    sidebar.style.top = "0";
                }
            } else {
                const scrollableY = closestScrollableY(sidebar);
                let stickyHeight = 0;
                let stickyZindex = 0;
                if (scrollableY) {
                    const statusBar = scrollableY.querySelector(".o_form_statusbar");
                    if (statusBar) {
                        const statusBarStyle = getComputedStyle(statusBar);
                        if (statusBarStyle.position === "sticky") {
                            stickyHeight += statusBar.getBoundingClientRect().height;
                        }
                        stickyZindex = parseInt(statusBarStyle.zIndex) || 0;
                    }
                }
                const top = scrollableY
                    ? `${
                          -1 * (parseInt(getComputedStyle(scrollableY).paddingTop) || 0) +
                          stickyHeight
                      }px`
                    : `${stickyHeight}px`;
                const maxHeight = iframe.getBoundingClientRect().height;
                const offsetHeight =
                    window.innerHeight -
                    stickyHeight -
                    document.querySelector(".o_content").getBoundingClientRect().y;
                sidebar.style.height = `${Math.min(maxHeight, offsetHeight)}px`;
                sidebar.style.top = top;
                if (stickyZindex > 0) {
                    sidebar.style.zIndex = `${stickyZindex - 1}`;
                }
            }
        };
        this.throttledResize = useThrottleForAnimation(() => {
            if (status(this) === "destroyed") {
                return;
            }
            iframeResize();
            sidebarResize();
        });
    }

    async setupIframe() {
        // TODO EGGMAIL: issue: the component is mounted twice, why?
        await this.loadAssetsEditBundle();
        if (status(this) === "destroyed") {
            return;
        }
        const htmlResizeObserver = new ResizeObserver(this.throttledResize);
        this.iframeRef.el.contentDocument.body.classList.add("o_in_iframe");
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
        this.props.onIframeLoad?.(this.iframeLoaded);
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
        const getExternalScrollableAncestor = () =>
            !this.showFullscreen && this.iframeRef.el && closestScrollableY(this.iframeRef.el);
        return {
            overlayRef: this.overlayRef,
            iframeLoaded: this.iframeLoaded,
            // TODO EGGMAIL: investigate if the "savePlugin" feature should be plugged to the form view save or should be disabled completely
            snippetsName: "mass_mailing.email_designer_snippets",
            config: {
                ...this.props.config,
                getExternalScrollableAncestor,
            },
            // codeView => make it an available option in the builder (optional), only in debug?
            // Plugins => provide plugins selection, properly filter excluded Plugins
            isMobile: this.state.isMobile,
            toggleMobile: this.toggleMobile.bind(this),
            editableSelector: IFRAME_VALUE_SELECTOR,
            toggleFullscreen: () => {
                this.state.showFullscreen = !this.state.showFullscreen;
            },
            toggleCodeView: this.props.toggleCodeView,
            onEditorLoad: this.props.onEditorLoad,
            getExternalScrollableAncestor,
            getThemeTab: () => {
                const DesignTab = odoo.loader.modules.get(
                    "@mass_mailing_egg/builder/tabs/design_tab"
                ).DesignTab;
                DesignTab.displayName = _t("Design");
                return DesignTab;
            },
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

    toggleMobile(ev) {
        this.state.isMobile = true;
        this.mobilePreview = this.dialog.add(MassMailingMobilePreviewDialog, {
            title: _t("Mobile Preview"),
            value: markup(this.props.config.content),
            IframeComponent: MassMailingIframe,
        }, {
            onClose: () => this.state.isMobile = false,
        });
    }
}
