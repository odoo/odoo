import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { ICON_SELECTOR } from "@html_editor/utils/dom_info";
import { fonts } from "@html_editor/utils/fonts";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { renderToFragment } from "@web/core/utils/render";
import { SocialMediaLinks } from "./social_media_links";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { SNIPPET_SPECIFIC, TITLE_LAYOUT_SIZE } from "@html_builder/utils/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

/**
 * @typedef { Object } SocialMediaInfo
 * @property { boolean } [recorded] whether the social media is one from the orm
 * @property { string|Markup|LazyTranslatedString } label
 * @property { string } iconClass the icon class to use for the social media
 * @property { RegExp } [extraHostnameRegex] a regex for host names that belongs to this social media, but are not catch by the default mechanism
 */

/** @type { Map<string, SocialMediaInfo> } */
const socialMediaInfo = new Map(
    Object.entries({
        facebook: {
            recorded: true,
            label: _t("Facebook"),
            iconClass: "fa-facebook",
            extraHostnameRegex: /(^|\.)fb\.(com|me)$/,
        },
        twitter: {
            recorded: true,
            label: _t("X"),
            iconClass: "fa-twitter",
            extraHostnameRegex: /(^|\.)x\.com$/,
        },
        linkedin: {
            recorded: true,
            label: _t("LinkedIn"),
            iconClass: "fa-linkedin",
        },
        youtube: {
            recorded: true,
            label: _t("YouTube"),
            iconClass: "fa-youtube-play",
            extraHostnameRegex: /(^|\.)youtu\.be$/,
        },
        instagram: {
            recorded: true,
            label: _t("Instagram"),
            iconClass: "fa-instagram",
            extraHostnameRegex: /(^|\.)instagr\.(am|com)$/,
        },
        github: {
            recorded: true,
            label: _t("GitHub"),
            iconClass: "fa-github",
        },
        tiktok: {
            recorded: true,
            label: _t("TikTok"),
            iconClass: "fa-tiktok",
        },
        discord: {
            recorded: true,
            label: _t("Discord"),
            iconClass: "fa-discord",
        },
        "google-play": {
            label: _t("Google Play"),
            iconClass: "fa-google-play",
            // Without this, the default finds 'google' instead
            extraHostnameRegex: /(^|\.)play\.google\.com$/,
        },
        google: {
            label: _t("Google"),
            iconClass: "fa-google",
        },
        whatsapp: {
            label: _t("Whatsapp"),
            iconClass: "fa-whatsapp",
            extraHostnameRegex: /(^|\.)wa\.me$/,
        },
        pinterest: {
            label: _t("Pinterest"),
            iconClass: "fa-pinterest-p",
        },
        kickstarter: {
            label: _t("Kickstarter"),
            iconClass: "fa-kickstarter",
        },
        strava: {
            label: _t("Strava"),
            iconClass: "fa-strava",
        },
        bluesky: {
            label: _t("Bluesky"),
            iconClass: "fa-bluesky",
            extraHostnameRegex: /(^|\.)bsky\.(app|social)$/,
        },
        threads: {
            label: _t("Threads"),
            iconClass: "fa-threads",
        },
    })
);

const defaultAriaLabel = _t("Other social network");

export class SocialMediaOption extends BaseOptionComponent {
    static template = "website.SocialMediaOption";
    static selector = ".s_share, .s_social_media";
}

class SocialMediaOptionPlugin extends Plugin {
    static id = "socialMediaOptionPlugin";
    static dependencies = ["history"];
    static shared = [
        "newLinkElement",
        "getRecordedSocialMedia",
        "setRecordedSocialMedia",
        "setRecordedSocialMediaAreEdited",
        "getAssociatedSocialMedia",
        "removeSocialMediaClasses",
        "removeIconClasses",
        "getRecordedSocialMediaNames",
        "reorderSocialMediaLink",
    ];
    resources = {
        builder_options: [
            withSequence(TITLE_LAYOUT_SIZE, SocialMediaOption),
            withSequence(SNIPPET_SPECIFIC, SocialMediaLinks),
        ],
        so_content_addition_selector: [".s_share", ".s_social_media"],
        builder_actions: {
            DeleteSocialMediaLinkAction,
            ToggleRecordedSocialMediaLinkAction,
            EditRecordedSocialMediaLinkAction,
            EditSocialMediaLinkAction,
            AddSocialMediaLinkAction,
        },
        normalize_handlers: this.normalize.bind(this),
        save_handlers: this.saveRecordedSocialMedia.bind(this),
        content_not_editable_selectors: [".s_share"],
        content_editable_selectors: [
            ".s_share a > i",
            ".s_share .s_share_title",
            ".s_social_media a > i",
            ".s_social_media .s_social_media_title",
        ],
    };

    /** The social media's name for which there is an entry in the orm */
    async getRecordedSocialMediaNames() {
        await this.fetchRecordedSocialMedia();
        return this.recordedSocialMedia.keys();
    }

    // TODO: a method to give access to the `recordedSocialMedia` for facebook page and instagram page

    setup() {
        this.recordedSocialMedia = new Map();
    }

    getRecordedSocialMedia(key) {
        return this.recordedSocialMedia.get(key);
    }
    setRecordedSocialMedia(key, value) {
        this.recordedSocialMedia.set(key, value);
    }
    setRecordedSocialMediaAreEdited(value) {
        this.recordedSocialMediaAreEdited = value;
    }
    async fetchRecordedSocialMedia() {
        if (this.hasStartedLoadingRecordedSocialMedia) {
            return;
        }
        this.hasStartedLoadingRecordedSocialMedia = true;

        const res = await this.services.orm.read(
            "website",
            [this.services.website.currentWebsite.id],
            [
                ...socialMediaInfo
                    .entries()
                    .filter(([name, info]) => info.recorded)
                    .map(([name, info]) => `social_${name}`),
            ]
        );
        for (const name of socialMediaInfo.keys()) {
            const key = `social_${name}`;
            if (key in res[0]) {
                this.recordedSocialMedia.set(name, res[0][key] || "");
            }
        }
        this.config.onChange({ isPreviewing: false });
    }

    async saveRecordedSocialMedia() {
        if (!this.recordedSocialMediaAreEdited) {
            return;
        }
        await this.services.orm.write(
            "website",
            [this.services.website.currentWebsite.id],
            Object.fromEntries(
                this.recordedSocialMedia.entries().map(([name, value]) => [`social_${name}`, value])
            )
        );

        this.recordedSocialMediaAreEdited = false;
    }

    normalize(root) {
        // Add https:// if needed, to the links from db, and the links from dom
        if (this.recordedSocialMediaAreEdited) {
            for (const [name, value] of this.recordedSocialMedia.entries()) {
                const newValue = this.addHttpsIfNeeded(value);
                if (value !== newValue) {
                    this.recordedSocialMedia.set(name, newValue);
                }
            }
        }
        for (const element of selectElements(root, ".s_social_media > a[href]")) {
            const value = element.attributes.href.value;
            const newHref = this.addHttpsIfNeeded(value);
            if (value !== newHref) {
                element.href = newHref;
            }
        }

        // ensure one '\n' between each element + before and after
        for (const element of selectElements(root, ".s_social_media > *")) {
            if (element.nextSibling?.nodeType === Node.TEXT_NODE) {
                while (element.nextSibling.nextSibling?.nodeType === Node.TEXT_NODE) {
                    element.parentNode.removeChild(element.nextSibling);
                }
                if (element.nextSibling.textContent !== "\n") {
                    element.nextSibling.textContent = "\n";
                }
            } else {
                element.after("\n");
            }
            if (element.previousSibling?.nodeType !== Node.TEXT_NODE) {
                element.before("\n");
            }
        }
    }

    /**
     * @param { HTMLElement } editingElement The element edited
     * @param { HTMLElement } element The element that is moved (a child of `editingElement`)
     * @param { HTMLElement } [elementAfter] The element that should be after the moved element (not present if moved to the end)
     */
    reorderSocialMediaLink({ editingElement, element, elementAfter }) {
        element.remove();
        if (elementAfter) {
            elementAfter.before(element);
        } else {
            editingElement.append(element);
        }
    }

    /**
     * @param { HTMLElement } [other] a link element to clone to use as base (use the template if none)
     * @param { String } [socialMediaName] the name of the social media to use if any
     * @returns { HTMLElement } a new link element
     */
    newLinkElement(other, socialMediaName) {
        const el =
            other?.cloneNode(true) ||
            renderToFragment("website.example_social_media_link").children[0];
        this.removeSocialMediaClasses(el);
        this.removeIconClasses(el);
        el.querySelector(ICON_SELECTOR)?.classList.add(
            socialMediaInfo.get(socialMediaName)?.iconClass || "fa-pencil"
        );
        if (socialMediaName) {
            el.href = `/website/social/${encodeURIComponent(socialMediaName)}`;
            el.classList.add(`s_social_media_${socialMediaName}`);
            el.setAttribute(
                "aria-label",
                socialMediaInfo.get(socialMediaName)?.label || defaultAriaLabel
            );
        } else {
            el.href = "https://www.example.com";
            el.setAttribute("aria-label", "example");
        }
        return el;
    }

    /**
     * Strip an element from the classes associated to social media
     * @param { HTMLElement } el
     */
    removeSocialMediaClasses(el) {
        for (const c of el.classList) {
            if (c.startsWith("s_social_media_")) {
                el.classList.remove(c);
            }
        }
    }
    /**
     * Strip an element from the classes associated to an icon (keeps the size)
     * @param { HTMLElement } el
     */
    removeIconClasses(el) {
        const iconEl = el.querySelector(ICON_SELECTOR);
        if (iconEl) {
            // Remove every fa classes except fa-x sizes.
            for (const c of iconEl.classList) {
                if (/^fa-[^0-9]/.test(c)) {
                    iconEl.classList.remove(c);
                }
            }
        }
    }

    /**
     * @typedef { Object } AssociatedSocialMediaReturn
     * @property { String } [name] the name of the social media
     * @property { SocialMediaInfo } [media] the info about the social media (an entry of `socialMediaInfo`) @see socialMediaInfo
     */
    /**
     * @param { String } link
     * @returns { AssociatedSocialMediaReturn }
     */
    getAssociatedSocialMedia(link) {
        try {
            const url = new URL(this.addHttpsIfNeeded(link));
            if (url.protocol && !url.protocol.startsWith("http")) {
                return {}; // no mailto, etc
            }
            const hostname = url.hostname;
            for (const [name, media] of socialMediaInfo.entries()) {
                if (media.extraHostnameRegex?.test(hostname)) {
                    return { name, media };
                }
            }
            // Retrieve the domain of the given url.
            const name = hostname
                .replace(/\.co\.uk$/, ".co")
                .split(".")
                .slice(-2)[0];
            return { name, media: socialMediaInfo.get(name) };
        } catch {
            return {};
        }
    }

    /**
     * @param { String } link
     * @returns { String } the same link, prefixed with 'https://' if none is set
     */
    addHttpsIfNeeded(link) {
        // We permit every protocol (http:, https:, ftp:, mailto:,...).
        // If none is explicitly specified, we assume it is a https.
        if (link && !/^(([a-zA-Z]+):|\/)/.test(link)) {
            return `https://${link}`;
        } else {
            return link;
        }
    }
}

export class DeleteSocialMediaLinkAction extends BuilderAction {
    static id = "deleteSocialMediaLink";
    apply({ editingElement }) {
        editingElement.remove();
    }
}
export class ToggleRecordedSocialMediaLinkAction extends BuilderAction {
    static id = "toggleRecordedSocialMediaLink";
    static dependencies = ["socialMediaOptionPlugin"];
    isApplied({ editingElement, params: { domPosition } }) {
        return !!domPosition;
    }
    apply({ editingElement, params: { media, elementAfter } }) {
        const el = this.dependencies.socialMediaOptionPlugin.newLinkElement(
            editingElement.querySelector(":scope > a"),
            media
        );
        if (elementAfter) {
            elementAfter.before(el);
        } else {
            editingElement.append(el);
        }
    }
    clean({ editingElement, params: { domPosition } }) {
        editingElement.querySelector(`a:nth-of-type(${domPosition})`).remove();
    }
}
export class EditRecordedSocialMediaLinkAction extends BuilderAction {
    static id = "editRecordedSocialMediaLink";
    static dependencies = ["socialMediaOptionPlugin", "history"];
    getValue({ params: { mainParam } }) {
        return this.dependencies.socialMediaOptionPlugin.getRecordedSocialMedia(mainParam);
    }
    apply({ params: { mainParam }, value }) {
        this.dependencies.socialMediaOptionPlugin.setRecordedSocialMediaAreEdited(true);
        const oldValue =
            this.dependencies.socialMediaOptionPlugin.getRecordedSocialMedia(mainParam);
        this.dependencies.history.applyCustomMutation({
            apply: () =>
                this.dependencies.socialMediaOptionPlugin.setRecordedSocialMedia(mainParam, value),
            revert: () =>
                this.dependencies.socialMediaOptionPlugin.setRecordedSocialMedia(
                    mainParam,
                    oldValue
                ),
        });
    }
}
export class EditSocialMediaLinkAction extends BuilderAction {
    static id = "editSocialMediaLink";
    static dependencies = ["socialMediaOptionPlugin"];
    apply({ editingElement, params: { mainParam }, value }) {
        if (!value) {
            editingElement.remove();
        }
        const info = this.dependencies.socialMediaOptionPlugin.getAssociatedSocialMedia(value);
        const ariaLabel = info.media?.label || info.name || defaultAriaLabel;
        editingElement.setAttribute("aria-label", ariaLabel);

        this.dependencies.socialMediaOptionPlugin.removeSocialMediaClasses(editingElement);
        let iconClass;
        if (info.media) {
            editingElement.classList.add(`s_social_media_${info.name}`);
            iconClass = info.media.iconClass;
        } else if (info.name) {
            fonts.computeFonts();
            iconClass = fonts.fontIcons[0].alias
                .filter((el) => el.replace(/^fa-/, "").includes(info.name))
                .reduce((a, b) => (a.length && a.length <= b.length ? a : b), "");
        }

        if (iconClass) {
            this.dependencies.socialMediaOptionPlugin.removeIconClasses(editingElement);
            editingElement.querySelector(ICON_SELECTOR)?.classList.add(iconClass);
        }
    }
}
export class AddSocialMediaLinkAction extends BuilderAction {
    static id = "addSocialMediaLink";
    static dependencies = ["socialMediaOptionPlugin"];
    apply({ editingElement }) {
        editingElement.append(
            this.dependencies.socialMediaOptionPlugin.newLinkElement(
                editingElement.querySelector(":scope > a")
            )
        );
    }
}

registry.category("website-plugins").add(SocialMediaOptionPlugin.id, SocialMediaOptionPlugin);
