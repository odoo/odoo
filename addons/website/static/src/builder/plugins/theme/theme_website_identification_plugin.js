import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { signal } from "@odoo/owl";
import {
    SetWebsiteNameAction,
    ReplaceFaviconAction,
    ReplaceLogoAction,
    RemoveFaviconAction,
    RestoreLogoAction,
} from "./theme_website_identification_action";
import {
    LOGO_OPTION_CONFIG,
    LOGO_TARGETS_NAME,
    getInitialLogoState,
    applyLogo,
    applyFavicon,
    applyWebsiteName,
    buildMediaUrl,
    MAIN_LOGO_TARGET,
    getLogoElements,
    observeLogoChanges,
} from "./theme_website_identification_util";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
/**
 * Plugin handling website branding modifications (name, logo, favicon).
 */
export class WebsiteBrandingPlugin extends Plugin {
    static id = "websiteBrandingPlugin";
    static dependencies = ["media"];
    faviconUrl = signal(null);

    static shared = [
        "getWebsiteName",
        "hasLogoLocationChange",
        "isLogoVisible",
        "faviconUrl",
        "updateName",
        "updateFavicon",
        "removeFavicon",
        "updateLogo",
        "restoreLogo",
    ];

    resources = {
        builder_actions: {
            SetWebsiteNameAction,
            ReplaceFaviconAction,
            RemoveFaviconAction,
            ReplaceLogoAction,
            RestoreLogoAction,
        },
        on_will_save_handlers: () => this.onWillSave(),
    };

    setup() {
        const website = this.services.website.currentWebsite;
        const websiteId = website.id;

        this.staged = {};
        this.rollback = [];
        this.standardFaviconUrl = websiteId ? `/web/image/website/${websiteId}/favicon` : null;

        this.originalValues = {
            name: website.name || "",
            favicon: null,
        };

        this.currentDisplayedName = this.originalValues.name;
        this.logosState = getInitialLogoState(this.document);
        this.logoObserver = observeLogoChanges(this.document, this.logosState);
        if (websiteId) {
            this.loadInitialFavicon(websiteId);
        }
    }

    // ========================================================================
    // GETTERS
    // ========================================================================

    getWebsiteName() {
        return this.currentDisplayedName;
    }

    hasLogoLocationChange(id) {
        return this.logosState[id].hasChange();
    }

    isLogoVisible(id) {
        return getLogoElements(this.document, [id]).length > 0;
    }

    // ========================================================================
    // ASYNCHRONOUS INITIALIZATION
    // ========================================================================

    /**
     * Fetches and loads the initial favicon URL from the server.
     * @param {number} websiteId - The ID of the current website.
     */
    async loadInitialFavicon(websiteId) {
        const count = await this.services.orm.searchCount("website", [
            ["id", "=", websiteId],
            ["favicon", "!=", false],
        ]);

        if (!("favicon" in this.staged)) {
            if (count > 0) {
                this.updateInitialFaviconState(this.standardFaviconUrl);
            } else {
                this.updateInitialFaviconState(null);
            }
        }
    }

    // ========================================================================
    // SETTERS & ACTIONS
    // ========================================================================

    /**
     * Updates both the plugin's internal state and the signal for the favicon.
     * @param {string|null} url - The new favicon URL.
     */
    updateInitialFaviconState(url) {
        this.originalValues.favicon = url;
        this.faviconUrl.set(`${url}?t=${Date.now()}`);
    }

    updateName(value) {
        if (value === this.originalValues.name) {
            delete this.staged.name;
        } else {
            this.staged.name = value;
        }

        if (value !== this.currentDisplayedName) {
            this.rollback.push(
                ...applyWebsiteName(this.services.title, value, this.currentDisplayedName)
            );
            this.currentDisplayedName = value;
        }
    }

    async updateFavicon() {
        await this.openImageDialog((mediaData) => {
            this.staged.favicon = mediaData;
            this.faviconUrl.set(mediaData.url);
            applyFavicon(mediaData.url);
        });
    }

    removeFavicon() {
        if (this.originalValues.favicon === null) {
            delete this.staged.favicon;
        } else {
            this.staged.favicon = false;
        }
        this.faviconUrl.set(null);
        applyFavicon(null);
    }

    async updateLogo(targets = LOGO_TARGETS_NAME) {
        await this.openImageDialog((mediaData) => {
            const globalUpdate = targets.includes(MAIN_LOGO_TARGET);
            applyLogo(this.document, mediaData.url, targets);
            if (globalUpdate) {
                this.staged.logo = mediaData;
            }
            for (const target of targets) {
                this.logosState[target].hasChange.set(
                    getLogoElements(this.document, [target])[0]?.src !=
                        this.logosState[target].initialUrlValue
                );
            }
        });
    }

    restoreLogo(target) {
        applyLogo(this.document, this.logosState[target].initialUrlValue, [target]);
        if (target == MAIN_LOGO_TARGET) {
            delete this.staged.logo;
        }
        this.logosState[target].hasChange.set(false);
    }

    // ========================================================================
    // HELPERS & PERSISTENCE
    // ========================================================================

    /**
     * Opens the Odoo media dialog configured for images.
     * @param {Function} onSelect - Callback executed when an image is selected.
     */
    async openImageDialog(onSelect) {
        const websiteId = this.services.website.currentWebsite.id;

        await this.dependencies.media.openMediaDialog({
            resModel: "website",
            resId: websiteId,
            onlyImages: true,
            save: (elements) => {
                const mediaElement = Array.isArray(elements) ? elements[0] : elements;
                const attachmentIdString =
                    mediaElement.dataset.attachmentId || mediaElement.dataset.id;

                onSelect({
                    attachmentId: attachmentIdString ? parseInt(attachmentIdString, 10) : null,
                    url: mediaElement.getAttribute("src") || mediaElement.src || null,
                });
            },
        });
    }

    preparePayload() {
        const payload = {};
        if ("name" in this.staged) {
            payload.name = this.staged.name;
        }
        if ("favicon" in this.staged) {
            payload.favicon = this.staged.favicon ? this.staged.favicon.attachmentId : false;
        }
        if ("logo" in this.staged) {
            payload.logo = this.staged.logo?.attachmentId;
        }
        return payload;
    }

    /**
     * Applies the server response to the local state after a successful save.
     * @param {Object} ormResult - The result returned by the ORM call.
     * @param {Object} payload - The payload that was sent.
     */
    applySaveResult(ormResult, payload) {
        const websiteId = this.services.website.currentWebsite.id;

        if ("name" in payload) {
            this.originalValues.name = ormResult.name;
        }
        if ("favicon" in payload) {
            const newFavicon = buildMediaUrl(websiteId, "favicon", ormResult.has_favicon);
            this.updateInitialFaviconState(newFavicon);
        }

        this.services.website.currentWebsite.name = this.originalValues.name;
        this.staged = {};
    }

    /**
     * Handler triggered before saving the website.
     */
    async onWillSave() {
        if (this.rollback.length > 0) {
            this.rollback.reverse().forEach((rollbackFn) => rollbackFn());
            this.rollback = [];
        }
        if (Object.keys(this.staged).length === 0) {
            return;
        }

        const payload = this.preparePayload();
        if (Object.keys(payload).length === 0) {
            return;
        }

        const websiteId = this.services.website.currentWebsite.id;
        const ormResult = await this.services.orm.call("website", "update_branding", [
            [websiteId],
            payload,
        ]);
        this.applySaveResult(ormResult, payload);
    }

    destroy() {
        if (this.logoObserver) {
            this.logoObserver.disconnect();
        }
        super.destroy();
    }
}

export class ThemeWebsiteIdentificationOption extends BaseOptionComponent {
    static template = "website.ThemeWebsiteIdentificationOption";
    static dependencies = ["websiteBrandingPlugin"];

    get logoConfig() {
        return LOGO_OPTION_CONFIG;
    }

    isVisible(id) {
        return this.plugin.isLogoVisible(id);
    }

    hasChange(id) {
        return this.plugin.hasLogoLocationChange(id);
    }

    get plugin() {
        return this.dependencies.websiteBrandingPlugin;
    }

    get faviconUrl() {
        return this.plugin.faviconUrl();
    }
}

registry.category("website-plugins").add(WebsiteBrandingPlugin.id, WebsiteBrandingPlugin);
