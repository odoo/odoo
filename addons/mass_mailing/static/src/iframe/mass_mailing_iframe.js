import { Editor } from "@html_editor/editor";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { loadIframe, loadIframeBundles } from "@mail/convert_inline/iframe_utils";
import { Component, onMounted, onWillDestroy, onWillUnmount, status } from "@odoo/owl";
import { LazyComponent } from "@web/core/lazy_component";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { uniqueId } from "@web/core/utils/functions";
import { useChildRef, useForwardRefToParent } from "@web/core/utils/hooks";
import { renderToFragment } from "@web/core/utils/render";
import { closestScrollableY } from "@web/core/utils/scrolling";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { useComponent, useLayoutEffect, useRef, useState, useSubEnv } from "@web/owl2/utils";

const IFRAME_VALUE_SELECTOR = ".o_mass_mailing_value";

/**
 * The MassMailingIframe will use this modified overlay service that will guarantee:
 * 1. Internal ordering of its different overlays
 * 2. To not mess up with owl's reconciliation of foreach when adding/removing overlays
 * This is a sub-optimal fix to the more general issue of owl displacing nodes that contain
 * an iframe, in which the iframe effectively unloads.
 */
export function useOverlayServiceOffset() {
    const comp = useComponent();
    const originalOverlay = comp.env.services.overlay;
    const subServices = Object.create(comp.env.services);
    subServices.overlay = Object.create(originalOverlay);
    subServices.overlay.add = (C, props, opts = {}) => {
        opts = {
            ...opts,
            sequence: (opts.sequence ?? 50) + 1000,
        };
        return originalOverlay.add(C, props, opts);
    };
    useSubEnv({ services: subServices });
}

export class MassMailingIframe extends Component {
    static template = "mass_mailing.MassMailingIframe";
    static components = {
        LazyComponent,
        LocalOverlayContainer,
    };
    static props = {
        config: { type: Object },
        iframeRef: { type: Function },
        iframeWrapperRef: { type: Function },
        showThemeSelector: { type: Boolean, optional: true },
        showCodeView: { type: Boolean, optional: true },
        toggleCodeView: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
        onEditorLoad: { type: Function, optional: true },
        onFocus: { type: Function, optional: true },
        extraClass: { type: String, optional: true },
        withBuilder: { type: Boolean, optional: true },
    };
    static defaultProps = {
        onEditorLoad: () => {},
        onFocus: () => {},
    };

    setup() {
        useOverlayServiceOffset();
        this.overlayRef = useChildRef();
        this.iframeRef = useForwardRefToParent("iframeRef");
        this.iframeWrapperRef = useForwardRefToParent("iframeWrapperRef");
        this.sidebarRef = useRef("sidebarRef");
        this.isRTL = localization.direction === "rtl";
        useSubEnv({
            localOverlayContainerKey: uniqueId("mass_mailing_iframe"),
        });
        this.state = useState({
            showFullscreen: false,
            isMobile: false,
            ready: false,
        });
        this.iframeLoaded = Promise.withResolvers();
        onMounted(() => {
            this.setupIframe();
        });
        if (!this.props.readonly && !this.props.withBuilder) {
            this.editor = new Editor(this.props.config, this.env.services);
            this.props.onEditorLoad(this.editor);
            onWillDestroy(() => {
                this.editor.destroy(true);
            });
            this.setupBasicEditor();
        }
        const iframeResize = () => {
            const iframe = this.iframeRef.el;
            if (this.state.isMobile) {
                // aspect-ratio of internal screen of /html_builder/static/img/phone.svg
                iframe.style.height = "668px";
                iframe.style.width = "367px";
                return;
            }
            iframe.style.width = "";
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
            if (!sidebar) {
                return;
            }
            if (this.state.showFullscreen) {
                sidebar.style.top = "0";
                sidebar.style.height = "100%";
            } else if (this.env.inDialog) {
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
                const maxHeight = this.state.isMobile
                    ? 1000
                    : Math.max(
                          // height to fill remaining viewport space on an unscrolled page
                          window.innerHeight - sidebar.parentElement.getBoundingClientRect().y - 5,
                          // height of the parent element
                          sidebar.parentElement.clientHeight
                      );
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
        useLayoutEffect(
            () => {
                this.iframeLoaded.promise.then(() => {
                    if (status(this) === "destroyed") {
                        return;
                    }
                    this.iframeRef.el.contentDocument.body.classList[
                        this.state.showFullscreen ? "add" : "remove"
                    ]("o_mass_mailing_iframe_fullscreen");
                    this.throttledResize();
                    this.editor?.shared.builderOverlay?.refreshOverlays();
                });
            },
            () => [this.state.showFullscreen]
        );
        useLayoutEffect(
            () => {
                this.iframeLoaded.promise.then(() => {
                    if (status(this) === "destroyed") {
                        return;
                    }
                    this.iframeRef.el.contentDocument.body.classList[
                        this.state.isMobile ? "add" : "remove"
                    ]("o_mass_mailing_iframe_mobile");
                    this.throttledResize();
                    this.editor?.shared.builderOverlay?.refreshOverlays();
                });
            },
            () => [this.state.isMobile]
        );
        onWillUnmount(() => {
            if (this.htmlResizeObserver) {
                this.htmlResizeObserver.disconnect();
            }
        });
        onWillDestroy(() => {
            this.iframeLoaded.resolve(false);
        });
    }

    get isBrowserSafari() {
        return isBrowserSafari();
    }

    async setupIframe() {
        let loadingError;
        try {
            this.bundleControls = await loadIframe(this.iframeRef.el, (iframe) => {
                iframe.contentDocument?.head.appendChild(this.renderHeadContent());
                return this.loadIframeAssets();
            });
        } catch (error) {
            loadingError = error;
        }
        if (status(this) === "destroyed") {
            return;
        } else if (loadingError) {
            throw loadingError;
        }
        this.htmlResizeObserver = new ResizeObserver(this.throttledResize);
        this.iframeRef.el.contentDocument.body.classList.add("o_in_iframe");
        if (this.props.withBuilder) {
            this.iframeRef.el.contentDocument.body.classList.add("o_mass_mailing_with_builder");
        } else {
            this.iframeRef.el.contentDocument.body.classList.add("bg-white");
        }
        this.iframeRef.el.contentDocument.body.appendChild(this.renderBodyContent());
        this.htmlResizeObserver.observe(
            this.iframeRef.el.contentDocument.body.querySelector(IFRAME_VALUE_SELECTOR)
        );
        if (this.props.readonly) {
            this.retargetLinks(
                this.iframeRef.el.contentDocument.body.querySelector(IFRAME_VALUE_SELECTOR)
            );
            this.fixInlineDynamicPlaceholders(this.iframeRef.el);
        }
        // Set `ready` symbol for tours
        this.iframeRef.el.setAttribute("is-ready", "true");
        this.iframeRef.el.contentWindow.addEventListener("beforeUnload", () => {
            this.iframeRef.el.removeAttribute("is-ready");
        });
        this.iframeRef.el.contentWindow.addEventListener("focus", this.props.onFocus.bind(this));
        this.iframeLoaded.resolve(this.iframeRef.el);
        this.state.ready = true;
    }

    /**
     * As no plugins are loaded in readonly mode, we manually set inlining attributes to
     * any t-element that might be present in the document, provided its children are inline
     * (which should always be the case for mass_mailing).
     * TODO: move this to a readonly plugin once they are implemented
     * @param {HTMLElement} iframe
     */
    fixInlineDynamicPlaceholders(iframe) {
        const checkAllInline = function (el) {
            return [...el.children].every((child) => {
                if (child.tagName === "T") {
                    return this.checkAllInline(child);
                } else {
                    return (
                        child.nodeType !== Node.ELEMENT_NODE ||
                        iframe.contentWindow.getComputedStyle(child).display === "inline"
                    );
                }
            });
        };
        for (const el of iframe.contentDocument.body.querySelectorAll("t")) {
            if (checkAllInline(el)) {
                el.setAttribute("data-oe-t-inline", "true");
            }
        }
    }

    async setupBasicEditor() {
        await this.iframeLoaded.promise;
        if (status(this) === "destroyed") {
            return;
        }
        this.editor.config.localOverlayContainers = {
            key: this.env.localOverlayContainerKey,
            ref: this.overlayRef,
        };
        this.editor.attachTo(
            this.iframeRef.el.contentDocument.body.querySelector(IFRAME_VALUE_SELECTOR)
        );
    }

    async loadIframeAssets() {
        const { readonly, withBuilder } = this.props;
        let iframeBundles;
        if (readonly) {
            iframeBundles = ["mass_mailing.assets_iframe_style"];
        } else if (withBuilder) {
            iframeBundles = ["mass_mailing.assets_inside_builder_iframe"];
        } else {
            iframeBundles = ["mass_mailing.assets_inside_basic_editor_iframe"];
        }
        return loadIframeBundles(this.iframeRef.el, iframeBundles);
    }

    renderHeadContent() {
        return renderToFragment("mass_mailing.IframeHead", this);
    }

    renderBodyContent() {
        return renderToFragment("mass_mailing.IframeBody", this);
    }

    getBuilderProps() {
        return {
            overlayRef: this.overlayRef,
            iframeLoaded: this.iframeLoaded.promise,
            snippetsName: "mass_mailing.email_designer_snippets",
            config: this.props.config,
            isMobile: this.state.isMobile,
            toggleMobile: () => {
                this.iframeRef.el.contentDocument.body.scrollTop = 0;
                this.state.isMobile = !this.state.isMobile;
            },
            editableSelector: IFRAME_VALUE_SELECTOR,
            onEditorLoad: (editor) => {
                if (this.editor) {
                    this.editor.destroy();
                }
                this.editor = editor;
                this.props.onEditorLoad(editor);
            },
            getThemeTab: () =>
                odoo.loader.modules.get("@mass_mailing/builder/tabs/design_tab").DesignTab,
            themeTabDisplayName: _t("Design"),
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

    toggleFullScreen() {
        this.state.showFullscreen = !this.state.showFullscreen;
    }
}
