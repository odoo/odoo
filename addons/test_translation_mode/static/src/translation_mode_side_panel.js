import { useRef, useState } from "@web/owl2/utils";
import { Component, onWillDestroy } from "@odoo/owl";
import { normalizedMatch } from "@web/core/l10n/utils";
import { useService } from "@web/core/utils/hooks";
import { isVisible } from "@web/core/utils/ui";

/**
 * @typedef {import("./translation_mode_service").TargetedTranslation} TargetedTranslation
 */

/**
 * @param {TargetedTranslation} translation
 */
function isMissingSource(translation) {
    return !translation.source || RE_MISSING_SOURCE.test(translation.source);
}

/**
 * @param {TargetedTranslation} translation
 */
function isMissingTranslation(translation) {
    return !translation.isTranslated;
}

/**
 * @param {string} filter
 * @param {TargetedTranslation} translation
 */
function matchFilter(filter, translation) {
    if (!filter) {
        return true;
    }
    if (!isMissingSource(translation) && normalizedMatch(translation.source, filter).match) {
        return true;
    }
    if (
        !isMissingTranslation(translation) &&
        normalizedMatch(translation.translation, filter).match
    ) {
        return true;
    }
    return false;
}

const DEFAULT_LANG_DISPLAY_NAME = "English (US)";
const DEFAULT_LANG_FLAG_URL = "/base/static/img/country_flags/us.png";

const RE_MISSING_SOURCE = /^MISSING_SOURCE_\d{8}$/;

export class TranslationModeSidePanel extends Component {
    static props = {
        translations: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    context: String,
                    link: String,
                    source: String,
                    targets: {
                        type: Array,
                        element: {
                            type: Array,
                            element: {
                                validate: (el) =>
                                    typeof el === "string" || el?.nodeType === Node.ELEMENT_NODE,
                            },
                        },
                    },
                    isTranslated: Boolean,
                    translation: String,
                },
            },
        },
    };
    static template = "test_translation_mode.TranslationModeSidePanel";

    isMissingSource = isMissingSource;
    isMissingTranslation = isMissingTranslation;

    defaultLangDisplayName = DEFAULT_LANG_DISPLAY_NAME;
    defaultLangFlagUrl = DEFAULT_LANG_FLAG_URL;
    /**
     * Internal set recomputed on each render keeping track of which translations
     * are only bound to hidden targets.
     * @type {Set<TargetedTranslation>}
     */
    hiddenTranslations = new Set();

    setup() {
        this.actionService = useService("action");
        this.localization = useService("localization");
        this.orm = useService("orm");
        this.translationMode = useService("translation_mode");

        this.translationMode.useBodyClass("o-body-with-translate-side-panel");

        this.rootRef = useRef("root");
        this.collapsedCategories = useState(new Set());
        this.state = useState({
            filter: "",
            currentLangDisplayName: this.localization.code,
            currentLangFlagUrl: "",
            translationUrl: null,
        });

        this.onPointerDown = this.onPointerDown.bind(this);
        window.addEventListener("pointerdown", this.onPointerDown, { capture: true });
        onWillDestroy(() =>
            window.removeEventListener("pointerdown", this.onPointerDown, { capture: true })
        );

        this.orm
            .call("ir.config_parameter", "get_str", ["test_translation_mode.translation_url"])
            .then((translationUrl) => {
                this.state.translationUrl = translationUrl || "";
                if (!this.state.translationUrl.endsWith("/")) {
                    this.state.translationUrl += "/";
                }
            });
        this.orm
            .webSearchRead("res.lang", [["code", "=", this.localization.code]], {
                specification: {
                    display_name: {},
                    flag_image_url: {},
                },
            })
            .then(({ records }) => {
                this.state.currentLangDisplayName = records[0].display_name;
                this.state.currentLangFlagUrl = records[0].flag_image_url;
            });
    }

    /**
     * @param {[target: HTMLElement, position: string]} targets
     */
    formatTarget(targets) {
        const resultSet = new Set();
        for (const [, position] of targets) {
            if (TRANSLATABLE_ATTRIBUTE_LABELS[position]) {
                resultSet.add(TRANSLATABLE_ATTRIBUTE_LABELS[position]);
            } else if (TRANSLATABLE_PROPERTY_LABELS[position]) {
                resultSet.add(TRANSLATABLE_PROPERTY_LABELS[position]);
            } else {
                resultSet.add(position);
            }
        }
        return [...resultSet].join(" / ");
    }

    getTranslationCategories() {
        /** @type {TargetedTranslation[]} */
        const translated = [];
        /** @type {TargetedTranslation[]} */
        const untranslated = [];
        this.hiddenTranslations.clear();
        const filter = this.state.filter.toLowerCase().trim();
        for (const translation of this.props.translations) {
            if (!matchFilter(filter, translation)) {
                continue;
            }
            if (!translation.targets.some(([el]) => isVisible(el, { css: true, viewPort: true }))) {
                this.hiddenTranslations.add(translation);
            }
            if (translation.isTranslated) {
                translated.push(translation);
            } else {
                untranslated.push(translation);
            }
        }
        const categories = [];
        if (untranslated.length) {
            categories.push({
                id: "untranslated",
                label: `Untranslated`,
                translations: untranslated,
            });
        }
        if (translated.length) {
            categories.push({
                id: "translated",
                label: `Translated`,
                translations: translated,
            });
        }
        return categories;
    }

    /**
     * @param {TargetedTranslation} translation
     * @param {PointerEvent} ev
     */
    onCardClick(translation, ev) {
        this.translationMode.highlightTranslation(translation, ev.ctrlKey);
    }

    /**
     * @param {Event} ev
     */
    onPointerDown(ev) {
        if (ev.composedPath().includes(this.rootRef.el)) {
            // Stop all pointer events from within the side panel.
            // This is done to avoid dropdowns closing when focusing translations
            ev.stopImmediatePropagation();
            ev.stopPropagation();
        }
    }

    openSettings() {
        this.actionService.doAction("test_translation_mode.translation_mode_settings_action");
    }

    toggleCategory(category) {
        if (this.collapsedCategories.has(category.id)) {
            this.collapsedCategories.delete(category.id);
        } else {
            this.collapsedCategories.add(category.id);
        }
    }
}

export const TRANSLATABLE_ATTRIBUTE_LABELS = {
    "aria-label": `Aria label`,
    "aria-placeholder": `Aria placeholder`,
    "aria-roledescription": `Aria role description`,
    "aria-valuetext": `Aria value text`,
    "data-tooltip-info": `Tooltip info data`,
    "data-tooltip": `Tooltip data`,
    "o-we-hint-text": `Web editor text hint`,
    alt: `Alternate text`,
    label: `Label`,
    name: `Name`,
    placeholder: `Placeholder`,
    searchabletext: `Searchable text`,
    title: `Title`,
};
export const TRANSLATABLE_PROPERTY_LABELS = {
    textContent: `Text`,
    value: `Value`,
};
