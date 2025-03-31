/**
 * Unformat the given html in order to use it with `innerHTML`.
 */
export function unformat(html) {
    return html
        .replace(/(^|[^ ])[\s\n]+([^<>]*?)</g, "$1$2<")
        .replace(/>([^<>]*?)[\s\n]+([^ ]|$)/g, ">$1$2");
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
