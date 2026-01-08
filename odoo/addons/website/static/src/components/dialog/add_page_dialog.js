/** @odoo-module **/

import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { Deferred } from "@web/core/utils/concurrency";
import { useAutofocus, useService } from '@web/core/utils/hooks';
import { _t } from "@web/core/l10n/translation";
import { WebsiteDialog } from '@website/components/dialog/dialog';
import { Switch } from '@website/components/switch/switch';
import { useRef, useState, useSubEnv, Component, onWillStart, onMounted } from "@odoo/owl";
import wUtils from '@website/js/utils';

const NO_OP = () => {};

export class AddPageConfirmDialog extends Component {
    setup() {
        super.setup();
        useAutofocus();

        this.title = _t("New Page");
        this.primaryTitle = _t("Create");
        this.switchLabel = _t("Add to menu");
        this.website = useService('website');
        this.http = useService('http');
        this.action = useService('action');

        this.state = useState({
            addMenu: true,
            name: this.props.name,
        });
    }

    onChangeAddMenu(value) {
        this.state.addMenu = value;
    }

    async addPage() {
        const params = {'add_menu': this.state.addMenu || '', csrf_token: odoo.csrf_token};
        if (this.props.sectionsArch) {
            params.sections_arch = this.props.sectionsArch;
        }
        // Remove any leading slash.
        const pageName = this.state.name.replace(/^\/*/, "") || _t("New Page");
        const url = `/website/add/${encodeURIComponent(pageName)}`;
        params['website_id'] = this.props.websiteId;
        const data = await this.http.post(url, params);
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
        this.props.onAddPage(this.state);
    }
}
AddPageConfirmDialog.props = {
    close: Function,
    onAddPage: {
        type: Function,
        optional: true,
    },
    websiteId: Number,
    sectionsArch: {
        type: String,
        optional: true,
    },
    name: String,
};
AddPageConfirmDialog.defaultProps = {
    onAddPage: NO_OP,
};
AddPageConfirmDialog.components = {
    Switch,
    WebsiteDialog,
};
AddPageConfirmDialog.template = "website.AddPageConfirmDialog";

export class AddPageTemplateBlank extends Component {
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
AddPageTemplateBlank.props = {
    firstRow: {
        type: Boolean,
        optional: true,
    },
};
AddPageTemplateBlank.template = "website.AddPageTemplateBlank";

export class AddPageTemplatePreview extends Component {
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
                #wrapwrap {
                    overflow: hidden;
                    padding-right: 0px;
                    padding-left: 0px;
                }
                section {
                    /* Avoid the zoom's missing pixel. */
                    transform: scale(101%);
                }
                section[data-snippet="s_carousel"],
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
            await wUtils.onceAllImagesLoaded($(wrapEl));
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
        });
    }

    select() {
        if (this.holderRef.el.classList.contains("o_loading")) {
            return;
        }
        const wrapEl = this.iframeRef.el.contentDocument.getElementById("wrap").cloneNode(true);
        for (const previewEl of wrapEl.querySelectorAll(".o_new_page_snippet_preview")) {
            previewEl.remove();
        }
        this.env.addPage(wrapEl.innerHTML);
    }
}
AddPageTemplatePreview.props = {
    template: Object,
    animationDelay: Number,
    firstRow: {
        type: Boolean,
        optional: true,
    },
};
AddPageTemplatePreview.template = "website.AddPageTemplatePreview";

export class AddPageTemplatePreviews extends Component {
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
AddPageTemplatePreviews.props = {
    templates: {
        type: Array,
        element: Object,
    },
};
AddPageTemplatePreviews.components = {
    AddPageTemplateBlank,
    AddPageTemplatePreview,
};
AddPageTemplatePreviews.template = "website.AddPageTemplatePreviews";

export class AddPageTemplates extends Component {
    setup() {
        super.setup();
        this.tabsRef = useRef("tabs");
        this.panesRef = useRef("panes");
        this.rpc = useService('rpc');

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
        // Forces the correct website if needed before fetching the templates.
        // Displaying the correct images in the previews also relies on the
        // website id having been forced.
        await this.env.getCssLinkEls();

        if (this.pages) {
            return this.pages;
        }

        const newPageTemplates = await this.rpc("/website/get_new_page_templates");
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

    onTabClick(id) {
        for (const page of this.state.pages) {
            if (page.id === id) {
                page.isAccessed = true;
            }
        }
        const activeTabEl = this.tabsRef.el.querySelector(".active");
        const activePaneEl = this.panesRef.el.querySelector(".active");
        activeTabEl?.classList?.remove("active");
        activePaneEl?.classList?.remove("active");
        const tabEl = this.tabsRef.el.querySelector(`[data-id=${id}]`);
        const paneEl = this.panesRef.el.querySelector(`[data-id=${id}]`);
        tabEl.classList.add("active");
        paneEl.classList.add("active");
        this.props.onTemplatePageChanged(tabEl.dataset.id === "basic" ? "" : tabEl.textContent);
    }
}
AddPageTemplates.props = {
    onTemplatePageChanged: Function,
};
AddPageTemplates.components = {
    AddPageTemplatePreviews,
};
AddPageTemplates.template = "website.AddPageTemplates";

export class AddPageDialog extends Component {
    setup() {
        super.setup();
        useAutofocus();

        this.title = _t("New Page");
        this.primaryTitle = _t("Create");
        this.switchLabel = _t("Add to menu");
        this.website = useService('website');
        this.dialogs = useService("dialog");
        this.orm = useService('orm');
        this.rpc = useService('rpc');
        this.http = useService('http');
        this.action = useService('action');
        this.userService = useService('user');

        this.cssLinkEls = undefined;
        this.lastTabName = "";

        useSubEnv({
            addPage: sectionsArch => this.addPage(sectionsArch),
            getCssLinkEls: () => this.getCssLinkEls(),
        });
    }

    onTemplatePageChanged(name) {
        this.lastTabName = name;
    }

    async addPage(sectionsArch) {
        const props = this.props;
        this.dialogs.add(AddPageConfirmDialog, {
            onAddPage: () => {
                props.onAddPage();
                props.close();
            },
            websiteId: this.props.websiteId,
            sectionsArch: sectionsArch,
            name: this.lastTabName,
        });
    }

    getCssLinkEls() {
        if (!this.cssLinkEls) {
            this.cssLinkEls = new Deferred();
            (async () => {
                let contentDocument;
                // Already in DOM ?
                const pageIframeEl = document.querySelector("iframe.o_iframe");
                if (pageIframeEl?.getAttribute("is-ready") === "true") {
                    // If there is a fully loaded website preview, use it.
                    contentDocument = pageIframeEl.contentDocument;
                }
                if (!contentDocument) {
                    // If there is no website preview or it was not ready yet, fetch page.
                    const html = await this.http.get(`/website/force/${this.props.websiteId}?path=/`, "text");
                    contentDocument = new DOMParser().parseFromString(html, "text/html");
                }
                this.cssLinkEls.resolve(contentDocument.head.querySelectorAll("link[type='text/css']"));
            })();
        }
        return this.cssLinkEls;
    }
}
AddPageDialog.props = {
    close: Function,
    onAddPage: {
        type: Function,
        optional: true,
    },
    websiteId: {
        type: Number,
    },
};
AddPageDialog.defaultProps = {
    onAddPage: NO_OP,
};
AddPageDialog.components = {
    WebsiteDialog,
    AddPageTemplates,
    AddPageTemplatePreviews,
};
AddPageDialog.template = "website.AddPageDialog";
