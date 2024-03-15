/** @odoo-module */

import { mount, reactive, whenReady } from "@odoo/owl";
import { patchWindow } from "../mock/window";
import { generateStyleSheets, setColorRoot } from "./hoot_colors";
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
    HTMLElement,
    Object: { entries: $entries },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const makeUiState = () =>
    reactive({
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

class HootContainer extends HTMLElement {
    constructor() {
        super(...arguments);

        this.attachShadow({ mode: "open" });

        const colorStyleElement = document.createElement("style");
        let colorStyleContent = "";
        for (const [className, content] of $entries(generateStyleSheets())) {
            const selector = className === "default" ? ":host" : `:host(.${className})`;
            colorStyleContent += `${selector}{${content}}`;
        }
        colorStyleElement.innerText = colorStyleContent;
        this.shadowRoot.appendChild(colorStyleElement);

        for (const href of STYLE_SHEETS) {
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = href;
            this.shadowRoot.appendChild(link);
        }
    }

    connectedCallback() {
        setColorRoot(this);
    }

    disconnectedCallback() {
        setColorRoot(null);
    }
}

const STYLE_SHEETS = [
    "/web/static/src/libs/fontawesome/css/font-awesome.css",
    "/web/static/lib/hoot/ui/hoot_style.css",
];

customElements.define("hoot-container", HootContainer);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {import("../core/runner").TestRunner} runner
 */
export function setupHootUI(runner) {
    // - Patch window before code from other modules is executed
    patchWindow();

    // - Mount the main UI component
    whenReady(() => {
        const container = document.createElement("hoot-container");
        container.style.display = "contents";
        document.body.appendChild(container);

        mount(HootMain, container.shadowRoot, {
            // TODO <<< remove when lib is stable
            dev: true,
            warnIfNoStaticProps: true,
            // TODO >>>
            env: {
                runner,
                ui: makeUiState(),
            },
            name: "HOOT",
        });
    });
}
