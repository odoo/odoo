const OPENING_TAG_REGEX = /<\s*([^\s/>]+)([^>]*?)(\/?)>/g;
const ATTRIBUTES_REGEX = /([^\s=]+)(=(?:"[^"]*"|'[^']*'))?/g;

/**
 * Unformat the given html in order to use it with `innerHTML`.
 */
export function unformat(html) {
    return (
        html
            // Trim whitespaces between attributes.
            .replace(OPENING_TAG_REGEX, (match, tag, attrs, selfClosing) => {
                // Isolate each attribute key/value pair.
                const attributes = attrs.match(ATTRIBUTES_REGEX);
                return `<${tag}${attributes ? " " + attributes.join(" ") : ""}${selfClosing}>`;
            })
            // Trim whitespace (except \ufeff) between > and <.
            .replace(/>[^\S\uFEFF]+/g, ">")
            .replace(/[^\S\uFEFF]+</g, "<")
            .trim()
    );
}

/**
 * Remove ZWNBSP characters and o_link_in_selection class from the given string
 * in order to make assertions easier to write and read.
 *
 * @param {string} html
 */
export function cleanLinkArtifacts(html) {
    // Multiple classes not supported (not needed for now)
    return html.replaceAll("\uFEFF", "").replace(/ class="o_link_in_selection"/g, "");
}
