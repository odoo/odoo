import { expect, queryFirst, test } from "@odoo/hoot";
import { AREAS } from "@website/builder/plugins/customize_website_plugin";
import {
    AREA_SELECTORS,
    THEME_GATES,
} from "@website/builder/plugins/theme_computed_preview_plugin";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

// The builder's tables repeat names and selectors of the compiled CSS: a typo
// on either side would only break the preview, silently.
test("the theme gates and areas the builder knows are the compiled CSS's", async () => {
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    const selectors = [];
    // The custom properties the CSS declares.
    const properties = new Set();
    const collect = (rules) => {
        for (const rule of rules) {
            if (rule.selectorText) {
                selectors.push(rule.selectorText);
            }
            for (const property of rule.style || []) {
                if (property.startsWith("--")) {
                    properties.add(property.slice(2));
                }
            }
            if (rule.cssRules) {
                collect(rule.cssRules);
            }
        }
    };
    for (const sheet of queryFirst(":iframe html").ownerDocument.styleSheets) {
        collect(sheet.cssRules);
    }
    const cssGates = new Set(
        selectors.flatMap((selector) =>
            [...selector.matchAll(/data-o-theme-gates~="([^"]+)"/g)].map(([, gate]) => gate)
        )
    );
    // Computed by the server with the colors (see `color_system.py`).
    const computedGates = ["menu-dark", "body-dark"];
    expect(
        [...cssGates].filter((gate) => !(gate in THEME_GATES || computedGates.includes(gate)))
    ).toEqual([]);
    expect(Object.keys(THEME_GATES).filter((gate) => !cssGates.has(gate))).toEqual([]);
    expect(computedGates.filter((gate) => !cssGates.has(gate))).toEqual([]);
    // The values a gate compares are the ones the CSS reads (the others may
    // be unset, then not printed).
    const names = Object.values(THEME_GATES).flatMap(({ apart = [] }) => apart);
    expect(names.filter((name) => !properties.has(name))).toEqual([]);
    expect(Object.keys(AREA_SELECTORS)).toEqual(AREAS);
    // An area's selector, as the builder marks it, ends with the one the CSS
    // gives the area's rules (it may narrow it, e.g. to the website's header).
    const parts = selectors.flatMap((selector) => selector.split(",").map((part) => part.trim()));
    expect(
        Object.entries(AREA_SELECTORS)
            .filter(([area, areaSelector]) => {
                const prefix = `:where(html[data-o-theme-gates~="${area}-custom"]) `;
                return !parts.some(
                    (part) =>
                        part.startsWith(prefix) && areaSelector.endsWith(part.slice(prefix.length))
                );
            })
            .map(([area]) => area)
    ).toEqual([]);
});
