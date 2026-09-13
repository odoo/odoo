/** @odoo-module native */
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import {
    SNIPPET_SPECIFIC,
    TITLE_LAYOUT_SIZE,
} from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { ICON_SELECTOR, iconClasses } from "@html_editor/utils/dom_info";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { fonts } from "@html_editor/utils/fonts";
import { withSequence } from "@html_editor/utils/resource";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { renderToFragment } from "@web/core/utils/render";

import { SocialMediaLinks } from "./social_media_links.js";

const log = makeLogger("website.builder.plugin.social_media_option_plugin");

/**
 * @typedef { Object } SocialMediaOptionShared
 * @property { SocialMediaOptionPlugin['newLinkElement'] } newLinkElement
 * @property { SocialMediaOptionPlugin['getRecordedSocialMedia'] } getRecordedSocialMedia
 * @property { SocialMediaOptionPlugin['setRecordedSocialMedia'] } setRecordedSocialMedia
 * @property { SocialMediaOptionPlugin['setRecordedSocialMediaAreEdited'] } setRecordedSocialMediaAreEdited
 * @property { SocialMediaOptionPlugin['getAssociatedSocialMedia'] } getAssociatedSocialMedia
 * @property { SocialMediaOptionPlugin['removeSocialMediaClasses'] } removeSocialMediaClasses
 * @property { SocialMediaOptionPlugin['removeIconClasses'] } removeIconClasses
 * @property { SocialMediaOptionPlugin['setIconClass'] } setIconClass
 * @property { SocialMediaOptionPlugin['getRecordedSocialMediaNames'] } getRecordedSocialMediaNames
 * @property { SocialMediaOptionPlugin['reorderSocialMediaLink'] } reorderSocialMediaLink
 */

/**
 * @typedef { Object } SocialMediaInfo
 * @property { boolean } [recorded]
 * @property { import("plugins").TranslatedString } label
 * @property { string } iconClass
 * @property { RegExp } [extraHostnameRegex]
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
    }),
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
        "setIconClass",
        "getRecordedSocialMediaNames",
        "reorderSocialMediaLink",
    ];
    /** @type {import("plugins").WebsiteResources} */
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

    async getRecordedSocialMediaNames() {
        await this.fetchRecordedSocialMedia();
        return this.recordedSocialMedia.keys();
    }

    setup() {
        this.recordedSocialMedia = new Map();
        log.lifecycle("SocialMediaOptionPlugin setup");
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
            log.logic("SocialMediaOptionPlugin fetch skipped: already started");
            return;
        }
        this.hasStartedLoadingRecordedSocialMedia = true;

        const endRead = log.perf("SocialMediaOptionPlugin read recorded social media");
        const res = await this.services.orm.read(
            "website",
            [this.services.website.currentWebsite.id],
            [
                ...socialMediaInfo
                    .entries()
                    .filter(([name, info]) => info.recorded)
                    .map(([name, info]) => `social_${name}`),
            ],
        );
        endRead();
        for (const name of socialMediaInfo.keys()) {
            const key = `social_${name}`;
            if (key in res[0]) {
                this.recordedSocialMedia.set(name, res[0][key] || "");
            }
        }
        log.pipeline("SocialMediaOptionPlugin recorded social media loaded", () => ({
            recorded: this.recordedSocialMedia.size,
        }));
        this.config.onChange({ isPreviewing: false });
    }

    async saveRecordedSocialMedia() {
        if (!this.recordedSocialMediaAreEdited) {
            log.logic(
                "SocialMediaOptionPlugin save skipped: recorded links not edited",
            );
            return;
        }
        const endWrite = log.perf(
            "SocialMediaOptionPlugin write recorded social media",
            () => ({
                recorded: this.recordedSocialMedia.size,
            }),
        );
        await this.services.orm.write(
            "website",
            [this.services.website.currentWebsite.id],
            Object.fromEntries(
                this.recordedSocialMedia
                    .entries()
                    .map(([name, value]) => [`social_${name}`, value]),
            ),
        );
        endWrite();

        this.recordedSocialMediaAreEdited = false;
    }

    normalize(root) {
        if (this.recordedSocialMediaAreEdited) {
            for (const [name, value] of this.recordedSocialMedia.entries()) {
                const newValue = this.addHttpsIfNeeded(value);
                if (value !== newValue) {
                    log.logic(
                        "SocialMediaOptionPlugin normalize recorded link: add https",
                        () => ({
                            name,
                        }),
                    );
                    this.recordedSocialMedia.set(name, newValue);
                }
            }
        }
        for (const element of selectElements(root, ".s_social_media > a[href]")) {
            const value = element.attributes.href.value;
            const newHref = this.addHttpsIfNeeded(value);
            if (value !== newHref) {
                log.logic(
                    "SocialMediaOptionPlugin normalize link href: add https",
                    () => ({
                        value,
                    }),
                );
                element.href = newHref;
            }
        }

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
     * @param { HTMLElement } editingElement
     * @param { HTMLElement } element
     * @param { HTMLElement } [elementAfter]
     */
    reorderSocialMediaLink({ editingElement, element, elementAfter }) {
        log.pipeline("SocialMediaOptionPlugin reorderSocialMediaLink", () => ({
            toEnd: !elementAfter,
        }));
        element.remove();
        if (elementAfter) {
            elementAfter.before(element);
        } else {
            editingElement.append(element);
        }
    }

    /**
     * @param { HTMLElement } [other]
     * @param { String } [socialMediaName]
     * @returns { HTMLElement }
     */
    newLinkElement(other, socialMediaName) {
        log.pipeline("SocialMediaOptionPlugin newLinkElement", () => ({
            socialMediaName,
            cloned: !!other,
        }));
        const el =
            other?.cloneNode(true) ||
            renderToFragment("website.example_social_media_link").children[0];
        this.removeSocialMediaClasses(el);
        this.removeIconClasses(el);
        const media = socialMediaInfo.get(socialMediaName);
        this.setIconClass(
            el,
            media?.iconClass || "fa-pencil",
            media ? "fa-brands" : "fa-solid",
        );
        if (socialMediaName) {
            el.href = `/website/social/${encodeURIComponent(socialMediaName)}`;
            el.classList.add(`s_social_media_${socialMediaName}`);
            el.setAttribute(
                "aria-label",
                socialMediaInfo.get(socialMediaName)?.label || defaultAriaLabel,
            );
        } else {
            el.href = "https://www.example.com";
            el.setAttribute("aria-label", "example");
        }
        return el;
    }

    /**
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
     * @param { HTMLElement } el
     */
    removeIconClasses(el) {
        const iconEl = el.querySelector(ICON_SELECTOR);
        if (iconEl) {
            // a copy, not the live list: removing while iterating skips the
            // class that slides into the removed slot. The face class
            // (fa-solid, fa-brands, ...) stays: it is what ICON_SELECTOR
            // matches, and setIconClass replaces it with the right one.
            const glyphs = [...iconEl.classList].filter(
                (c) => /^fa-[^0-9]/.test(c) && !iconClasses.includes(c),
            );
            iconEl.classList.remove(...glyphs);
        }
    }
    /**
     * @param { HTMLElement } el
     * @param { String } iconClass
     * @param { String } [face] the FA7 face the glyph lives in
     */
    setIconClass(el, iconClass, face = "fa-brands") {
        const iconEl = el.querySelector(ICON_SELECTOR);
        if (!iconEl) {
            return;
        }
        iconEl.classList.remove(...iconClasses);
        iconEl.classList.add(face, iconClass);
    }

    /**
     * @typedef { Object } AssociatedSocialMediaReturn
     * @property { String } [name]
     * @property { SocialMediaInfo } [media]
     */
    /**
     * @param { String } link
     * @returns { AssociatedSocialMediaReturn }
     */
    getAssociatedSocialMedia(link) {
        try {
            const url = new URL(this.addHttpsIfNeeded(link));
            if (url.protocol && !url.protocol.startsWith("http")) {
                log.logic("SocialMediaOptionPlugin link not http", () => ({
                    protocol: url.protocol,
                }));
                return {};
            }
            const hostname = url.hostname;
            for (const [name, media] of socialMediaInfo.entries()) {
                if (media.extraHostnameRegex?.test(hostname)) {
                    return { name, media };
                }
            }
            const name = hostname
                .replace(/\.co\.uk$/, ".co")
                .split(".")
                .slice(-2)[0];
            return { name, media: socialMediaInfo.get(name) };
        } catch {
            log.logic("SocialMediaOptionPlugin link is not a valid url", () => ({
                link,
            }));
            return {};
        }
    }

    /**
     * @param { String } link
     * @returns { String }
     */
    addHttpsIfNeeded(link) {
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
        log.pipeline("DeleteSocialMediaLinkAction apply");
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
        log.pipeline("ToggleRecordedSocialMediaLinkAction apply", () => ({ media }));
        const el = this.dependencies.socialMediaOptionPlugin.newLinkElement(
            editingElement.querySelector(":scope > a"),
            media,
        );
        if (elementAfter) {
            elementAfter.before(el);
        } else {
            editingElement.append(el);
        }
    }
    clean({ editingElement, params: { domPosition } }) {
        log.pipeline("ToggleRecordedSocialMediaLinkAction clean", () => ({
            domPosition,
        }));
        editingElement.querySelector(`a:nth-of-type(${domPosition})`).remove();
    }
}
export class EditRecordedSocialMediaLinkAction extends BuilderAction {
    static id = "editRecordedSocialMediaLink";
    static dependencies = ["socialMediaOptionPlugin", "history"];
    getValue({ params: { mainParam } }) {
        return this.dependencies.socialMediaOptionPlugin.getRecordedSocialMedia(
            mainParam,
        );
    }
    apply({ params: { mainParam }, value }) {
        log.pipeline("EditRecordedSocialMediaLinkAction apply", () => ({ mainParam }));
        this.dependencies.socialMediaOptionPlugin.setRecordedSocialMediaAreEdited(true);
        const oldValue =
            this.dependencies.socialMediaOptionPlugin.getRecordedSocialMedia(mainParam);
        this.dependencies.history.applyCustomMutation({
            apply: () =>
                this.dependencies.socialMediaOptionPlugin.setRecordedSocialMedia(
                    mainParam,
                    value,
                ),
            revert: () =>
                this.dependencies.socialMediaOptionPlugin.setRecordedSocialMedia(
                    mainParam,
                    oldValue,
                ),
        });
    }
}
export class EditSocialMediaLinkAction extends BuilderAction {
    static id = "editSocialMediaLink";
    static dependencies = ["socialMediaOptionPlugin"];
    apply({ editingElement, params: { mainParam }, value }) {
        if (!value) {
            log.logic("EditSocialMediaLinkAction empty link: remove it");
            editingElement.remove();
            return;
        }
        const info =
            this.dependencies.socialMediaOptionPlugin.getAssociatedSocialMedia(value);
        log.logic("EditSocialMediaLinkAction apply", () => ({
            name: info.name,
            known: !!info.media,
        }));
        const ariaLabel = info.media?.label || info.name || defaultAriaLabel;
        editingElement.setAttribute("aria-label", ariaLabel);

        this.dependencies.socialMediaOptionPlugin.removeSocialMediaClasses(
            editingElement,
        );
        let iconClass;
        let face = "fa-brands";
        if (info.media) {
            editingElement.classList.add(`s_social_media_${info.name}`);
            iconClass = info.media.iconClass;
        } else if (info.name) {
            const endFonts = log.perf("EditSocialMediaLinkAction computeFonts");
            iconClass = fonts
                .iconNames()
                .filter((el) => el.replace(/^fa-/, "").includes(info.name))
                .reduce((a, b) => (a.length && a.length <= b.length ? a : b), "");
            face = fonts.faceOf(iconClass) || "fa-solid";
            endFonts();
        }

        if (iconClass) {
            this.dependencies.socialMediaOptionPlugin.removeIconClasses(editingElement);
            this.dependencies.socialMediaOptionPlugin.setIconClass(
                editingElement,
                iconClass,
                face,
            );
        }
    }
}
export class AddSocialMediaLinkAction extends BuilderAction {
    static id = "addSocialMediaLink";
    static dependencies = ["socialMediaOptionPlugin"];
    apply({ editingElement }) {
        log.pipeline("AddSocialMediaLinkAction apply");
        editingElement.append(
            this.dependencies.socialMediaOptionPlugin.newLinkElement(
                editingElement.querySelector(":scope > a"),
            ),
        );
    }
}

registry
    .category("website-plugins")
    .add(SocialMediaOptionPlugin.id, SocialMediaOptionPlugin);
