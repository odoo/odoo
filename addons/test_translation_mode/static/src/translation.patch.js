import { TranslatedString } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/**
 * @typedef {{
 *  context: string;
 *  isTranslated: boolean;
 *  source: string;
 *  translation: string;
 * }} ContextualizedTranslation
 *
 * @typedef {[context: string, source: string, translation?: string]} TranslationMetadata
 */

/**
 * @template [T=unknown]
 * @typedef {import("@web/core/utils/strings").Substitutions<T>} Substitutions
 */

/**
 * @param {string} context
 * @param {string} translation
 */
function contextualizeTranslation(context, translation) {
    if (context === TRANSLATION_MODE_ADDON_NAME) {
        return translation.replaceAll(RE_CONTEXTUALIZED_TRANSLATION, "");
    }
    if (translation.match(RE_CONTEXTUALIZED_TRANSLATION)) {
        return translation;
    }
    // 'isTranslated' is always 0 if it comes from here
    return encodeTranslation(0, [context, translation], translation);
}

/**
 * @param {string} encodedBytes
 * @param {number} start
 * @param {number} count
 */
function decodeByte(encodedBytes, start, count) {
    let total = 0;
    for (let i = 0; i < count; i++) {
        total |= CT_LOOKUP[encodedBytes[start + i]] << ((count - i - 1) * 4);
    }
    return total;
}

/**
 * Parameters used to encode and decode contextualized translations (short: 'CT').
 *
 * Translation metadata:
 *
 * Each translation is preceded by its context, or "metadata", which is a 'list' containing:
 * - :int: whether the term is translated (0 or 1);
 * - :string: the (encoded) addon from which the translation originates;
 * - :string: the (encoded) source term
 * - :string: (optional the (encoded) translation, attached only if:
 *     > it exists for the given source (if not, source == translation)
 *     > the translated term differs from its source
 *
 * Encoding:
 *
 * This metadata is "encoded" and attached to each translated string. It is encoded
 * using the following system:
 * 1. the metadata (list) is stringified;
 * 2. stringified metadata is converted to bytes array;
 * 3. each byte is then converted to a tuple of its base-16 integer components;
 * 4. each integer is then swapped with its corresponding zero-width character.
 *
 * Hiding:
 *
 * The metadata is encoded in zero-width characters to allow 2 things:
 * - being properly picked up by the client code with an arrangement of non-conventional characters;
 * - being invisible in the UI, should the service not work or fail to pick up a translation.
 *
 * Encoding happens on the server side; @see {@link addons/test_translation_mode/tools/translate.py}
 */
const CT_MAP =
    "\u200B\u200C\u200D\u200E\u200F\u2060\u2061\u2062\u2063\u2064\uFE00\uFE01\uFE02\uFE03\uFE04\uFE05".split(
        ""
    );
const CT_LOOKUP = Object.fromEntries(CT_MAP.map((char, i) => [char, i]));
const RE_CONTEXTUALIZED_TRANSLATION = new RegExp(
    `([${CT_MAP[0]}${CT_MAP[1]}])([${CT_MAP.join("")}]{4,})`,
    "g"
);
const TRANSLATION_MODE_ADDON_NAME = "test_translation_mode";

// Used to encode/decode translation context from strings
const decoder = new TextDecoder("utf-8");
const encoder = new TextEncoder();

patch(TranslatedString.prototype, {
    valueOf() {
        const translation = super.valueOf();
        if (isTranslationModeEnabled()) {
            return contextualizeTranslation(this.context, translation);
        } else {
            return translation;
        }
    },
});

/**
 * @param {0 | 1} isTranslated
 * @param {TranslationMetadata} metadata
 * @param {string} translation
 */
export function encodeTranslation(isTranslated, metadata, translation) {
    const strMetadata = JSON.stringify(metadata);
    const bytesMetadata = encoder.encode(strMetadata);
    const byteCount = bytesMetadata.length;
    let encodedMetadata =
        CT_MAP[isTranslated] +
        CT_MAP[(byteCount >> 12) & 0xf] +
        CT_MAP[(byteCount >> 8) & 0xf] +
        CT_MAP[(byteCount >> 4) & 0xf] +
        CT_MAP[byteCount & 0xf];
    for (const charCode of bytesMetadata) {
        encodedMetadata += CT_MAP[(charCode >> 4) & 0xf] + CT_MAP[charCode & 0xf];
    }
    return encodedMetadata + translation;
}

/**
 * @param {import("@web/env").OdooEnv} [env]
 */
export function isTranslationModeEnabled(env) {
    const debug = env?.debug ?? odoo.debug ?? "";
    return debug.includes("translate");
}

/**
 * @param {string} text
 * @returns {[value: string, translations: ContextualizedTranslation[]]}
 */
export function parseTranslatedText(text) {
    /** @type {ContextualizedTranslation[]} */
    const translations = [];
    const cleanedText = text.replaceAll(
        RE_CONTEXTUALIZED_TRANSLATION,
        (fullMatch, isTranslatedBit, encodedMetadata) => {
            const byteCount = decodeByte(encodedMetadata, 0, 4);
            if (!byteCount || 2 * byteCount > encodedMetadata.length - 4) {
                return fullMatch;
            }
            const bytes = new Uint8Array(byteCount);
            for (let i = 0; i < byteCount; i++) {
                bytes[i] = decodeByte(encodedMetadata, i * 2 + 4, 2);
            }
            const strJsonMetadata = decoder.decode(bytes);
            const [context, source, translation] = JSON.parse(strJsonMetadata);
            translations.push({
                context,
                isTranslated: isTranslatedBit === CT_MAP[1],
                source,
                translation: translation || source,
            });
            return "";
        }
    );
    return [cleanedText, translations];
}
