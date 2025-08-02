import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";
import { useAutofocus, useService } from '@web/core/utils/hooks';
import { _t } from "@web/core/l10n/translation";
import { WebsiteDialog } from '@website/components/dialog/dialog';
import { Switch } from '@html_editor/components/switch/switch';
import { applyTextHighlight } from "@website/js/text_processing";
import { useRef, useState, useSubEnv, Component, onWillStart, onMounted, status } from "@odoo/owl";
import { onceAllImagesLoaded } from "@website/utils/images";

const NO_OP = () => {};

export class AddPageConfirmDialog extends Component {
    static template = "website.AddPageConfirmDialog";
    static props = {
        close: Function,
        createPage: Function,
        name: String,
    };
    static components = {
        Switch,
        WebsiteDialog,
    };

    setup() {
        super.setup();
        useAutofocus();

        this.state = useState({
            addMenu: true,
            name: this.props.name,
        });
    }

    onChangeAddMenu(value) {
        this.state.addMenu = value;
    }

    async addPage() {
        await this.props.createPage(this.state.name, this.state.addMenu);
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
        this.holderRef = useRef("holder");

        onMounted(async () => {
            this.holderRef.el.classList.add("o_ready");
        });
    }

    select() {
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
        this.iframeRef = useRef("iframe");
        this.previewRef = useRef("preview");
        this.holderRef = useRef("holder");

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
            if (isFirefox) {
                // Make sure empty preview iframe is loaded.
                // This event is never triggered on Chrome.
                await new Promise(resolve => {
                    iframeEl.contentDocument.body.onload = resolve;
                });
            }
            // Apply styles.
            for (const cssLinkEl of await this.env.getCssLinkEls()) {
                const preloadLinkEl = document.createElement("link");
                preloadLinkEl.setAttribute("rel", "preload");
                preloadLinkEl.setAttribute("href", cssLinkEl.getAttribute("href"));
                preloadLinkEl.setAttribute("as", "style");
                iframeEl.contentDocument.head.appendChild(preloadLinkEl);
                iframeEl.contentDocument.head.appendChild(cssLinkEl.cloneNode(true));
            }
            // Adjust styles.
            const styleEl = document.createElement("style");
            // Does not work with fit-content in Firefox.
            const carouselHeight = isFirefox ? '450px' : 'fit-content';
            // Prevent successive resizes.
            const fullHeight = getComputedStyle(document.querySelector(".o_action_manager")).height;
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
                    height: ${carouselHeight} !important;
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
            // Put blocks.
            // To preserve styles, the whole #wrapwrap > main > #wrap
            // nesting must be reproduced.
            const mainEl = document.createElement("main");
            const wrapwrapEl = document.createElement("div");
            wrapwrapEl.id = "wrapwrap";
            wrapwrapEl.appendChild(mainEl);
            iframeEl.contentDocument.body.appendChild(wrapwrapEl);
            const templateDocument = new DOMParser().parseFromString(this.props.template.template, "text/html");
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
                previewEl.style.setProperty("height", `${Math.round(innerHeight * ratio)}px`);
                // Sometimes the final height is not ready yet.
                setTimeout(adjustHeight, 50);
                holderEl.classList.add("o_ready");
            };
            adjustHeight();
            if (this.props.isCustom) {
                this.adaptCustomTemplate(wrapEl);
            }
            // We need this to correctly compute the highlights size (the
            // `ResizeObserver` that adapts the effects when a custom font
            // is applied is not available), for now, we need a setTimeout.
            setTimeout(() => {
                for (const textEl of iframeEl.contentDocument?.querySelectorAll(".o_text_highlight") || []) {
                    applyTextHighlight(textEl);
                }
            }, 200);
        });
    }

    adaptCustomTemplate(wrapEl) {
        for (const sectionEl of wrapEl.querySelectorAll("section:not(.o_snippet_desktop_invisible)")) {
            const style = window.getComputedStyle(sectionEl);
            if (!style.height || style.display === 'none') {
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
        for (const previewEl of wrapEl.querySelectorAll(".o_new_page_snippet_preview, .s_dialog_preview")) {
            previewEl.remove();
        }
        this.env.addPage(wrapEl.innerHTML, this.props.template.name && _t("Copy of %s", this.props.template.name));
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
        this.website = useService("website");
        this.tabsRef = useRef("tabs");
        this.panesRef = useRef("panes");
        useAutofocus();

        this.state = useState({
            pages: [{
                Component: AddPageTemplatePreviews,
                title: _t("Loading..."),
                isPreloading: true,
                props: {
                    id: "basic",
                    title: _t("Basic"),
                    // Blank and 5 preloading boxes.
                    templates: [{ isBlank: true }, {}, {}, {}, {}, {}],
                },
            }],
        });
        this.pages = undefined;

        onWillStart(() => {
            this.preparePages().then(pages => {
                this.state.pages = pages;
            });
        });
    }

    async preparePages() {
        const loadTemplates = rpc("/website/get_new_page_templates", { context: { website_id: this.website.currentWebsiteId}}, { cache: true, silent: true });

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
        return pages;
    }

    onTabListBtnClick(id) {
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
        activePaneEl?.setAttribute("inert", "inert"); // Make sure trapFocus() works.
        const tabEl = this.tabsRef.el.querySelector(`[data-id=${id}]`);
        const paneEl = this.panesRef.el.querySelector(`[data-id=${id}]`);
        tabEl.classList.add("active");
        tabEl.tabIndex = 0;
        paneEl.classList.add("active");
        paneEl.removeAttribute("inert");
        this.props.onTemplatePageChanged(tabEl.dataset.id === "basic" ? "" : tabEl.textContent);
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
    };
    static defaultProps = {
        onAddPage: NO_OP,
    };
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
        this.website = useService('website');
        this.dialogs = useService("dialog");
        this.http = useService('http');
        this.action = useService('action');

        this.cssLinkEls = undefined;
        this.lastTabName = "";

        useSubEnv({
            addPage: (sectionsArch, name) => this.addPage(sectionsArch, name),
            getCssLinkEls: () => this.getCssLinkEls(),
        });
    }

    onTemplatePageChanged(name) {
        this.lastTabName = name;
    }

    async addPage(sectionsArch, name) {
        if (this.props.forcedURL) {
            // We also skip the possibility to choose to add in menu in that
            // case (e.g. in creation from 404 page button). The user can still
            // create its menu afterwards if needed.
            await this.createPage(sectionsArch, this.props.forcedURL);
        } else {
            this.dialogs.add(AddPageConfirmDialog, {
                createPage: (...args) => this.createPage(sectionsArch, ...args),
                name: name || this.lastTabName,
            });
        }
    }

    async createPage(sectionsArch, name = "", addMenu = false) {
        // Remove any leading slash.
        const pageName = name.replace(/^\/*/, "") || _t("New Page");
        const data = await this.http.post(`/website/add/${encodeURIComponent(pageName)}`, {
            // Needed to be passed as a (falsy) string because false would be
            // converted to 'false' with a POST.
            'sections_arch': sectionsArch || '',
            'add_menu': addMenu || '',

            'website_id': this.props.websiteId,
            'csrf_token': odoo.csrf_token,
        });
        if (data.view_id) {
            this.action.doAction({
                'res_model': 'ir.ui.view',
                'res_id': data.view_id,
                'views': [[false, 'form']],
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
            });
        } else {
            this.website.goToWebsite({path: data.url, edition: true, websiteId: this.props.websiteId});
        }
        this.props.onAddPage();
        this.props.close();
    }

    getCssLinkEls() {
        if (!this.cssLinkEls) {
            this.cssLinkEls = new Promise((resolve) => {
                const container = document.querySelector(".o_website_preview .o_iframe_container");
                const iframe = container?.lastElementChild;
                if (iframe?.contentDocument.body.getAttribute("is-ready") === "true") {
                    // If there is a fully loaded website preview, use it.
                    resolve(iframe.contentDocument.head.querySelectorAll("link[type='text/css']"));
                } else {
                    // If there is no website preview or it was not ready yet, fetch page.
                    this.http.get(`/website/force/${this.props.websiteId}?path=/`, "text").then(html => {
                        const doc = new DOMParser().parseFromString(html, "text/html");
                        resolve(doc.head.querySelectorAll("link[type='text/css']"));
                    });
                }
            });
        }
        return this.cssLinkEls;
    }
}
