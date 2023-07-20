/** @odoo-module */

export function fuzzyLookup(pattern, list, fn, options = null) {
    const items = list.map(fn);
    const fuse = new Fuse(items, options);
    const finds = fuse.search(pattern);
    return finds.map((find) => list[find.refIndex]);
}
