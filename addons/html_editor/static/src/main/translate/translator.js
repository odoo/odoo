import { rpc } from "@web/core/network/rpc";

const POSTPROCESS_GENERATED_CONTENT = (content, baseContainer, document) => {
    let lines = content.split("\n");
    if (baseContainer.toUpperCase() === "P") {
        // P has a margin bottom which is used as an interline, no need to
        // keep empty lines in that case.
        lines = lines.filter((line) => line.trim().length);
    }
    const fragment = document.createDocumentFragment();
    let parentUl, parentOl;
    let lineIndex = 0;
    for (const line of lines) {
        if (line.trim().startsWith("- ")) {
            // Create or continue an unordered list.
            parentUl = parentUl || document.createElement("ul");
            const li = document.createElement("li");
            li.textContent = line.trim().slice(2);
            parentUl.appendChild(li);
        } else if (
            (parentOl && line.startsWith(`${parentOl.children.length + 1}. `)) ||
            (!parentOl && line.startsWith("1. ") && lines[lineIndex + 1]?.startsWith("2. "))
        ) {
            // Create or continue an ordered list (only if the line starts
            // with the next number in the current ordered list (or 1 if no
            // ordered list was in progress and it's followed by a 2).
            parentOl = parentOl || document.createElement("ol");
            const li = document.createElement("li");
            li.textContent = line.slice(line.indexOf(".") + 2);
            parentOl.appendChild(li);
        } else if (line.trim().length === 0) {
            const emptyLine = document.createElement("DIV");
            emptyLine.append(document.createElement("BR"));
            fragment.appendChild(emptyLine);
        } else {
            // Insert any list in progress, and a new block for the current
            // line.
            [parentUl, parentOl].forEach((list) => list && fragment.appendChild(list));
            parentUl = parentOl = undefined;
            const block = document.createElement(line.startsWith("Title: ") ? "h2" : baseContainer);
            block.textContent = line;
            fragment.appendChild(block);
        }
        lineIndex += 1;
    }
    [parentUl, parentOl].forEach((list) => list && fragment.appendChild(list));
    return fragment;
};

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
     * @returns {Object} { translatedContent: String, isError: Boolean }
     */
    async translate(originalText, targetLang, baseContainer, document) {
        const translatedContent = `Translated content`; // Placeholder for actual translation logic
        return {
            translatedContent: translatedContent,
            isError: false,
        };
    }
}

export class GoogleTranslator extends Translator {
    async translate(fragment, targetLang, baseContainer, document) {
        const protectedCallback = (content) => {
            delete this.pendingRpcPromise;
            return {
                translatedContent: POSTPROCESS_GENERATED_CONTENT(
                    content.translated_text,
                    baseContainer,
                    document
                ),
                isError: content.isError || false,
            };
        };
        const googleLanguageCode = targetLang.languageCode.replace("_", "-"); // Google Translate API expects language codes in the format "en-US"
        this.pendingRpcPromise = rpc(
            "/html_editor/google_translate",
            {
                originalText: fragment.textContent,
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

    async translate(fragment, targetLang, baseContainer, document) {
        const content = document.createElement("div");
        content.appendChild(fragment.cloneNode(true));
        const query = `Translate <generated_html>${content.innerHTML}</generated_html> to ${targetLang.languageName}`;
        function contentCleaningCallback(content, isError) {
            const translatedContent = content
                .replace(/^[\s\S]*<generated_html>/, "")
                .replace(/<\/generated_html>[\s\S]*$/, "");
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
            const doc = new DOMParser().parseFromString(translatedContent, "text/html");
            const fragment = document.createDocumentFragment();
            fragment.append(...doc.body.childNodes);
            return {
                translatedContent: fragment,
                isError,
            };
        }

        return await this.generate(query, contentCleaningCallback.bind(this));
    }
}
