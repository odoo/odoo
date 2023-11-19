/**
 * Unformat the given html in order to use it with `innerHTML`.
 */
export function unformat(html) {
    return html
        .replace(/(^|[^ ])[\s\n]+([^<>]*?)</g, "$1$2<")
        .replace(/>([^<>]*?)[\s\n]+([^ ]|$)/g, ">$1$2");
}
