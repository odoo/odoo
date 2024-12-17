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
    return (
        html
            .replaceAll("\uFEFF", "")
            // o_link_in_selection as single class
            .replace(/ class="o_link_in_selection"/g, "")
            // o_link_in_selection among other classes (except if last one)
            .replace(/o_link_in_selection /g, "")
            // o_link_in_selection as last class
            .replace(/ o_link_in_selection/g, "")
    );
}
