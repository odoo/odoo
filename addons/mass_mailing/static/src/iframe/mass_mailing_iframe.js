import {
    Component,
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
import { useChildRef, useForwardRefToParent } from "@web/core/utils/hooks";
import { renderToFragment } from "@web/core/utils/render";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { Editor } from "@html_editor/editor";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { closestScrollableY } from "@web/core/utils/scrolling";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";

const IFRAME_VALUE_SELECTOR = ".o_mass_mailing_value";

export class MassMailingIframe extends Component {
    static template = "mass_mailing.MassMailingIframe";
    static components = {
        LazyComponent,
        LocalOverlayContainer,
    };
    static props = {
        config: { type: Object },
        iframeRef: { type: Function },
        showThemeSelector: { type: Boolean, optional: true },
        onIframeLoad: { type: Function, optional: true },
        showCodeView: { type: Boolean, optional: true },
        toggleCodeView: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
        onEditorLoad: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
        extraClass: { type: String, optional: true },
        withBuilder: { type: Boolean, optional: true },
    };
    static defaultProps = {
        onEditorLoad: () => {},
    };

    setup() {
        this.overlayRef = useChildRef();
        this.iframeRef = useForwardRefToParent("iframeRef");
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
        onWillUpdateProps((nextProps) => {
            if (nextProps.showCodeView) {
                this.state.showFullscreen = false;
            }
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
            const iframe = this.iframeRef.el;
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
                    : iframe.getBoundingClientRect().height;
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
        useEffect(
            () => {
                this.iframeLoaded.then(() => {
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
        useEffect(
            () => {
                this.iframeLoaded.then(() => {
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
    }

    async setupIframe() {
        await this.loadIframeAssets();
        if (status(this) === "destroyed") {
            return;
        }
        const htmlResizeObserver = new ResizeObserver(this.throttledResize);
        this.iframeRef.el.contentDocument.body.classList.add("o_in_iframe");
        if (this.props.withBuilder) {
            this.iframeRef.el.contentDocument.body.classList.add("o_mass_mailing_with_builder");
        } else {
            this.iframeRef.el.contentDocument.body.classList.add("bg-white");
        }
        this.iframeRef.el.contentDocument.head.appendChild(this.renderHeadContent());
        this.iframeRef.el.contentDocument.body.appendChild(this.renderBodyContent());
        htmlResizeObserver.observe(
            this.iframeRef.el.contentDocument.body.querySelector(IFRAME_VALUE_SELECTOR)
        );
        if (this.props.readonly) {
            this.retargetLinks(
                this.iframeRef.el.contentDocument.body.querySelector(IFRAME_VALUE_SELECTOR)
            );
        }
        // Set `ready` symbol for tours
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

    async loadIframeAssets() {
        await Promise.all([
            loadBundle("mass_mailing.assets_iframe_style", {
                targetDoc: this.iframeRef.el.contentDocument,
                css: true,
                js: false,
            }),
        ]);
    }

    onBlur(ev) {
        if (!this.props.readonly) {
            this.props.onBlur(ev);
        }
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
            iframeLoaded: this.iframeLoaded,
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
