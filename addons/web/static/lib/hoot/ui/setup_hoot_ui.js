/** @odoo-module */

import { mount, reactive } from "@odoo/owl";
import { HootFixtureElement } from "../core/fixture";
import { waitForDocument } from "../hoot_utils";
import { getRunner } from "../main_runner";
import { patchWindow } from "../mock/window";
import {
    generateStyleSheets,
    getColorScheme,
    onColorSchemeChange,
    setColorRoot,
} from "./hoot_colors";
import { HootMain } from "./hoot_main";

/**
 * @typedef {"failed" | "passed" | "skipped" | "todo"} StatusFilter
 *
 * @typedef {ReturnType<typeof makeUiState>} UiState
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    customElements,
    document,
    fetch,
    HTMLElement,
    Object: { entries: $entries },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {string} href
 */
function createLinkElement(href) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    return link;
}

/**
 * @param {string} content
 */
function createStyleElement(content) {
    const style = document.createElement("style");
    style.innerText = content;
    return style;
}

function getPrismStyleUrl() {
    const theme = getColorScheme() === "dark" ? "okaida" : "default";
    return `/web/static/lib/prismjs/themes/${theme}.css`;
}

function loadAsset(tagName, attributes) {
    return new Promise((resolve, reject) => {
        const el = document.createElement(tagName);
        Object.assign(el, attributes);
        el.addEventListener("load", resolve);
        el.addEventListener("error", reject);
        document.head.appendChild(el);
    });
}

async function loadBundle(bundle) {
    const bundleResponse = await fetch(`/web/bundle/${bundle}`);
    const result = await bundleResponse.json();
    const promises = [];
    for (const { src, type } of result) {
        if (src && type === "link") {
            loadAsset("link", {
                rel: "stylesheet",
                href: src,
            });
        } else if (src && type === "script") {
            promises.push(
                loadAsset("script", {
                    src,
                    type: "text/javascript",
                })
            );
        }
    }
    await Promise.all(promises);
}

class HootContainer extends HTMLElement {
    constructor() {
        super(...arguments);

        this.attachShadow({ mode: "open" });
    }

    connectedCallback() {
        setColorRoot(this);
    }

    disconnectedCallback() {
        setColorRoot(null);
    }
}

customElements.define("hoot-container", HootContainer);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function makeUiState() {
    return reactive({
        resultsPage: 0,
        resultsPerPage: 40,
        /** @type {string | null} */
        selectedSuiteId: null,
        /** @type {"asc" | "desc" | false} */
        sortResults: false,
        /** @type {StatusFilter | null} */
        statusFilter: null,
        totalResults: 0,
    });
}

/**
 * Appends the main Hoot UI components in a container, which itself will be appended
 * on the current document body.
 *
 * @returns {Promise<void>}
 */
export async function setupHootUI() {
    // - Patch window before code from other modules is executed
    patchWindow();

    const runner = getRunner();

    const container = document.createElement("hoot-container");
    container.style.display = "contents";

    await waitForDocument(document);

    document.head.appendChild(HootFixtureElement.styleElement);
    document.body.appendChild(container);

    const promises = [
        // Mount main container
        mount(HootMain, container.shadowRoot, {
            env: {
                runner,
                ui: makeUiState(),
            },
            name: "HOOT",
        }),
    ];

    if (!runner.headless) {
        // In non-headless: also wait for lazy-loaded libs (Highlight & DiffMatchPatch)
        promises.push(loadBundle("web.assets_unit_tests_setup_ui"));

        let colorStyleContent = "";
        for (const [className, content] of $entries(generateStyleSheets())) {
            const selector = className === "default" ? ":host" : `:host(.${className})`;
            colorStyleContent += `${selector}{${content}}`;
        }

        const prismStyleLink = createLinkElement(getPrismStyleUrl());
        onColorSchemeChange(() => {
            prismStyleLink.href = getPrismStyleUrl();
        });

        container.shadowRoot.append(
            createStyleElement(colorStyleContent),
            createLinkElement("/web/static/src/libs/fontawesome/css/font-awesome.css"),
            prismStyleLink,
            // Hoot-specific style is loaded last to take priority over other stylesheets
            createLinkElement("/web/static/lib/hoot/ui/hoot_style.css")
        );
    }

    await Promise.all(promises);
}
