import {
    Component,
    computed,
    onWillDestroy,
    Plugin,
    signal,
    useListener,
    usePlugin,
} from "@odoo/owl";
import { LocalizationPlugin } from "@web/core/l10n/localization_plugin";
import { normalizedMatch } from "@web/core/l10n/utils";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { isVisible } from "@web/core/utils/ui";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { isTranslationModeEnabled } from "./translation.patch";
import {
    TRANSLATABLE_ATTRIBUTE_LABELS,
    TRANSLATABLE_PROPERTY_LABELS,
    TranslationModePlugin,
} from "./translation_mode_plugin";

/**
 * @typedef {import("./translation_mode_plugin").TargetedTranslation} TargetedTranslation
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
    static template = "test_translation_mode.TranslationModeSidePanel";

    action = usePlugin(ActionPlugin);
    localization = usePlugin(LocalizationPlugin);
    orm = usePlugin(ORM);
    translationMode = usePlugin(TranslationModePlugin);

    collapsedCategories = signal.Set(new Set());
    currentLangDisplayName = signal(this.localization.localization.code);
    currentLangFlagUrl = signal("");
    filter = signal("");
    rootRef = signal.ref();
    /** @type {import("@odoo/owl").Signal<string | null>} */
    translationUrl = signal(null);

    filteredTranslations = computed(() => {
        const filter = this.filter().toLowerCase().trim();
        return this.translationMode
            .currentTranslations()
            .filter((translation) => matchFilter(filter, translation));
    });
    hiddenTranslations = computed(() => {
        /** @type {Set<TargetedTranslation>} */
        const hiddenTranslations = new Set();
        for (const translation of this.filteredTranslations()) {
            if (!translation.targets.some(([el]) => isVisible(el, { css: true, viewPort: true }))) {
                hiddenTranslations.add(translation);
            }
        }
        return hiddenTranslations;
    });
    translationCategories = computed(() => {
        /** @type {TargetedTranslation[]} */
        const translated = [];
        /** @type {TargetedTranslation[]} */
        const untranslated = [];
        for (const translation of this.filteredTranslations()) {
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
    });

    defaultLangDisplayName = DEFAULT_LANG_DISPLAY_NAME;
    defaultLangFlagUrl = DEFAULT_LANG_FLAG_URL;
    isMissingSource = isMissingSource;
    isMissingTranslation = isMissingTranslation;

    setup() {
        this.translationMode.useBodyClass("o-body-with-translate-side-panel");

        useListener(window, "pointerdown", this.onPointerDown.bind(this), { capture: true });

        this.orm
            .call("ir.config_parameter", "get_str", ["test_translation_mode.translation_url"])
            .then((translationUrl) => {
                translationUrl ||= "";
                if (!translationUrl.endsWith("/")) {
                    translationUrl += "/";
                }
                this.translationUrl.set(translationUrl);
            });
        this.orm
            .webSearchRead("res.lang", [["code", "=", this.localization.localization.code]], {
                specification: {
                    display_name: {},
                    flag_image_url: {},
                },
            })
            .then(({ records }) => {
                this.currentLangDisplayName.set(records[0].display_name);
                this.currentLangFlagUrl.set(records[0].flag_image_url);
            });
    }

    /**
     * @param {[target: HTMLElement, position: string][]} targets
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
        if (ev.composedPath().includes(this.rootRef())) {
            // Stop all pointer events from within the side panel.
            // This is done to avoid dropdowns closing when focusing translations
            ev.stopImmediatePropagation();
            ev.stopPropagation();
        }
    }

    openSettings() {
        this.action.doAction("test_translation_mode.translation_mode_settings_action");
    }

    /**
     * @param {{ id: string }} category
     */
    toggleCategory(category) {
        const collapsedCategories = this.collapsedCategories();
        if (collapsedCategories.has(category.id)) {
            collapsedCategories.delete(category.id);
        } else {
            collapsedCategories.add(category.id);
        }
    }
}

/**
 * Displays the side panel listing the translations of the current page when the
 * interactive translation mode is enabled.
 */
export class TranslationModeSidePanelPlugin extends Plugin {
    setup() {
        if (!isTranslationModeEnabled()) {
            return;
        }
        const mainComponents = registry.category("main_components");
        mainComponents.add("translation-mode-side-panel", {
            Component: TranslationModeSidePanel,
        });
        onWillDestroy(() => mainComponents.remove("translation-mode-side-panel"));
    }
}

// Same restriction as the translation mode plugin, which looks for translations
// in iframes.
if (window === window.top) {
    services.add(TranslationModeSidePanelPlugin);
}
