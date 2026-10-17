import {
    onMounted,
    onWillDestroy,
    onWillUnmount,
    Plugin,
    signal,
    useListener,
    usePlugin,
} from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { LocalizationPlugin } from "@web/core/l10n/localization_plugin";
import { services } from "@web/core/services";
import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";
import { session } from "@web/session";
import { siphash } from "./siphash";
import { isTranslationModeEnabled, parseTranslatedText } from "./translation.patch";

/**
 * @typedef {import("./translation.patch").ContextualizedTranslation} ContextualizedTranslation
 *
 * @typedef {[position: string, translations: ContextualizedTranslation[]]} PositionTranslations
 *
 * @typedef {ContextualizedTranslation & {
 *  link: string;
 *  targets: [HTMLElement, string][];
 * }} TargetedTranslation
 */

function getLang() {
    if (!urlParams.lang) {
        const code = localization.code;
        if (code === "en_US") {
            urlParams.lang = "en";
        } else {
            urlParams.lang = WEBLATE_LANG_MAPPING[code] || code;
        }
    }
    return urlParams.lang;
}

/**
 * @param {CSSStyleDeclaration} style
 * @param {string} property
 */
function getPxValue(style, property) {
    return Number(style.getPropertyValue(property).replaceAll(/[^\d.]+/g, "")) || 0;
}

/**
 * @param {string} source
 * @param {string} context
 */
function getTranslationLink(source, context) {
    const lang = getLang();
    const version = getVersion();
    if (!termHashes.has(source)) {
        termHashes.set(source, siphash(WEBLATE_SIPHASH_KEY, source));
    }
    const checksum = termHashes.get(source);
    return `${BASE_TRANSLATE_URL}${version}/${context}/${lang}/?checksum=${checksum}`;
}

function getVersion() {
    if (!urlParams.version) {
        const versionInfo = session.server_version_info;
        urlParams.version = String(versionInfo[0]);
        if (versionInfo[1]) {
            const majorVersion = urlParams.version.split(/[~-]/g).at(-1);
            urlParams.version = `s${majorVersion}-${versionInfo[1]}`;
        }
    }
    return urlParams.version;
}

/**
 * @param {CSSStyleDeclaration} style
 * @param {string} property
 * @param {number} value
 */
function setPxValue(style, property, value) {
    style.setProperty(property, `${value}px`);
}

/**
 * @param {HTMLElement} target
 * @param {HTMLDivElement} pointer
 */
function updateTranslationPointer(target, pointer) {
    const rect = target.getBoundingClientRect();
    if (
        !rect.width ||
        !rect.height ||
        rect.x + rect.width < 0 ||
        rect.x > window.innerWidth ||
        rect.y + rect.height < 0 ||
        rect.y > window.innerHeight
    ) {
        pointer.remove();
        return;
    }

    const style = getComputedStyle(target);
    const xBorderWidth =
        getPxValue(style, "border-left-width") && getPxValue(style, "border-right-width");
    const yBorderWidth =
        getPxValue(style, "border-top-width") && getPxValue(style, "border-bottom-width");

    const width = Math.max(rect.width, POINTER_MIN_SIZE);
    const wDiff = rect.width < POINTER_MIN_SIZE ? width - rect.width : 0;
    const wMargin = xBorderWidth || rect.width < POINTER_MIN_SIZE ? 0 : POINTER_MARGIN;
    setPxValue(pointer.style, "--_x", rect.x - wDiff / 2 - wMargin);
    setPxValue(pointer.style, "--_w", width + wMargin * 2);

    const height = Math.max(rect.height, POINTER_MIN_SIZE);
    const hDiff = rect.height < POINTER_MIN_SIZE ? height - rect.height : 0;
    const hMargin = yBorderWidth || rect.height < POINTER_MIN_SIZE ? 0 : POINTER_MARGIN;
    setPxValue(pointer.style, "--_y", rect.y - hDiff / 2 - hMargin);
    setPxValue(pointer.style, "--_h", height + hMargin * 2);

    if (!pointer.isConnected) {
        target.ownerDocument.body.appendChild(pointer);
    }
}

class TranslationScanner {
    /** @type {Set<HTMLIFrameElement>} */
    addedIframes = new Set();
    /**
     * @private
     * @type {Map<Element, PositionTranslations[]>}
     */
    elementTranslations = new Map();

    /**
     * @param {Iterable<Node>} nodes
     * @param {boolean} [highlightsEnabled]
     */
    constructor(nodes, highlightsEnabled) {
        this.highlightsEnabled = highlightsEnabled;
        for (const node of nodes) {
            this._translateNode(node);
        }
    }

    getGroupedTranslations() {
        /** @type {Record<string, TargetedTranslation>} */
        const translationsBySources = {};
        for (const [el, translations] of this.elementTranslations) {
            for (const [position, positionTranslations] of translations) {
                for (const translation of positionTranslations) {
                    translationsBySources[translation.source] ||= {
                        targets: [],
                        link: getTranslationLink(translation.source, translation.context),
                        ...translation,
                    };
                    translationsBySources[translation.source].targets.push([el, position]);
                }
            }
        }
        return translationsBySources;
    }

    /**
     * @private
     * @param {Node} node
     * @param {PositionTranslations} positionTranslations
     */
    _addNodeTranslations(node, positionTranslations) {
        if (!this.highlightsEnabled) {
            return;
        }
        const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
        if (!el) {
            return;
        }
        /** @type {PositionTranslations[]} */
        const info = [];
        for (const [root, rootTranslations] of this.elementTranslations) {
            if (root === el || root.contains(el)) {
                // Element *is contained* within an existing element:
                // -> return the parent info
                rootTranslations.push(...info, positionTranslations);
                return;
            }
            if (el.contains(root)) {
                // Element *contains* an existing element:
                // -> replace that element with the given one and retrieve the existing
                //  info
                this.elementTranslations.delete(root);
                info.push(...rootTranslations);
            }
        }
        info.push(positionTranslations);

        this.elementTranslations.set(el, info);
    }

    /**
     * @private
     * @param {Node} node
     * @param {Attr} attribute
     */
    _translateAttribute(node, attribute) {
        const [value, translations] = parseTranslatedText(attribute.value);
        if (!translations.length) {
            return;
        }

        attribute.value = value;

        this._addNodeTranslations(node, [attribute.name, translations]);
    }

    /**
     * @private
     * @param {HTMLCanvasElement} canvas
     * @param {string} text
     */
    _translateCanvasText(canvas, text) {
        const [value, translations] = parseTranslatedText(text);
        if (!translations.length) {
            return text;
        }

        this._addNodeTranslations(canvas, ["canvas", translations]);

        return value;
    }

    /**
     * @private
     * @param {Node} node
     */
    _translateNode(node) {
        switch (node.nodeType) {
            case Node.ELEMENT_NODE: {
                if (node.closest(IGNORE_SELECTOR)) {
                    return;
                }
                if (node.nodeName === "IFRAME") {
                    this.addedIframes.add(node);
                } else if (node.nodeName === "TITLE") {
                    this._translateProperty(node, "textContent", false);
                    return;
                }
                break;
            }
            case Node.TEXT_NODE: {
                const parent = node.parentElement;
                if (parent) {
                    this._translateProperty(node, "textContent");
                }
                return;
            }
            default: {
                return;
            }
        }

        // Scan children first to replace translated string on the deepest possible
        // level
        for (const childNode of node.childNodes) {
            this._translateNode(childNode);
        }

        // Replace and highlight element translated attributes
        for (const attribute of node.attributes) {
            this._translateAttribute(node, attribute);
        }

        // Replace and highlight translated properties
        for (const propertyName in TRANSLATABLE_PROPERTY_LABELS) {
            this._translateProperty(node, propertyName);
        }
    }

    /**
     * @private
     * @param {Node} node
     * @param {string} property
     */
    _translateProperty(node, property) {
        const rawValue = node[property];
        if (typeof rawValue !== "string" || !rawValue) {
            return;
        }

        const [value, translations] = parseTranslatedText(rawValue);
        if (!translations.length) {
            return;
        }

        node[property] = value;

        this._addNodeTranslations(node, [property, translations]);
    }
}

const CAPTURE = { capture: true };
const IGNORE_SELECTOR = [`[data-translation-highlight]`].join(",");
/**
 * !TODO: replace by a parser... JS does not support (?R) recursion in regexes so this is not possible
 * Translate URL is constructed based on the following pattern:
 *
 * <ORIGIN>/translate/odoo-<VERSION_NUMBER>/<LANGUAGE>/?checksum=<TERM_HASH>
 *
 * Where:
 * - ORIGIN = translate.odoo.com
 * - VERSION_NUMBER = current stable version
 * - LANGUAGE = language code ("en", "fr", etc.)
 * - TERM_HASH = SipHash 2-4 representation of the given term, using {@link WEBLATE_SIPHASH_KEY}
 */
const BASE_TRANSLATE_URL = "translate/odoo-";
/**
 * Hard-coded hash key used to generate SipHash 2-4 hexadecimal hash reprenstation
 * of translated terms.
 *
 * This has been extracted directly from the official Weblate repository:
 * @see https://github.com/WeblateOrg/weblate/blob/main/weblate/utils/hash.py#L23
 */
const WEBLATE_SIPHASH_KEY = "Weblate Sip Hash";
const WEBLATE_LANG_MAPPING = {
    ar_001: "ar",
    ku: "ckb",
    "sr@latin": "sr_Latn",
    nb: "nb_NO",
    tl: "fil",
};
const POINTER_MARGIN = 5;
const POINTER_MIN_SIZE = 32;

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

/** @type {Map<string, string>} */
const termHashes = new Map();

export class TranslationModePlugin extends Plugin {
    localization = usePlugin(LocalizationPlugin);

    /** @type {import("@odoo/owl").Signal<TargetedTranslation[]>} */
    currentTranslations = signal([]);

    highlightsEnabled = this.localization.localization.code !== "en_US";
    /** @type {Set<Node>} */
    observedNodes = new Set();
    observer = new MutationObserver(this._onMutation.bind(this));
    /** @type {Map<HTMLElement, HTMLDivElement>} */
    translationPointers = new Map();

    /**
     * @private
     * @type {TranslationModePlugin["_onKeyDown"]}
     */
    _boundOnKeyDown = this._onKeyDown.bind(this);
    /**
     * @private
     * @type {TranslationModePlugin["_onPointerDown"]}
     */
    _boundOnPointerDown = this._onPointerDown.bind(this);
    /**
     * @private
     * @type {TranslationModePlugin["_onWindowScroll"]}
     */
    _debouncedOnWindowScroll = debounce(this._onWindowScroll.bind(this), "animationFrame");

    // Lifecycle

    setup() {
        if (this.highlightsEnabled) {
            console.debug(`Interactive translation mode is active with translation highlighting.`);
        } else {
            const { code } = this.localization.localization;
            console.log(
                `Interactive translation mode is active, but translation highlighting has` +
                    ` been disabled for language "${code}".`
            );
        }

        for (const title of document.head.getElementsByTagName("title")) {
            this.addObservedNode(title);
        }
        this.addObservedNode(document.body, true);

        // Initial scan
        const scanner = new TranslationScanner([document.body], this.highlightsEnabled);
        for (const iframe of scanner.addedIframes) {
            this.addObservedNode(iframe);
        }
        this._registerTranslations(scanner.getGroupedTranslations());

        // Start observing mutations immediately
        this._observe();

        // Observe canvas text rendering as well
        const unpatchCanvas = patch(CanvasRenderingContext2D.prototype, {
            fillText(text, ...args) {
                return super.fillText(scanner._translateCanvasText(this.canvas, text), ...args);
            },
            strokeText(text, ...args) {
                return super.strokeText(scanner._translateCanvasText(this.canvas, text), ...args);
            },
        });

        if (isTranslationModeEnabled()) {
            useListener(window, "scroll", this._debouncedOnWindowScroll, CAPTURE);
        }

        onWillDestroy(() => {
            this._disconnect();
            unpatchCanvas();

            for (const node of this.observedNodes) {
                const target = node.nodeName === "IFRAME" ? node.contentDocument?.body : node;
                target?.removeEventListener("keydown", this._boundOnKeyDown, CAPTURE);
                target?.removeEventListener("pointerdown", this._boundOnPointerDown, CAPTURE);
            }
            this.observedNodes.clear();

            this._debouncedOnWindowScroll.cancel();

            this._clearTranslationPointers();
        });
    }

    // Public

    /**
     * @param {Node} node
     * @param {boolean} [options]
     */
    addObservedNode(node, withListeners) {
        if (this.observedNodes.has(node)) {
            return;
        }
        this.observedNodes.add(node);
        if (withListeners) {
            node.addEventListener("keydown", this._boundOnKeyDown, CAPTURE);
            node.addEventListener("pointerdown", this._boundOnPointerDown, CAPTURE);
        }
    }

    /**
     * @param {TargetedTranslation} translation
     * @param {boolean} keepHighlighted
     */
    highlightTranslation(translation, keepHighlighted) {
        this._handleMutations(this._disconnect());

        if (!keepHighlighted) {
            this._clearTranslationPointers();
        }
        for (const [el] of translation.targets) {
            this._createTranslationPointer(el, translation.isTranslated);
        }

        this._observe();
    }

    useBodyClass(className) {
        onMounted(() => {
            this._handleMutations(this._disconnect());

            document.body.classList.add(className);

            this._observe();
        });
        onWillUnmount(() => {
            this._handleMutations(this._disconnect());

            document.body.classList.remove(className);

            this._observe();
        });
    }

    // Private

    /**
     * @private
     */
    _clearTranslationPointers() {
        for (const pointer of this.translationPointers.values()) {
            pointer.remove();
        }
        this.translationPointers.clear();
    }

    /**
     * @private
     * @param {HTMLElement} target
     * @param {boolean} isTranslated
     */
    _createTranslationPointer(target, isTranslated) {
        if (this.translationPointers.has(target)) {
            return;
        }

        const rgbColor = isTranslated ? "success" : "danger";
        const pointer = document.createElement("div");
        pointer.classList.add("o-translation-pointer");
        pointer.style.setProperty("--_rgb", `var(--${rgbColor}-rgb)`);

        this.translationPointers.set(target, pointer);

        updateTranslationPointer(target, pointer);
    }

    /**
     * @private
     */
    _disconnect() {
        const remainingMutations = this.observer.takeRecords();
        this.observer.disconnect();

        return remainingMutations;
    }

    /**
     * @private
     * @param {MutationRecord[]} mutations
     */
    _handleMutations(mutations) {
        if (!mutations.length) {
            return;
        }
        /**
         * Use a set to eliminate:
         *  - duplicate nodes;
         *  - children of nodes already contained in the set.
         * @type {Set<Node>}
         */
        const targets = new Set();
        for (const mutation of mutations) {
            if (!mutation.target) {
                continue;
            }
            let assigned = false;
            for (const otherTarget of targets) {
                if (mutation.target.contains(otherTarget)) {
                    targets.delete(otherTarget);
                    break;
                } else if (otherTarget.contains(mutation.target)) {
                    assigned = true;
                    break;
                }
            }
            if (!assigned) {
                targets.add(mutation.target);
            }
        }

        const scanner = new TranslationScanner(targets, this.highlightsEnabled);
        for (const iframe of scanner.addedIframes) {
            this.addObservedNode(iframe);
        }
        this._registerTranslations(scanner.getGroupedTranslations());
    }

    /**
     * @private
     */
    _observe() {
        for (let node of this.observedNodes) {
            if (!node.isConnected) {
                this.observedNodes.delete(node);
                continue;
            }
            if (node.nodeName === "IFRAME") {
                const document = node.contentDocument;
                if (document?.body?.isConnected) {
                    node = document.body;

                    // Remove existing event listeners (if any)
                    node.removeEventListener("keydown", this._boundOnKeyDown, CAPTURE);
                    node.removeEventListener("pointerdown", this._boundOnPointerDown, CAPTURE);

                    // Add them back
                    node.addEventListener("keydown", this._boundOnKeyDown, CAPTURE);
                    node.addEventListener("pointerdown", this._boundOnPointerDown, CAPTURE);
                } else {
                    this.observedNodes.delete(node);
                    continue;
                }
            }
            this.observer.observe(node, {
                attributes: true,
                characterData: true,
                childList: true,
                subtree: true,
            });
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeyDown(ev) {
        if (ev.key === "Escape") {
            this._clearTranslationPointers();
        }
    }

    /**
     * @private
     * @type {MutationCallback}
     */
    _onMutation(mutations) {
        const startTime = performance.now();

        mutations.push(...this._disconnect());
        this._handleMutations(mutations);
        this._observe();

        console.debug(
            "[TRANSLATION SERVICE] scan took",
            Number((performance.now() - startTime).toFixed(3)),
            "ms"
        );
    }

    /**
     * @private
     * @param {PointerEvent} ev
     */
    _onPointerDown(ev) {
        if (!ev.ctrlKey) {
            this._clearTranslationPointers();
        }
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onWindowScroll(ev) {
        if (
            ev.target.nodeType === Node.ELEMENT_NODE &&
            ev.target.closest(".o-translate-side-panel")
        ) {
            return;
        }
        for (const [target, pointer] of this.translationPointers) {
            updateTranslationPointer(target, pointer);
        }
    }

    /**
     * @private
     * @param {Record<string, TargetedTranslation>} newTranslations
     */
    _registerTranslations(newTranslations) {
        /** @type {Map<string, TargetedTranslation>} */
        const nextTranslations = new Map();
        for (const translation of this.currentTranslations()) {
            const targets = translation.targets.filter(([el]) => el.isConnected);
            nextTranslations.set(translation.source, { ...translation, targets });
        }
        for (const translation of Object.values(newTranslations)) {
            const existingTranslation = nextTranslations.get(translation.source);
            if (existingTranslation) {
                existingTranslation.targets.push(...translation.targets);
            } else {
                nextTranslations.set(translation.source, translation);
            }
        }
        const translations = [];
        for (const translation of nextTranslations.values()) {
            if (translation.targets.length) {
                translations.push(translation);
            }
        }
        this.currentTranslations.set(translations);
    }
}

export const urlParams = {
    lang: "",
    version: "",
};

// Plugin should only be registered at top level, as it will look for translations
// in iframes.
if (window === window.top) {
    services.add(TranslationModePlugin);
}
