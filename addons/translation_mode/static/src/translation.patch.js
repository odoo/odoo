import { TranslatedString } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/**
 * @typedef {{
 *  context: string;
 *  translated: boolean;
 *  source: string;
 *  translation: string;
 * }} ContextualizedTranslation
 */

/**
 * @template [T=unknown]
 * @typedef {import("@web/core/utils/strings").Substitutions<T>} Substitutions
 */

/**
 * @param {string} context
 * @param {string} source
 * @param {string} translation
 */
function contextualizeTranslation(context, source, translation) {
    if (R_CONTEXTUALIZED_TRANSLATION.test(translation)) {
        return translation;
    }
    return `_(${context},0{${source}}[${translation}])`;
}

const R_CONTEXTUALIZED_TRANSLATION = new RegExp(
    [
        "_\\(", // starting delimiter
        "(?<context>[\\w-]+),", // translation context (i.e. module)
        "(?<translated>0|1)", // 1 if translated, else 0
        "\\{(?<source>.*?)\\}", // source string
        "\\[(?<translation>.*)\\]", // translated string
        "\\)", // ending delimiter"
    ].join("")
);
const R_ESCAPED_SUBSTITUTION = /%%s/g; // server-escaped substitutions in source strings

patch(TranslatedString.prototype, {
    valueOf() {
        const translation = super.valueOf();
        const { context } = this;
        if (isTranslateModeEnabled()) {
            const source = String.prototype.valueOf.call(this);
            return contextualizeTranslation(context, source, translation);
        } else {
            return translation;
        }
    },
});

/**
 * @param {import("@web/env").OdooEnv} [env]
 */
export function isTranslateModeEnabled(env) {
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
    if (!text || !R_CONTEXTUALIZED_TRANSLATION.test(text)) {
        return [text, translations];
    }
    const translationStack = [];
    let pendingChars = "";
    let result = "";
    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        pendingChars += char;
        if (char === "_" && text[i + 1] === "(") {
            if (!translationStack.length) {
                // Add pending chars except "_"
                result += pendingChars.slice(0, -1);
                pendingChars = pendingChars.slice(-1);
            }
            pendingChars += text[++i];
            translationStack.push([1, "", "", "", ""]);
            continue;
        } else if (!translationStack.length) {
            continue;
        }
        const currentTranslation = translationStack.at(-1);
        const partIndex = currentTranslation[0];
        if (char === "," && partIndex === 1) {
            currentTranslation[0] = 2;
        } else if (char === "{" && partIndex === 2) {
            currentTranslation[0] = 3;
        } else if (char === "}" && text[i + 1] === "[" && partIndex === 3) {
            pendingChars += text[++i];
            currentTranslation[0] = 4;
        } else if (char === "]" && text[i + 1] === ")" && partIndex === 4) {
            i++;
            // Add translation to result
            const [, context, translated, source, translation] = translationStack.pop();
            if (translationStack.length) {
                translationStack.at(-1)[4] += translation;
            } else {
                result += translation;
            }
            translations.push({
                context,
                translated: translated === "1",
                source: source.replace(R_ESCAPED_SUBSTITUTION, "%s"),
                translation,
            });
            pendingChars = "";
        } else {
            // Not a special character: add the char to the current part
            currentTranslation[partIndex] += char;
        }
    }
    return [result + pendingChars, translations];
}
