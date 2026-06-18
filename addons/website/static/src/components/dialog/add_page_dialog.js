import { useExternalListener, useRef, useSubEnv } from "@web/owl2/utils";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { utils as uiUtils, SIZES } from "@web/core/ui/ui_service";
import { useDebounced } from "@web/core/utils/timing";
import { WebsiteDialog } from "@website/components/dialog/dialog";
import { useMatrixKeyNavigation } from "@html_builder/utils/keyboard_navigation";
import { Switch } from "@html_editor/components/switch/switch";
import {
    applyTextHighlight,
    removeTextHighlight,
    getObservedEls,
} from "@website/js/highlight_utils";
import { Component, onWillStart, onMounted, props, status, proxy, t } from "@odoo/owl";
import { onceAllImagesLoaded } from "@website/utils/images";

const NO_OP = () => {};

function isMobileView() {
    return uiUtils.getSize() < SIZES.MD;
}

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
        useAutofocus();

        this.state = proxy({
            addMenu: true,
            name: this.props.name,
            sectionsArch: this.props.sectionsArch,
            templateId: this.props.templateId,
        });
    }

    onChangeAddMenu(value) {
        this.state.addMenu = value;
    }

    async addPage() {
        await this.props.createPage(this.state.sectionsArch, this.state.name, this.state.addMenu);
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
        onPageKeydown: { type: Function },
    };

    setup() {
        super.setup();
        this.iframeRef = useRef("iframe");
        this.previewRef = useRef("preview");
        this.holderRef = useRef("holder");

        this.resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const targetEl = entry.target.querySelector(".o_text_highlight") || entry.target;
                removeTextHighlight(targetEl);
                applyTextHighlight(targetEl);
            }
        });

        onMounted(async () => {
            const holderEl = this.holderRef.el;
            holderEl.classList.add("o_loading");
            if (!this.props.template.key) {
                return;
            }
            const previewEl = this.previewRef.el;
            const iframeEl = this.iframeRef.el;
            // Firefox replaces the built content with about:blank.
            const isFirefox = isBrowserFirefox();
            if (isFirefox && !(iframeEl?.contentDocument.readyState === "complete")) {
                // Make sure empty preview iframe is loaded. This was necessary
                // in Firefox < 148 as it created and parsed a new document.
                // This event is never triggered on Chrome.
                await new Promise((resolve) => {
                    iframeEl.contentDocument.body.onload = resolve;
                });
            }
            // Apply styles.
            const cssLinkEls = await this.env.getCssLinkEls();
            if (status(this) === "destroyed") {
                return;
            }
            for (const cssLinkEl of cssLinkEls) {
                const preloadLinkEl = document.createElement("link");
                preloadLinkEl.setAttribute("rel", "preload");
                preloadLinkEl.setAttribute("href", cssLinkEl.getAttribute("href"));
                preloadLinkEl.setAttribute("as", "style");
                iframeEl.contentDocument.head.appendChild(preloadLinkEl);
                iframeEl.contentDocument.head.appendChild(cssLinkEl.cloneNode(true));
            }
            // Adjust styles.
            const styleEl = document.createElement("style");
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
                section.o_full_screen_height,
                section.o_half_screen_height,
                section.o_three_quarter_height {
                    height: unset !important;
                    min-height: unset !important;
                }
                section.o_full_screen_height {
                    aspect-ratio: 4 / 3;
                }
                section.o_three_quarter_height {
                    aspect-ratio: 16 / 9;
                }
                /* This is kept for compatibility */
                section.o_half_screen_height {
                    aspect-ratio: 8 / 3;
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
                .s_floating_blocks {
                    /* Make s_floating_blocks snippet look good. */
                    .s_floating_blocks_wrapper {
                        box-shadow: none !important;
                    }
                    .s_floating_blocks_block {
                        position: relative !important;
                        opacity: 1 !important;
                    }
                    .s_floating_blocks_block:nth-child(1) {
                        z-index: 1;
                        transform: scale(.96) !important;
                    }
                    .s_floating_blocks_block:nth-child(2) {
                        z-index: 2;
                        transform: scale(.98) !important;
                        margin-top: -45% !important;
                    }
                    .s_floating_blocks_block:nth-child(3) {
                        z-index: 3;
                        margin-top: -45% !important;
                    } 
                }
            `;
            const cssText = document.createTextNode(css);
            styleEl.appendChild(cssText);
            iframeEl.contentDocument.head.appendChild(styleEl);
            // Put blocks.
            // To preserve styles, the whole #wrapwrap > main > #wrap
            // nesting must be reproduced.
            const mainEl = document.createElement("main");
            const wrapwrapEl = document.createElement("div");
            wrapwrapEl.id = "wrapwrap";
            wrapwrapEl.appendChild(mainEl);
            iframeEl.contentDocument.body.appendChild(wrapwrapEl);
            const templateDocument = new DOMParser().parseFromString(
                this.props.template.template,
                "text/html"
            );
            const wrapEl = templateDocument.getElementById("wrap");
            mainEl.appendChild(wrapEl);
            // Make image loading eager.
            const lazyLoadedImgEls = wrapEl.querySelectorAll("img[loading=lazy]");
            for (const imgEl of lazyLoadedImgEls) {
                imgEl.setAttribute("loading", "eager");
            }
            mainEl.appendChild(wrapEl);
            await onceAllImagesLoaded(wrapEl);
            // Restore image lazy loading.
            for (const imgEl of lazyLoadedImgEls) {
                imgEl.setAttribute("loading", "lazy");
            }
            if (!this.previewRef.el) {
                // Stop the process when preview is removed
                return;
            }
            // Wait for fonts.
            await iframeEl.contentDocument.fonts.ready;
            holderEl.classList.remove("o_loading");
            const adjustHeight = () => {
                if (!this.previewRef.el) {
                    // Stop ajusting height when preview is removed.
                    return;
                }
                const outerWidth = parseInt(window.getComputedStyle(previewEl).width);
                const innerHeight = wrapEl.getBoundingClientRect().height;
                const innerWidth = wrapEl.getBoundingClientRect().width;
                const ratio = outerWidth / innerWidth;
                iframeEl.height = Math.round(innerHeight);
                iframeEl.style.transform = `scale(${ratio})`;
                previewEl.style.setProperty("height", `${Math.round(innerHeight * ratio)}px`);
                // Sometimes the final height is not ready yet.
                setTimeout(adjustHeight, 50);
                holderEl.classList.add("o_ready");
            };
            adjustHeight();
            if (this.props.isCustom) {
                this.adaptCustomTemplate(wrapEl);
            }
            for (const textEl of iframeEl.contentDocument?.querySelectorAll(".o_text_highlight") ||
                []) {
                for (const elToObserve of getObservedEls(textEl)) {
                    this.resizeObserver.observe(elToObserve);
                }
            }
        });
    }

    adaptCustomTemplate(wrapEl) {
        for (const sectionEl of wrapEl.querySelectorAll(
            "section:not(.o_snippet_desktop_invisible)"
        )) {
            const style = window.getComputedStyle(sectionEl);
            if (!style.height || style.display === "none") {
                const messageEl = renderToElement("website.AddPageTemplatePreviewDynamicMessage", {
                    message: _t(
                        "No preview for the %s block because it is dynamically rendered.",
                        sectionEl.dataset.name
                    ),
                });
                sectionEl.insertAdjacentElement("beforebegin", messageEl);
            }
        }
    }

    select() {
        if (this.holderRef.el.classList.contains("o_loading")) {
            return;
        }
        const wrapEl = this.iframeRef.el.contentDocument.getElementById("wrap").cloneNode(true);
        const templateId = this.props.template.key;
        for (const previewEl of wrapEl.querySelectorAll(
            ".o_new_page_snippet_preview, .s_dialog_preview"
        )) {
            previewEl.remove();
        }
        this.resizeObserver.disconnect();
        // Remove highlighted text content from the cloned page. The full
        // highlight structure will be restored on page load.
        for (const textHighlightEl of wrapEl.querySelectorAll(".o_text_highlight")) {
            removeTextHighlight(textHighlightEl);
        }
        this.env.addPage(
            wrapEl.innerHTML,
            this.props.template.name && _t("Copy of %s", this.props.template.name),
            templateId
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
        isSingleColumn: {
            type: Boolean,
            optional: true,
        },
    };
    static components = {
        AddPageTemplatePreview,
    };

    setup() {
        super.setup();
        this.container = useRef("previews-container");

        this.onPageKeydown = useMatrixKeyNavigation(
            () => [this.container.el],
            ".o_page_template",
            ".o_button_area"
        );
    }

    get columns() {
        const result = this.props.isSingleColumn ? [[]] : [[], [], []];
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
        defaultTemplateId: { type: String, optional: true },
    };
    static components = {
        AddPageTemplatePreviews,
    };

    setup() {
        super.setup();
        this.website = useService("website");
        this.tabsRef = useRef("tabs");
        this.panesRef = useRef("panes");
        useAutofocus();

        const isMobile = isMobileView();
        this.state = proxy({
            pages: [
                {
                    Component: AddPageTemplatePreviews,
                    title: _t("Loading..."),
                    isPreloading: true,
                    id: "loading",
                    props: { id: "loading", templates: [{}] },
                },
            ],
            activePageId: isMobile ? null : "loading",
            isMobile: isMobile,
        });
        this.pages = undefined;

        const onResize = () => {
            const isMobile = isMobileView();
            if (isMobile !== this.state.isMobile) {
                this.state.isMobile = isMobile;
                if (!isMobile && !this.state.activePageId) {
                    this.state.activePageId = this.state.pages[0]?.props.id;
                }
            }
        };
        useExternalListener(window, "resize", useDebounced(onResize, 100));

        onWillStart(() => {
            this.preparePages().then((pages) => {
                this.state.pages = pages;

                // Show the menu directly if we open the dialog in mobile view.
                if (this.state.isMobile) {
                    this.state.activePageId = null;
                    return;
                }

                if (
                    this.props.defaultTemplateId &&
                    this.state.pages.some((page) => page.id === this.props.defaultTemplateId)
                ) {
                    this.state.activePageId = this.props.defaultTemplateId;
                } else {
                    this.state.activePageId = this.state.pages[0]?.props.id;
                }
            });
        });
    }

    async preparePages() {
        // Fetch templates without client-side caching to reflect recent changes
        // to custom templates within the same session.
        const loadTemplates = rpc(
            "/website/get_new_page_templates",
            { context: { website_id: this.website.currentWebsiteId } },
            { silent: true }
        );

        // Forces the correct website if needed before fetching the templates.
        // Displaying the correct images in the previews also relies on the
        // website id having been forced.
        await this.env.getCssLinkEls();
        if (status(this) === "destroyed") {
            return new Promise(() => {});
        }

        if (this.pages) {
            return this.pages;
        }

        const newPageTemplates = await loadTemplates;
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
        return pages;
    }

    onTabListBtnClick(id) {
        this.state.activePageId = id;
        const tabEl = this.tabsRef.el.querySelector(`[data-id=${id}]`);
        this.props.onTemplatePageChanged(tabEl.textContent);
    }

    addBlankPage() {
        this.env.addPage();
    }

    get selectedPage() {
        return this.state.pages.find((p) => p.id === this.state.activePageId);
    }

    onMobileBackClick() {
        this.state.activePageId = null;
    }

    onTabListBtnKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (!["arrowleft", "arrowright", "arrowdown", "arrowup"].includes(hotkey)) {
            return;
        }
        const currentTabEl = this.tabsRef.el.querySelector(`[data-id=${ev.target.dataset.id}]`);
        if (["arrowleft", "arrowup"].includes(hotkey)) {
            currentTabEl.previousElementSibling?.focus();
        } else {
            currentTabEl.nextElementSibling?.focus();
        }
    }
}

export class AddPageDialog extends Component {
    static template = "website.AddPageDialog";
    props = props({
        close: t.function(),
        onAddPage: t.function().optional(() => NO_OP),
        websiteId: t.number(),
        forcedURL: t.string().optional(),
        goToPage: t.boolean().optional(true),
        pageTitle: t.string().optional(),
        defaultTemplateId: t.string().optional(),
    });
    static components = {
        WebsiteDialog,
        AddPageTemplates,
        AddPageTemplatePreviews,
    };

    setup() {
        super.setup();
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
        if (this.props.forcedURL) {
            // We also skip the possibility to choose to add in menu in that
            // case (e.g. in creation from 404 page button). The user can still
            // create its menu afterwards if needed.
            await this.createPage(sectionsArch, this.props.forcedURL, false, this.props.pageTitle);
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
        // Remove any leading slash.
        const pageName = name.replace(/^\/*/, "") || _t("New Page");
        const data = await this.http.post(`/website/add/${encodeURIComponent(pageName)}`, {
            // Needed to be passed as a (falsy) string because false would be
            // converted to 'false' with a POST.
            sections_arch: sectionsArch || "",
            add_menu: addMenu || "",

            website_id: this.props.websiteId,
            csrf_token: odoo.csrf_token,
            page_title: pageTitle,
        });
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
        this.props.onAddPage({ createdUrl: data.url });
        this.props.close();
    }

    getCssLinkEls() {
        if (!this.cssLinkEls) {
            this.cssLinkEls = new Promise((resolve) => {
                const container = document.querySelector(".o_website_preview .o_iframe_container");
                const iframe = container?.querySelector(
                    'iframe:not([src="/website/iframefallback"])'
                );
                if (iframe?.contentDocument.body.getAttribute("is-ready") === "true") {
                    // If there is a fully loaded website preview, use it.
                    resolve(iframe.contentDocument.head.querySelectorAll("link[type='text/css']"));
                } else {
                    // If there is no website preview or it was not ready yet, fetch page.
                    this.http
                        .get(`/website/force/${this.props.websiteId}?path=/`, "text")
                        .then((html) => {
                            const doc = new DOMParser().parseFromString(html, "text/html");
                            resolve(doc.head.querySelectorAll("link[type='text/css']"));
                        });
                }
            });
        }
        return this.cssLinkEls;
    }
}
