import { rpc } from "@web/core/network/rpc";

class Translator {
    constructor(id, name) {
        this.id = id;
        this.name = name;
    }

    /**
     * translate text to a given language, returns the translated text and
     * indicates if there was an error
     *
     * @param {String} originalText the text needs to be translated
     * @param {String} targetLang the destination language
     *
     * @returns {Object} { translatedText: String, isError: Boolean }
     */
    async translate(originalText, targetLang) {
        const translatedText = `Translated content`; // Placeholder for actual translation logic
        return {
            translatedText: translatedText,
            isError: false,
        };
    }
}

export class GoogleTranslator extends Translator {
    async translate(originalText, targetLang) {
        const protectedCallback = (content) => {
            delete this.pendingRpcPromise;
            return {
                translatedText: content.translated_text,
                isError: content.isError || false,
            };
        };
        const googleLanguageCode = targetLang.languageCode.replace("_", "-"); // Google Translate API expects language codes in the format "en-US"
        this.pendingRpcPromise = rpc(
            "/html_editor/google_translate",
            {
                originalText,
                targetLang: googleLanguageCode,
            },
            { silent: true }
        );
        return await this.pendingRpcPromise
            .then((content) => protectedCallback(content))
            .catch((error) =>
                protectedCallback({
                    translated_text: error.data?.message || error.message,
                    isError: true,
                })
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
                    "You are a translation assistant. You goal is to translate text while maintaining the original format and" +
                    "respecting specific instructions. \n" +
                    "Instructions: \n" +
                    "- You must respect the format (wrapping the translated text between <generated_text> and </generated_text>)\n" +
                    "- Do not write HTML.",
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

    async translate(originalText, targetLang) {
        const query = `Translate <generated_text>${originalText}</generated_text> to ${targetLang.languageName}`;
        function contentCleaningCallback(content, isError) {
            const translatedText = content
                .replace(/^[\s\S]*<generated_text>/, "")
                .replace(/<\/generated_text>[\s\S]*$/, "");
            if (!isError) {
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
            }

            return {
                translatedText,
                isError,
            };
        }

        return await this.generate(query, contentCleaningCallback.bind(this));
    }
}
