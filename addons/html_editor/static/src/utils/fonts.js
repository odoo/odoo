/** @odoo-module native */
const DEFAULT_FACE = "fa-solid";
// FontAwesome 7 glyph rules set only `--fa`; the face they belong to is the
// last `--fa-family` marker rule before them in source order (`.fab,
// .fa-brands {...}` opens brands.css), unless the rule names its own family,
// as the v4 shims do.
const FACE_MARKERS = {
    fab: "fa-brands",
    "fa-brands": "fa-brands",
    fas: DEFAULT_FACE,
    far: DEFAULT_FACE,
    "fa-classic": DEFAULT_FACE,
};
const FACE_FAMILY_RE = /--fa-family\s*:\s*var\(--fa-family-(\w+)\)/;

function faceOfRule(selectors, cssText, currentFace) {
    const family = cssText.match(FACE_FAMILY_RE)?.[1];
    if (family) {
        const named = family === "brands" ? "fa-brands" : DEFAULT_FACE;
        if (/--fa\s*:/.test(cssText)) {
            return { face: named, nextFace: currentFace };
        }
        const marker = selectors.find((selector) => FACE_MARKERS[selector.slice(1)]);
        if (marker) {
            return { face: currentFace, nextFace: FACE_MARKERS[marker.slice(1)] };
        }
    }
    return { face: currentFace, nextFace: currentFace };
}

export const fonts = {
    /**
     * @param {Regex} filter
     * @param {Regex} [cssFilter]
     * @returns {Object[]}
     */
    cacheCssSelectors: {},
    getCssSelectors: function (filter, cssFilter) {
        const cacheKey = `${filter}${cssFilter || ""}`;
        if (this.cacheCssSelectors[cacheKey]) {
            return this.cacheCssSelectors[cacheKey];
        }
        this.cacheCssSelectors[cacheKey] = [];
        // FontAwesome 7 writes an icon and each of its aliases as separate
        // rules with the same glyph, canonical name first; one icon per
        // glyph, or the picker lists it twice and stores whichever name
        // was clicked.
        const byCss = new Map();
        const sheets = document.styleSheets;
        let currentFace = DEFAULT_FACE;
        for (let i = 0; i < sheets.length; i++) {
            let rules;
            try {
                rules = sheets[i].rules || sheets[i].cssRules;
            } catch {
                continue;
            }
            if (!rules) {
                continue;
            }

            for (let r = 0; r < rules.length; r++) {
                const selectorText = rules[r].selectorText;
                if (!selectorText) {
                    continue;
                }
                const selectors = selectorText.split(/\s*,\s*/);
                const { face, nextFace } = faceOfRule(
                    selectors,
                    rules[r].cssText,
                    currentFace,
                );
                currentFace = nextFace;
                if (cssFilter && !cssFilter.test(rules[r].cssText)) {
                    continue;
                }
                let data = null;
                for (let s = 0; s < selectors.length; s++) {
                    const match = selectors[s].trim().match(filter);
                    if (!match) {
                        continue;
                    }
                    if (!data) {
                        data = {
                            selector: match[0],
                            css: rules[r].cssText.replace(
                                /(^.*\{\s*)|(\s*\}\s*$)/g,
                                "",
                            ),
                            names: [match[1]],
                            face,
                        };
                    } else {
                        data.selector += ", " + match[0];
                        data.names.push(match[1]);
                    }
                }
                if (data) {
                    const key = `${data.face}|${data.css}`;
                    const known = byCss.get(key);
                    if (known) {
                        known.selector += ", " + data.selector;
                        known.names.push(...data.names);
                    } else {
                        byCss.set(key, data);
                        this.cacheCssSelectors[cacheKey].push(data);
                    }
                }
            }
        }
        return this.cacheCssSelectors[cacheKey];
    },
    fontIcons: [
        { base: "fa-solid", parser: /\.(fa-(?:\w|-)+)$/i, cssFilter: /--fa\s*:/ },
        { base: "fa-brands", parser: /\.(fa-(?:\w|-)+)$/i, cssFilter: /--fa\s*:/ },
    ],
    computedFonts: false,
    computeFonts: function () {
        if (!this.computedFonts) {
            const self = this;
            this.fontIcons.forEach((data) => {
                data.cssData = self
                    .getCssSelectors(data.parser, data.cssFilter)
                    .filter((x) => x.face === data.base);
                data.alias = data.cssData.map((x) => x.names).flat();
            });
            this.computedFonts = true;
        }
    },
    /**
     * @returns {string[]} every icon class of every face
     */
    iconNames: function () {
        this.computeFonts();
        return this.fontIcons.flatMap((data) => data.alias);
    },
    /**
     * @param {string} iconClass
     * @returns {string|undefined} the face class rendering that icon
     */
    faceOf: function (iconClass) {
        this.computeFonts();
        return this.fontIcons.find((data) => data.alias.includes(iconClass))?.base;
    },
};
