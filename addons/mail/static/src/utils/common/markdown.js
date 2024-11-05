const SAFE_URL_PATTERN =
    /^(?!(javascript:|vbscript:|data:))(?:[a-z0-9+.-]+:|[^&:/?#]*(?:[/?#]|$))/i;

// Extracted from the marked library
function cleanUrl(href) {
    if (!SAFE_URL_PATTERN.test(href)) {
        return null;
    }
    try {
        href = encodeURI(href).replace(/%25/g, "%");
    } catch {
        return null;
    }
    return href;
}

let odooMarked;
export function markdown(markdown) {
    if (!odooMarked) {
        const odooRenderer = {
            useNewRenderer: true,
            breaks: true,
            renderer: {
                // Override the link renderer to add `target="_blank"`
                link({ href, title, tokens }) {
                    const text = this.parser.parseInline(tokens);
                    const cleanHref = cleanUrl(href);
                    if (cleanHref === null) {
                        return text;
                    }
                    href = cleanHref;
                    const link = document.createElement("a");
                    link.setAttribute("href", href);
                    if (title) {
                        link.setAttribute("title", title);
                    }
                    link.setAttribute("target", "_blank");
                    link.setAttribute("rel", "noreferrer noopener");
                    link.innerHTML = text;
                    return link.outerHTML;
                },
                code({ text, lang, escaped }) {
                    const langString = (lang || "").match(/^\S*/)?.[0];
                    const codeAsText = text.replace(/\n$/, "") + "\n";
                    const pre = document.createElement("pre");
                    const code = document.createElement("code");
                    pre.appendChild(code);
                    if (langString) {
                        code.setAttribute("class", `language-${langString}`);
                    }
                    code.appendChild(document.createTextNode(codeAsText));
                    return pre.outerHTML;
                },
            },
            tokenizer: {
                hr() {
                    return;
                },
                lheading() {
                    return;
                },
                codespan(src) {
                    // override this token to avoid unecessary escaping
                    const cap = this.rules.inline.code.exec(src);
                    if (cap) {
                        let text = cap[2].replace(/\n/g, " ");
                        const hasNonSpaceChars = /[^ ]/.test(text);
                        const hasSpaceCharsOnBothEnds = /^ /.test(text) && / $/.test(text);
                        if (hasNonSpaceChars && hasSpaceCharsOnBothEnds) {
                            text = text.substring(1, text.length - 1);
                        }
                        return {
                            type: "codespan",
                            raw: cap[0],
                            text,
                        };
                    }
                },
            },
        };
        odooMarked = new window.marked.Marked(odooRenderer);
    }
    return DOMPurify.sanitize(odooMarked.parse(markdown), {
        ADD_ATTR: ["target"],
    });
}
