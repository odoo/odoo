const SAFE_URL_PATTERN = /^(?!(javascript:|vbscript:|data:))(?:[a-z0-9+.-]+:|[^&:/?#]*(?:[/?#]|$))/i;

// Extracted from the marked library
function cleanUrl(href) {
    if (!SAFE_URL_PATTERN.test(href)) {
        return null;
    }
    try {
        href = encodeURI(href).replace(/%25/g, '%');
    }
    catch {
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
                    let out = '<a href="' + href + '"';
                    if (title) {
                        out += ' title="' + title + '"';
                    }
                    out += ' target="_blank">' + text + '</a>';
                    return out;
                },
                code({ text, lang, escaped }) {
                    const langString = (lang || '').match(/^\S*/)?.[0];
                    const code = text.replace(/\n$/, '') + '\n';
                    if (!langString) {
                        return '<pre><code>'
                            + code
                            + '</code></pre>\n';
                    }
                    return '<pre><code class="language-'
                        + langString
                        + '">'
                        + code
                        + '</code></pre>\n';
                }
            },
            tokenizer: {
                codespan(src) {
                    // override this token to avoid unecessary escaping
                    const cap = this.rules.inline.code.exec(src);
                    if (cap) {
                        let text = cap[2].replace(/\n/g, ' ');
                        const hasNonSpaceChars = /[^ ]/.test(text);
                        const hasSpaceCharsOnBothEnds = /^ /.test(text) && / $/.test(text);
                        if (hasNonSpaceChars && hasSpaceCharsOnBothEnds) {
                            text = text.substring(1, text.length - 1);
                        }
                        return {
                            type: 'codespan',
                            raw: cap[0],
                            text
                        };
                    }
                }
            }
        };
        odooMarked = new window.marked.Marked(odooRenderer);
    }
    return odooMarked.parse(markdown);
};
