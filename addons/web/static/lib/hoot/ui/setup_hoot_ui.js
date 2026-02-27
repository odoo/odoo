/** @odoo-module */

import { mount } from "@odoo/owl";
import { HootFixtureElement } from "../core/fixture";
import { waitForDocument } from "../hoot_utils";
import { patchWindow } from "../mock/window";
import { colorRoot, colorScheme, generateStyleSheets, onColorSchemeChange } from "./hoot_colors";
import { HootMain } from "./hoot_main";
import { RunnerPlugin } from "./runner_plugin";
import { UiPlugin } from "./ui_plugin";

/**
 * @typedef {import("../core/runner").Runner} Runner
 *
 * @typedef {"failed" | "passed" | "skipped" | "todo"} StatusFilter
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
    const theme = colorScheme() === "dark" ? "okaida" : "default";
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
        colorRoot.set(this);
    }

    disconnectedCallback() {
        colorRoot.set(null);
    }
}

customElements.define("hoot-container", HootContainer);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Appends the main Hoot UI components in a container, which itself will be appended
 * on the current document body.
 *
 * @param {Runner} runner
 */
export async function setupHootUI(runner) {
    // - Patch window before code from other modules is executed
    patchWindow();

    const container = document.createElement("hoot-container");
    container.style.display = "contents";

    await waitForDocument(document);

    document.head.appendChild(HootFixtureElement.styleElement);
    document.body.appendChild(container);

    const promises = [
        // Mount main container
        mount(HootMain, container.shadowRoot, {
            name: "HOOT",
            plugins: [RunnerPlugin, UiPlugin],
            config: { runner },
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
