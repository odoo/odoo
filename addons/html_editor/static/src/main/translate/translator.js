import { rpc } from "@web/core/network/rpc";

class Translator {
    constructor(id, name) {
        this.id = id;
        this.name = name;
    }

    /**
     * Translate an HTML fragment to a given language.
     *
     * @param {string} originalHtml the HTML that needs to be translated
     * @param {{ languageCode: string, languageName: string }} targetLang the
     *        destination language
     *
     * @returns {Promise<{ translatedHtml: string } | { isError: true, message: string }>}
     */
    async translate(originalHtml, targetLang) {
        return { translatedHtml: originalHtml }; // Placeholder for actual translation logic
    }
}

export class GoogleTranslator extends Translator {
    async translate(originalHtml, targetLang) {
        const protectedCallback = (result) => {
            delete this.pendingRpcPromise;
            return result;
        };
        const googleLanguageCode = targetLang.languageCode.replace("_", "-"); // Google Translate API expects language codes in the format "en-US"
        this.pendingRpcPromise = rpc(
            "/html_editor/google_translate",
            {
                originalHtml,
                targetLang: googleLanguageCode,
            },
            { silent: true }
        );
        return await this.pendingRpcPromise
            .then((content) => protectedCallback({ translatedHtml: content.translated_html }))
            .catch((error) =>
                protectedCallback({ isError: true, message: error.data?.message || error.message })
            );
    }
}

export class ChatGPTTranslator extends Translator {
    constructor(id, name) {
        super(id, name);
        this.conversationHistory = [
            {
                role: "system",
                content:
                    "You are an HTML-aware translation assistant. Your goal is to translate the text content of the provided HTML into the target language while preserving the HTML structure exactly.\n" +
                    "Instructions:\n" +
                    "- Wrap the entire output between <generated_html> and </generated_html>. Output nothing outside these tags.\n" +
                    "- The input is an HTML fragment. Translate only the human-readable text nodes (including text inside nested elements).\n" +
                    "- Preserve every tag, attribute (names and values), attribute order, inline style, class, id, data-* attribute, and nesting exactly as given. Do not add, remove, reorder, or merge elements.\n" +
                    "- Preserve whitespace, line breaks, and HTML entities (e.g. &nbsp;, &amp;) as in the input.\n" +
                    "- Do not translate or alter: code/pre content, URLs.\n" +
                    "- Keep the text flowing naturally in the target language; word order inside a sentence may change as long as the surrounding tags still wrap the equivalent words.\n" +
                    "- Do not wrap the output in markdown code fences, do not add explanations, comments, or notes.\n" +
                    "- If the input contains no translatable text, return it unchanged inside the tags.\n",
            },
        ];
    }

    generate(prompt, callback) {
        const protectedCallback = (...args) => {
            delete this.pendingRpcPromise;
            return callback(...args);
        };
        this.pendingRpcPromise = rpc(
            "/html_editor/generate_text",
            {
                prompt,
                conversation_history: this.conversationHistory,
            },
            { silent: true }
        );
        return this.pendingRpcPromise
            .then((content) => protectedCallback(content))
            .catch((error) => protectedCallback(error.data?.message || error.message, true));
    }

    async translate(originalHtml, targetLang) {
        const query = `Translate <generated_html>${originalHtml}</generated_html> to ${targetLang.languageName}`;
        function contentCleaningCallback(content, isError) {
            if (isError) {
                return { isError: true, message: content };
            }
            const translatedHtml = content
                .replace(/^[\s\S]*<generated_html>/, "")
                .replace(/<\/generated_html>[\s\S]*$/, "");
            // There was no error, add the response to the history.
            this.conversationHistory.push(
                {
                    role: "user",
                    content: query,
                },
                {
                    role: "assistant",
                    content,
                }
            );
            return { translatedHtml };
        }

        return await this.generate(query, contentCleaningCallback.bind(this));
    }
}
