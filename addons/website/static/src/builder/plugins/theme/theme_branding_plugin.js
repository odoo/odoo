import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { TitlePlugin } from "@web/core/browser/title_plugin";
import { usePlugin } from "@odoo/owl";

const HEADER_LOGO_SELECTOR = ".navbar-brand.logo span img";
const LOGO_SELECTOR = `${HEADER_LOGO_SELECTOR}, .o_footer_logo img`;
// Styles set by rotating or stretching the old logo image
// Width excluded: the footer uses it to set the logo size
const LOGO_STYLES_TO_REMOVE = [
    "transform",
    "transform-box",
    "transform-origin",
    "transform-style",
    "height",
];

function applyLogo(root, pickedImgEl) {
    for (const logoEl of root.querySelectorAll(LOGO_SELECTOR)) {
        for (const key of Object.keys(logoEl.dataset)) {
            delete logoEl.dataset[key];
        }
        for (const property of LOGO_STYLES_TO_REMOVE) {
            logoEl.style.removeProperty(property);
        }
        logoEl.setAttribute("src", pickedImgEl.getAttribute("src"));
        logoEl.removeAttribute("srcset");
        logoEl.classList.toggle(
            "o_modified_image_to_save",
            pickedImgEl.classList.contains("o_modified_image_to_save")
        );
        Object.assign(logoEl.dataset, pickedImgEl.dataset);
    }
}

// Invisible mark added to a previewed title, used to force Chrome to refresh
// the tab label.
const PREVIEW_TITLE_MARK = "\u200b";
// What the website serves as favicon when it has none.
const FAVICON_PLACEHOLDER_URL = "/web/static/img/placeholder.png";
// `document.title` collapses spaces.
const collapseSpaces = (text) => text.replace(/[\t\n\f\r ]+/g, " ").trim();

const FIELD_ERROR_MESSAGES = {
    name: (reason) => _t("The website name could not be saved: %s", reason),
    favicon: (reason) => _t("The favicon could not be saved: %s", reason),
    logo: (reason) => _t("The logo could not be saved: %s", reason),
};

class RemoveFaviconAction extends BuilderAction {
    static id = "removeFavicon";

    apply({ editingElement }) {
        editingElement.dataset.favicon = "false";
        delete editingElement.dataset.faviconSrc;
    }
}

class ReplaceBrandingImageAction extends BuilderAction {
    static id = "replaceBrandingImage";
    static dependencies = ["media"];

    setup() {
        this.canTimeout = false;
    }

    apply({ editingElement, params: { mainParam: field } }) {
        return this.dependencies.media.openMediaDialog({
            resModel: "website",
            resId: this.services.website.currentWebsite.id,
            onlyImages: true,
            useMediaLibrary: false,
            save: (imgEl) => {
                const attachmentId = imgEl.dataset.attachmentId;
                if (field === "logo") {
                    applyLogo(this.document, imgEl);
                    editingElement.dataset.logo = attachmentId;
                } else {
                    editingElement.dataset.favicon = attachmentId;
                    editingElement.dataset.faviconSrc = `/web/image/${attachmentId}`;
                }
            },
        });
    }
}

export class ThemeBrandingPlugin extends Plugin {
    static id = "themeBranding";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            ReplaceBrandingImageAction,
            RemoveFaviconAction,
        },
        on_ready_to_save_document_handlers: () => this.saveBranding(),
    };

    setup() {
        this.brandingHiddenEl = this.editable.querySelector("#o_website_branding");
        if (!this.brandingHiddenEl) {
            return;
        }
        this.titlePlugin = usePlugin(TitlePlugin);
        this.originalTitle = this.document.title;
        this.titlePrefix = this.getTitlePrefix();
        this.faviconLinkEl = document.querySelector("link[rel~='icon']");
        this.originalFaviconHref = this.faviconLinkEl.href;
        this.previewObserver = new MutationObserver(() => this.showPreview());
        this.previewObserver.observe(this.brandingHiddenEl, {
            attributeFilter: ["data-website-name", "data-favicon", "data-favicon-src"],
        });
    }

    destroy() {
        if (this.brandingHiddenEl) {
            this.previewObserver.disconnect();
            if (this.faviconLinkEl.href === this.previewFaviconHref) {
                this.faviconLinkEl.href = this.originalFaviconHref;
            }
        }
        super.destroy();
    }

    /**
     * @returns {string|null} the page title without the website name, or null
     * if the page has its own (SEO) title: the name isn't in it.
     */
    getTitlePrefix() {
        const defaultTitle = this.document.querySelector("meta[name='default_title']")?.content;
        const savedName = collapseSpaces(this.brandingHiddenEl.dataset.savedName);
        if (
            !defaultTitle ||
            collapseSpaces(defaultTitle) !== this.originalTitle ||
            !this.originalTitle.endsWith(savedName)
        ) {
            return null;
        }
        return this.originalTitle.slice(0, this.originalTitle.length - savedName.length);
    }

    showPreview() {
        const { websiteName, favicon, faviconSrc } = this.brandingHiddenEl.dataset;
        if (this.titlePrefix !== null) {
            const title = this.titlePrefix + collapseSpaces(websiteName);
            this.titlePlugin.setParts({
                action: title === this.originalTitle ? title : title + PREVIEW_TITLE_MARK,
            });
        }
        this.faviconLinkEl.href = favicon
            ? faviconSrc || FAVICON_PLACEHOLDER_URL
            : this.originalFaviconHref;
        this.previewFaviconHref = this.faviconLinkEl.href;
    }

    getPayload() {
        const { websiteName, savedName, favicon, logo } = this.brandingHiddenEl.dataset;
        const payload = {};
        if (websiteName.trim() !== savedName.trim()) {
            payload.name = websiteName;
        }
        if (favicon) {
            payload.favicon = favicon === "false" ? false : parseInt(favicon, 10);
        }
        // With a header logo image, the page save updates the logo field.
        if (logo && !this.document.querySelector(HEADER_LOGO_SELECTOR)) {
            payload.logo = parseInt(logo, 10);
        }
        return payload;
    }

    async saveBranding() {
        if (!this.brandingHiddenEl) {
            return;
        }
        const payload = this.getPayload();
        if (!Object.keys(payload).length) {
            return;
        }
        let errors;
        try {
            errors = await this.services.orm.call("website", "update_branding", [
                [this.services.website.currentWebsite.id],
                payload,
            ]);
        } catch (error) {
            this.notifyError(
                _t(
                    "The website branding could not be saved: %s",
                    error.data?.message || error.message
                )
            );
            return;
        }
        for (const [field, reason] of Object.entries(errors)) {
            this.notifyError(FIELD_ERROR_MESSAGES[field](reason));
        }
        if ("name" in payload && !("name" in errors)) {
            await this.services.website.fetchWebsites().catch(() => {});
        }
    }

    notifyError(message) {
        this.services.notification.add(message, { type: "danger", sticky: true });
    }
}

registry.category("website-plugins").add(ThemeBrandingPlugin.id, ThemeBrandingPlugin);
