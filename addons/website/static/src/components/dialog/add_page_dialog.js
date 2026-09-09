/** @odoo-module native */
import { Switch } from "@html_editor/components/switch/switch";
import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    status,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { WebsiteDialog } from "@website/components/dialog/dialog";
import {
    applyTextHighlight,
    getObservedEls,
    removeTextHighlight,
} from "@website/js/highlight_utils";
import { onceAllImagesLoaded } from "@website/utils/images";

const NO_OP = () => {};

const log = makeLogger("website.dialog.add_page");

export class AddPageConfirmDialog extends Component {
    static template = "website.AddPageConfirmDialog";
    static props = {
        close: Function,
        createPage: Function,
        name: String,
        sectionsArch: String,
        templateId: String,
    };
    static components = {
        Switch,
        WebsiteDialog,
    };

    setup() {
        super.setup();
        useLifecycleLog(log);
        useAutofocus();

        this.state = useState({
            addMenu: true,
            name: this.props.name,
            sectionsArch: this.props.sectionsArch,
            templateId: this.props.templateId,
        });
    }

    onChangeAddMenu(value) {
        log.logic("AddPageConfirmDialog addMenu", { value });
        this.state.addMenu = value;
    }

    async addPage() {
        log.pipeline("AddPageConfirmDialog confirm", () => ({
            name: this.state.name,
            addMenu: this.state.addMenu,
            templateId: this.state.templateId,
        }));
        await this.props.createPage(
            this.state.sectionsArch,
            this.state.name,
            this.state.addMenu,
        );
    }
}

class AddPageTemplateBlank extends Component {
    static template = "website.AddPageTemplateBlank";
    static props = {
        firstRow: {
            type: Boolean,
            optional: true,
        },
    };

    setup() {
        super.setup();
        useLifecycleLog(log);
        this.holderRef = useRef("holder");

        onMounted(async () => {
            this.holderRef.el.classList.add("o_ready");
        });
    }

    select() {
        log.logic("AddPageTemplateBlank select");
        this.env.addPage();
    }
}

class AddPageTemplatePreview extends Component {
    static template = "website.AddPageTemplatePreview";
    static props = {
        template: Object,
        animationDelay: Number,
        firstRow: {
            type: Boolean,
            optional: true,
        },
        isCustom: {
            type: Boolean,
            optional: true,
        },
    };

    setup() {
        super.setup();
        useLifecycleLog(log);
        this.iframeRef = useRef("iframe");
        this.previewRef = useRef("preview");
        this.holderRef = useRef("holder");
        this.resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const targetEl =
                    entry.target.querySelector(".o_text_highlight") || entry.target;
                removeTextHighlight(targetEl);
                applyTextHighlight(targetEl);
            }
        });
        onWillUnmount(() => {
            log.lifecycle("AddPageTemplatePreview observer disconnected", () => ({
                key: this.props.template.key,
            }));
            this.resizeObserver.disconnect();
            clearTimeout(this._adjustHeightTimeout);
        });

        onMounted(async () => {
            const holderEl = this.holderRef.el;
            holderEl.classList.add("o_loading");
            if (!this.props.template.key) {
                log.logic("AddPageTemplatePreview skip: placeholder template");
                return;
            }
            const endPreview = log.perf("AddPageTemplatePreview render", () => ({
                key: this.props.template.key,
                isCustom: this.props.isCustom,
            }));
            const previewEl = this.previewRef.el;
            const iframeEl = this.iframeRef.el;
            const isFirefox = isBrowserFirefox();
            if (isFirefox) {
                log.logic("AddPageTemplatePreview firefox: wait iframe body load");
                await new Promise((resolve) => {
                    iframeEl.contentDocument.body.onload = resolve;
                });
            }
            for (const cssLinkEl of await this.env.getCssLinkEls()) {
                const preloadLinkEl = document.createElement("link");
                preloadLinkEl.setAttribute("rel", "preload");
                preloadLinkEl.setAttribute("href", cssLinkEl.getAttribute("href"));
                preloadLinkEl.setAttribute("as", "style");
                iframeEl.contentDocument.head.appendChild(preloadLinkEl);
                iframeEl.contentDocument.head.appendChild(cssLinkEl.cloneNode(true));
            }
            const styleEl = document.createElement("style");
            const fullHeight = getComputedStyle(
                document.querySelector(".o_action_manager"),
            ).height;
            const halfHeight = `${Math.round(parseInt(fullHeight) / 2)}px`;
            const css = `
                html, body {
                    /* Needed to prevent scrollbar to appear on chrome */
                    overflow: hidden;
                }
                #wrapwrap {
                    padding-right: 0px;
                    padding-left: 0px;
                    --snippet-preview-height: 340px;
                }
                section {
                    /* Avoid the zoom's missing pixel. */
                    transform: scale(101%);
                }
                section[data-snippet="s_carousel"],
                section[data-snippet="s_carousel_intro"],
                section[data-snippet="s_carousel_cards"],
                section[data-snippet="s_quotes_carousel_minimal"],
                section[data-snippet="s_quotes_carousel_compact"],
                section[data-snippet="s_quotes_carousel"] {
                    .carousel-inner, .carousel-inner > .carousel-item {
                        height: fit-content !important;
                    }
                }
                section.o_half_screen_height {
                    min-height: ${halfHeight} !important;
                }
                section.o_full_screen_height {
                    min-height: ${fullHeight} !important;
                }
                section[data-snippet="s_three_columns"] .figure-img[style*="height:50vh"] {
                    /* In Travel theme. */
                    height: 170px !important;
                }
                .o_we_shape {
                    /* Avoid the zoom's missing pixel. */
                    transform: scale(101%);
                }
                .o_animate {
                    visibility: visible;
                    animation-name: none;
                }
            `;
            const cssText = document.createTextNode(css);
            styleEl.appendChild(cssText);
            iframeEl.contentDocument.head.appendChild(styleEl);
            const mainEl = document.createElement("main");
            const wrapwrapEl = document.createElement("div");
            wrapwrapEl.id = "wrapwrap";
            wrapwrapEl.appendChild(mainEl);
            iframeEl.contentDocument.body.appendChild(wrapwrapEl);
            const templateDocument = new DOMParser().parseFromString(
                this.props.template.template,
                "text/html",
            );
            const wrapEl = templateDocument.getElementById("wrap");
            mainEl.appendChild(wrapEl);
            const lazyLoadedImgEls = wrapEl.querySelectorAll("img[loading=lazy]");
            log.pipeline("AddPageTemplatePreview template injected", () => ({
                key: this.props.template.key,
                lazyImages: lazyLoadedImgEls.length,
                sections: wrapEl.children.length,
            }));
            for (const imgEl of lazyLoadedImgEls) {
                imgEl.setAttribute("loading", "eager");
            }
            const endImages = log.perf("AddPageTemplatePreview images loaded");
            // A single broken image must not reject and abort the rest of the
            // setup (fonts.ready, o_loading removal, adjustHeight), which would
            // leave the preview stuck loading.
            await onceAllImagesLoaded(wrapEl).catch(() => {});
            endImages();
            for (const imgEl of lazyLoadedImgEls) {
                imgEl.setAttribute("loading", "lazy");
            }
            if (!this.previewRef.el) {
                log.logic("AddPageTemplatePreview unmounted while loading images");
                return;
            }
            await iframeEl.contentDocument.fonts.ready;
            endPreview();
            holderEl.classList.remove("o_loading");
            let lastHeight = -1;
            let stableCount = 0;
            const adjustHeight = () => {
                if (!this.previewRef.el) {
                    return;
                }
                const outerWidth = parseInt(window.getComputedStyle(previewEl).width);
                const innerHeight = wrapEl.getBoundingClientRect().height;
                const innerWidth = wrapEl.getBoundingClientRect().width;
                const ratio = outerWidth / innerWidth;
                const rounded = Math.round(innerHeight);
                iframeEl.height = rounded;
                previewEl.style.setProperty(
                    "height",
                    `${Math.round(innerHeight * ratio)}px`,
                );
                holderEl.classList.add("o_ready");
                stableCount = rounded === lastHeight ? stableCount + 1 : 0;
                lastHeight = rounded;
                if (stableCount < 5) {
                    this._adjustHeightTimeout = setTimeout(adjustHeight, 50);
                }
            };
            adjustHeight();
            if (this.props.isCustom) {
                log.logic("AddPageTemplatePreview adapt custom template");
                this.adaptCustomTemplate(wrapEl);
            }
            log.pipeline("AddPageTemplatePreview observe text highlights", () => ({
                highlights:
                    iframeEl.contentDocument?.querySelectorAll(".o_text_highlight")
                        .length || 0,
            }));
            for (const textEl of iframeEl.contentDocument?.querySelectorAll(
                ".o_text_highlight",
            ) || []) {
                for (const elToObserve of getObservedEls(textEl)) {
                    this.resizeObserver.observe(elToObserve);
                }
            }
        });
    }

    adaptCustomTemplate(wrapEl) {
        for (const sectionEl of wrapEl.querySelectorAll(
            "section:not(.o_snippet_desktop_invisible)",
        )) {
            const style = window.getComputedStyle(sectionEl);
            if (!style.height || style.display === "none") {
                log.logic("adaptCustomTemplate dynamic section: no preview", () => ({
                    snippet: sectionEl.dataset.snippet,
                    name: sectionEl.dataset.name,
                }));
                const messageEl = renderToElement(
                    "website.AddPageTemplatePreviewDynamicMessage",
                    {
                        message: _t(
                            "No preview for the %s block because it is dynamically rendered.",
                            sectionEl.dataset.name,
                        ),
                    },
                );
                sectionEl.insertAdjacentElement("beforebegin", messageEl);
            }
        }
    }

    select() {
        if (this.holderRef.el.classList.contains("o_loading")) {
            log.logic("AddPageTemplatePreview select ignored: still loading");
            return;
        }
        const wrapEl = this.iframeRef.el.contentDocument
            .getElementById("wrap")
            .cloneNode(true);
        const templateId = this.props.template.key;
        for (const previewEl of wrapEl.querySelectorAll(
            ".o_new_page_snippet_preview, .s_dialog_preview",
        )) {
            previewEl.remove();
        }
        this.resizeObserver.disconnect();
        for (const textHighlightEl of wrapEl.querySelectorAll(".o_text_highlight")) {
            removeTextHighlight(textHighlightEl);
        }
        log.pipeline("AddPageTemplatePreview select", () => ({
            templateId,
            sections: wrapEl.children.length,
        }));
        this.env.addPage(
            wrapEl.innerHTML,
            this.props.template.name && _t("Copy of %s", this.props.template.name),
            templateId,
        );
    }
}

class AddPageTemplatePreviews extends Component {
    static template = "website.AddPageTemplatePreviews";
    static props = {
        isCustom: {
            type: Boolean,
            optional: true,
        },
        templates: {
            type: Array,
            element: Object,
        },
    };
    static components = {
        AddPageTemplateBlank,
        AddPageTemplatePreview,
    };

    setup() {
        super.setup();
        useLifecycleLog(log);
    }

    get columns() {
        const result = [[], [], []];
        let currentColumnIndex = 0;
        for (const template of this.props.templates) {
            result[currentColumnIndex].push(template);
            currentColumnIndex = (currentColumnIndex + 1) % result.length;
        }
        return result;
    }
}

class AddPageTemplates extends Component {
    static template = "website.AddPageTemplates";
    static props = {
        onTemplatePageChanged: Function,
    };
    static components = {
        AddPageTemplatePreviews,
    };

    setup() {
        super.setup();
        useLifecycleLog(log);
        this.website = useService("website");
        this.tabsRef = useRef("tabs");
        this.panesRef = useRef("panes");
        useAutofocus();

        this.state = useState({
            pages: [
                {
                    Component: AddPageTemplatePreviews,
                    title: _t("Loading..."),
                    isPreloading: true,
                    props: {
                        id: "basic",
                        title: _t("Basic"),
                        templates: [{ isBlank: true }, {}, {}, {}, {}, {}],
                    },
                },
            ],
        });
        this.pages = undefined;

        onWillStart(() => {
            this.preparePages().then((pages) => {
                log.pipeline("AddPageTemplates pages ready", () => ({
                    pages: pages.length,
                }));
                this.state.pages = pages;
            });
        });
    }

    async preparePages() {
        const loadTemplates = rpc(
            "/website/get_new_page_templates",
            { context: { website_id: this.website.currentWebsiteId } },
            { silent: true },
        );

        const endCss = log.perf("AddPageTemplates await css links");
        await this.env.getCssLinkEls();
        endCss();
        if (status(this) === "destroyed") {
            log.logic("preparePages abort: destroyed");
            return new Promise(() => {});
        }

        if (this.pages) {
            log.logic("preparePages cached");
            return this.pages;
        }

        const endTemplates = log.perf("get_new_page_templates");
        const newPageTemplates = await loadTemplates;
        endTemplates(() => ({ groups: newPageTemplates.length }));
        newPageTemplates[0].templates.unshift({
            isBlank: true,
        });
        const pages = [];
        for (const template of newPageTemplates) {
            pages.push({
                Component: AddPageTemplatePreviews,
                title: template.title,
                props: template,
                id: `${template.id}`,
            });
        }
        this.pages = pages;
        log.pipeline("preparePages built", () => ({
            pages: pages.length,
            templates: newPageTemplates.reduce((n, t) => n + t.templates.length, 0),
        }));
        return pages;
    }

    onTabListBtnClick(id) {
        log.logic("AddPageTemplates tab", { id });
        for (const page of this.state.pages) {
            if (page.id === id) {
                page.isAccessed = true;
            }
        }
        const activeTabEl = this.tabsRef.el.querySelector(".active");
        const activePaneEl = this.panesRef.el.querySelector(".active");
        activeTabEl?.classList?.remove("active");
        activeTabEl?.setAttribute("tabIndex", "-1");
        activePaneEl?.classList?.remove("active");
        activePaneEl?.setAttribute("inert", "inert");
        const tabEl = this.tabsRef.el.querySelector(`[data-id=${id}]`);
        const paneEl = this.panesRef.el.querySelector(`[data-id=${id}]`);
        tabEl.classList.add("active");
        tabEl.tabIndex = 0;
        paneEl.classList.add("active");
        paneEl.removeAttribute("inert");
        this.props.onTemplatePageChanged(
            tabEl.dataset.id === "basic" ? "" : tabEl.textContent,
        );
    }

    onTabListBtnKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (!["arrowleft", "arrowright", "arrowdown", "arrowup"].includes(hotkey)) {
            return;
        }
        const currentTabEl = this.tabsRef.el.querySelector(
            `[data-id=${ev.target.dataset.id}]`,
        );
        if (["arrowleft", "arrowup"].includes(hotkey)) {
            currentTabEl.previousElementSibling?.focus();
        } else {
            currentTabEl.nextElementSibling?.focus();
        }
    }
}

export class AddPageDialog extends Component {
    static template = "website.AddPageDialog";
    static props = {
        close: Function,
        onAddPage: {
            type: Function,
            optional: true,
        },
        websiteId: {
            type: Number,
        },
        forcedURL: {
            type: String,
            optional: true,
        },
        goToPage: {
            type: Boolean,
            optional: true,
        },
        pageTitle: {
            type: String,
            optional: true,
        },
    };
    static defaultProps = {
        onAddPage: NO_OP,
        goToPage: true,
    };
    static components = {
        WebsiteDialog,
        AddPageTemplates,
        AddPageTemplatePreviews,
    };

    setup() {
        super.setup();
        useLifecycleLog(log);
        useAutofocus();

        this.primaryTitle = _t("Create");
        this.switchLabel = _t("Add to menu");
        this.website = useService("website");
        this.dialogs = useService("dialog");
        this.http = useService("http");
        this.action = useService("action");

        this.cssLinkEls = undefined;
        this.lastTabName = "";

        useSubEnv({
            addPage: (sectionsArch, name, templateId) =>
                this.addPage(sectionsArch, name, templateId),
            getCssLinkEls: () => this.getCssLinkEls(),
        });
    }

    onTemplatePageChanged(name) {
        this.lastTabName = name;
    }

    async addPage(sectionsArch, name, templateId) {
        log.logic("addPage", () => ({
            forcedURL: this.props.forcedURL,
            templateId,
            blank: !sectionsArch,
        }));
        if (this.props.forcedURL) {
            await this.createPage(
                sectionsArch,
                this.props.forcedURL,
                false,
                this.props.pageTitle,
            );
        } else {
            this.dialogs.add(AddPageConfirmDialog, {
                createPage: (...args) => this.createPage(...args),
                name: name || this.lastTabName,
                sectionsArch: sectionsArch || "",
                templateId: templateId || "",
            });
        }
    }

    async createPage(sectionsArch, name = "", addMenu = false, pageTitle = "") {
        log.logic("createPage", () => ({
            name,
            addMenu,
            pageTitle,
            sections: Boolean(sectionsArch),
        }));
        const pageName = name.replace(/^\/*/, "") || _t("New Page");
        const endPost = log.perf("createPage /website/add", { pageName });
        const data = await this.http.post(
            `/website/add/${encodeURIComponent(pageName)}`,
            {
                sections_arch: sectionsArch || "",
                add_menu: addMenu || "",

                website_id: this.props.websiteId,
                csrf_token: odoo.csrf_token,
                page_title: pageTitle,
            },
        );
        endPost(() => ({ url: data.url, viewId: data.view_id }));
        log.logic("createPage after create", () => ({
            openViewForm: Boolean(data.view_id),
            goToPage: this.props.goToPage,
        }));
        if (data.view_id) {
            this.action.doAction({
                res_model: "ir.ui.view",
                res_id: data.view_id,
                views: [[false, "form"]],
                type: "ir.actions.act_window",
                view_mode: "form",
            });
        } else if (this.props.goToPage) {
            this.website.goToWebsite({
                path: data.url,
                edition: true,
                websiteId: this.props.websiteId,
            });
        }
        this.props.onAddPage();
        this.props.close();
    }

    getCssLinkEls() {
        if (!this.cssLinkEls) {
            this.cssLinkEls = new Promise((resolve) => {
                const container = document.querySelector(
                    ".o_website_preview .o_iframe_container",
                );
                const iframe = container?.querySelector(
                    'iframe:not([src="/website/iframefallback"])',
                );
                if (iframe?.contentDocument.body.getAttribute("is-ready") === "true") {
                    log.logic("getCssLinkEls from preview iframe");
                    resolve(
                        iframe.contentDocument.head.querySelectorAll(
                            "link[type='text/css']",
                        ),
                    );
                } else {
                    log.logic("getCssLinkEls fetch homepage", () => ({
                        iframe: Boolean(iframe),
                    }));
                    const endFetch = log.perf("getCssLinkEls fetch /website/force");
                    this.http
                        .get(`/website/force/${this.props.websiteId}?path=/`, "text")
                        .then((html) => {
                            endFetch(() => ({ bytes: html.length }));
                            const doc = new DOMParser().parseFromString(
                                html,
                                "text/html",
                            );
                            resolve(doc.head.querySelectorAll("link[type='text/css']"));
                        });
                }
            });
        }
        return this.cssLinkEls;
    }
}
