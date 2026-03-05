import { onMounted, onWillUnmount, reactive } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";
import { session } from "@web/session";
import { siphash } from "./siphash";
import { isTranslateModeEnabled, parseTranslatedText } from "./translation.patch";
import {
    TRANSLATABLE_PROPERTY_LABELS,
    TranslationModeSidePanel,
} from "./translation_mode_side_panel";

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

function clearTranslationPointers() {
    for (const pointer of translationPointers.values()) {
        pointer.remove();
    }
    translationPointers.clear();
}

/**
 * @param {HTMLElement} target
 * @param {boolean} translated
 */
function createTranslationPointer(target, translated) {
    if (translationPointers.has(target)) {
        return;
    }

    const rgbColor = translated ? "success" : "danger";
    const pointer = document.createElement("div");
    pointer.classList.add("o-translation-pointer");
    pointer.style.setProperty("--_rgb", `var(--${rgbColor}-rgb)`);

    translationPointers.set(target, pointer);

    updateTranslationPointer(target, pointer);
}

function getLangAndVersion() {
    if (!urlParams.lang) {
        const code = localization.code;
        if (code === "en_US") {
            urlParams.lang = "en";
        } else {
            const [lang, cc] = code.split("_");
            if (!isNaN(cc)) {
                urlParams.lang = lang;
            } else {
                urlParams.lang = code in WEBLATE_LANG_MAPPING ? WEBLATE_LANG_MAPPING[code] : code;
            }
        }
    }
    if (!urlParams.version) {
        const versionInfo = session.server_version_info;
        urlParams.version = String(versionInfo[0]);
        if (versionInfo[1]) {
            const majorVersion = urlParams.version.split(/[~-]/g).at(-1);
            urlParams.version = `s${majorVersion}-${versionInfo[1]}`;
        }
    }
    return urlParams;
}

/**
 * @param {CSSStyleDeclaration} style
 * @param {string} property
 */
function getPxValue(style, property) {
    return Number(style.getPropertyValue(property).replaceAll(/[^\d.]+/g, ""));
}

/**
 * @param {string} source
 * @param {string} context
 */
function getTranslationLink(source, context) {
    const { lang, version } = getLangAndVersion();
    if (!termHashes.has(source)) {
        termHashes.set(source, siphash(WEBLATE_SIPHASH_KEY, source));
    }
    const checksum = termHashes.get(source);
    return `${BASE_TRANSLATE_URL}${version}/${context}/${lang}/?checksum=${checksum}`;
}

/**
 * @param {PointerEvent} ev
 */
function onPointerDown(ev) {
    if (!ev.ctrlKey) {
        clearTranslationPointers();
    }
}

/**
 * @param {KeyboardEvent} ev
 */
function onKeyDown(ev) {
    if (ev.key === "Escape") {
        clearTranslationPointers();
    }
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
     */
    _getElementInfo(node) {
        const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
        if (!el) {
            return null;
        }
        /** @type {PositionTranslations[]} */
        const info = [];
        for (const [root, rootTranslations] of this.elementTranslations) {
            if (root === el || root.contains(el)) {
                // Element *is contained* within an existing element:
                // -> return the parent info
                rootTranslations.push(...info);
                return rootTranslations;
            }
            if (el.contains(root)) {
                // Element *contains* an existing element:
                // -> replace that element with the given one and retrieve the existing
                //  info
                this.elementTranslations.delete(root);
                info.push(...rootTranslations);
            }
        }
        this.elementTranslations.set(el, info);
        return info;
    }

    /**
     * @private
     * @param {Node} node
     * @param {Attr} attribute
     * @param {boolean} highlightsEnabled
     */
    _translateAttribute(node, attribute, highlightsEnabled) {
        const [value, translations] = parseTranslatedText(attribute.value.trim());
        if (!translations.length) {
            return;
        }

        attribute.value = value;
        if (!highlightsEnabled) {
            return;
        }

        const info = this._getElementInfo(node);
        if (info) {
            info.push([attribute.name, translations]);
        }
    }

    /**
     * @private
     * @param {HTMLCanvasElement} node
     * @param {string} text
     * @param {boolean} highlightsEnabled
     */
    _translateCanvasText(canvas, text, highlightsEnabled) {
        const [value, translations] = parseTranslatedText(text.trim());
        if (!translations.length) {
            return text;
        }
        if (highlightsEnabled) {
            const info = this._getElementInfo(canvas);
            if (info) {
                info.push(["canvas", translations]);
            }
        }
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
                    this._translateProperty(node, "textContent", this.highlightsEnabled);
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
            this._translateAttribute(node, attribute, this.highlightsEnabled);
        }

        // Replace and highlight translated properties
        for (const propertyName in TRANSLATABLE_PROPERTY_LABELS) {
            this._translateProperty(node, propertyName, this.highlightsEnabled);
        }
    }

    /**
     * @private
     * @param {Node} node
     * @param {string} property
     * @param {boolean} highlightsEnabled
     */
    _translateProperty(node, property, highlightsEnabled) {
        const rawValue = node[property];
        if (typeof rawValue !== "string" || !rawValue) {
            return;
        }

        const [value, translations] = parseTranslatedText(rawValue);
        if (!translations.length) {
            return;
        }

        node[property] = value;
        if (!highlightsEnabled) {
            return;
        }

        const info = this._getElementInfo(node);
        if (info) {
            info.push([property, translations]);
        }
    }
}

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
    ku: "ckb",
    "sr@latin": "sr_Latn",
    nb: "nb_NO",
    tl: "fil",
};
const POINTER_MARGIN = 5;
const POINTER_MIN_SIZE = 32;

/** @type {Map<string, string>} */
const termHashes = new Map();
/** @type {Map<HTMLElement, HTMLDivElement>} */
const translationPointers = new Map();

export class TranslationModeService {
    started = false;

    /**
     * @param {import("@web/env").OdooEnv} _env
     * @param {import("services").Services} services
     */
    setup(_env, { localization }) {
        if (this.started) {
            return;
        }

        this.started = true;
        this.highlightsEnabled = localization.code !== "en_US";
        if (this.highlightsEnabled) {
            console.debug(`Interactive translation mode is active with translation highlighting.`);
        } else {
            console.log(
                `Interactive translation mode is active, but translation highlighting has been disabled for language "${localization.code}".`
            );
        }

        /** @type {Set<Node>} */
        this.observedNodes = new Set();
        this.observer = new MutationObserver(this._onMutation.bind(this));
        /** @type {TargetedTranslation[]} */
        this.currentTranslations = reactive([]);

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

        // Start observing mutations immediatly
        this._observe();

        patch(CanvasRenderingContext2D.prototype, {
            fillText(text, ...args) {
                return super.fillText(scanner._translateCanvasText(this.canvas, text), ...args);
            },
            measureText(text, ...args) {
                return super.measureText(parseTranslatedText(text)[0], ...args);
            },
            strokeText(text, ...args) {
                return super.strokeText(scanner._translateCanvasText(this.canvas, text), ...args);
            },
        });

        window.addEventListener(
            "scroll",
            debounce(this._onWindowScroll.bind(this), "animationFrame"),
            { capture: true }
        );
    }

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
            node.addEventListener("pointerdown", onPointerDown, { capture: true });
            node.addEventListener("keydown", onKeyDown, { capture: true });
        }
    }

    destroy() {
        this._disconnect();

        registry.category("main_components").remove("translation-mode-side-panel");

        for (const node of this.observedNodes) {
            node.removeEventListener("pointerdown", onPointerDown, { capture: true });
            node.removeEventListener("keydown", onKeyDown, { capture: true });
        }
    }

    getTranslations() {
        const translated = [];
        const untranslated = [];
        for (const translation of this.currentTranslations) {
            if (translation.translated) {
                translated.push(translation);
            } else {
                untranslated.push(translation);
            }
        }
        return { translated, untranslated };
    }

    /**
     * @param {TargetedTranslation} translation
     * @param {boolean} keepHighlighted
     */
    highlightTranslation(translation, keepHighlighted) {
        this._handleMutations(this._disconnect());

        if (!keepHighlighted) {
            clearTranslationPointers();
        }
        for (const [el] of translation.targets) {
            createTranslationPointer(el, translation.translated);
        }

        this._observe();
    }

    registerSidePanel() {
        registry.category("main_components").add("translation-mode-side-panel", {
            Component: TranslationModeSidePanel,
            props: {
                translations: this.currentTranslations,
            },
        });
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

    /**
     * @protected
     */
    _disconnect() {
        const remainingMutations = this.observer.takeRecords();
        this.observer.disconnect();

        return remainingMutations;
    }

    /**
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
     * @protected
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
                    node.removeEventListener("pointerdown", onPointerDown, { capture: true });
                    node.removeEventListener("keydown", onKeyDown, { capture: true });

                    // Add them back
                    node.addEventListener("pointerdown", onPointerDown, { capture: true });
                    node.addEventListener("keydown", onKeyDown, { capture: true });
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
     * @protected
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
     * @param {Event} ev
     */
    _onWindowScroll(ev) {
        if (
            ev.target.nodeType === Node.ELEMENT_NODE &&
            ev.target.closest(".o-translate-side-panel")
        ) {
            return;
        }
        for (const [target, pointer] of translationPointers) {
            updateTranslationPointer(target, pointer);
        }
    }

    /**
     * @protected
     * @param {Record<string, TargetedTranslation>} newTranslations
     */
    _registerTranslations(newTranslations) {
        const oldTranslations = new Map(this.currentTranslations.map((t) => [t.source, t]));
        for (const translation of Object.values(newTranslations)) {
            const existingTranslation = oldTranslations.get(translation.source);
            if (existingTranslation) {
                const nextTargets = new Set();
                for (const target of existingTranslation.targets) {
                    if (target[0].isConnected) {
                        nextTargets.add(target);
                    }
                }
                for (const newTarget of translation.targets) {
                    nextTargets.add(newTarget);
                }
                if (nextTargets.size) {
                    translation.targets = [...nextTargets];
                    oldTranslations.delete(translation.source);
                }
            } else {
                this.currentTranslations.push(translation);
            }
        }
        for (const translation of oldTranslations.values()) {
            const nextTargets = new Set();
            for (const target of translation.targets) {
                if (target[0].isConnected) {
                    nextTargets.add(target);
                }
            }
            if (nextTargets.size) {
                translation.targets = [...nextTargets];
            } else {
                const index = this.currentTranslations.indexOf(translation);
                this.currentTranslations.splice(index, 1);
            }
        }
    }
}

export const translationModeServiceFactory = {
    dependencies: ["localization"],
    start(env, dependencies) {
        const service = new TranslationModeService();
        service.setup(env, dependencies);
        if (isTranslateModeEnabled(env)) {
            service.registerSidePanel();
        }
        return service;
    },
};

export const urlParams = {
    lang: "",
    version: "",
};

if (window === window.top) {
    registry.category("services").add("translation_mode", translationModeServiceFactory);
}
