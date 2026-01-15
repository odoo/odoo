/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { createUrl, refresh } from "../core/url";
import { callHootKey, useHootKey, useWindowListener } from "../hoot_utils";
import { HootButtons } from "./hoot_buttons";
import { HootConfigMenu } from "./hoot_config_menu";
import { HootDebugToolBar } from "./hoot_debug_toolbar";
import { HootDropdown } from "./hoot_dropdown";
import { HootReporting } from "./hoot_reporting";
import { HootSearch } from "./hoot_search";
import { HootSideBar } from "./hoot_side_bar";
import { HootStatusPanel } from "./hoot_status_panel";

/**
 * @typedef {{
 * }} HootMainProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { setTimeout } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

// Indenpendant from Hoot style classes since it is not loaded in headless
const HEADLESS_CONTAINER_STYLE = [
    "position: absolute",
    "bottom: 0",
    "inset-inline-start: 50%",
    "transform: translateX(-50%)",
    "display: flex",
    "z-index: 4",
    "margin-bottom: 1rem",
    "padding-left: 1rem",
    "padding-right: 1rem",
    "padding-top: 0.5rem",
    "padding-bottom: 0.5rem",
    "gap: 0.5rem",
    "white-space: nowrap",
    "border-radius: 9999px",
    "box-shadow: 2px 1px 5px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)",
    "background-color: #e2e8f0",
].join(";");
const HEADLESS_LINK_STYLE = ["color: #714b67", "text-decoration: underline"].join(";");

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootMainProps, import("../hoot").Environment>} */
export class HootMain extends Component {
    static components = {
        HootButtons,
        HootConfigMenu,
        HootDebugToolBar,
        HootDropdown,
        HootReporting,
        HootSearch,
        HootSideBar,
        HootStatusPanel,
    };

    static props = {};

    static template = xml`
        <t t-if="env.runner.headless">
            <div style="${HEADLESS_CONTAINER_STYLE}">
                Running in headless mode
                <a style="${HEADLESS_LINK_STYLE}" t-att-href="createUrl({ headless: null })">
                    Run with UI
                </a>
            </div>
        </t>
        <t t-else="">
            <main
                class="${HootMain.name} flex flex-col w-full h-full bg-base relative"
                t-att-class="{ 'hoot-animations': env.runner.config.fun }"
            >
                <header class="flex flex-col bg-gray-200 dark:bg-gray-800">
                    <nav class="hoot-controls py-1 px-2">
                        <h1
                            class="hoot-logo m-0 select-none"
                            title="Hierarchically Organized Odoo Tests"
                        >
                            <strong class="flex">HOOT</strong>
                        </h1>
                        <HootButtons />
                        <HootSearch />
                        <HootDropdown buttonClassName="'bg-btn'">
                            <t t-set-slot="toggler" t-slot-scope="dropdownState">
                                <i class="fa fa-cog transition" t-att-class="{ 'rotate-90': dropdownState.open }" />
                            </t>
                            <t t-set-slot="menu">
                                <HootConfigMenu />
                            </t>
                        </HootDropdown>
                    </nav>
                </header>
                <HootStatusPanel />
                <div class="flex h-full overflow-y-auto">
                    <HootSideBar />
                    <HootReporting />
                </div>
            </main>
            <t t-if="state.debugTest">
                <HootDebugToolBar test="state.debugTest" />
            </t>
        </t>
    `;

    createUrl = createUrl;
    escapeKeyPresses = 0;

    setup() {
        const { runner } = this.env;
        this.state = useState({
            debugTest: null,
        });

        runner.beforeAll(() => {
            if (!runner.debug) {
                return;
            }
            if (runner.debug === true) {
                this.state.debugTest = runner.state.tests[0];
            } else {
                this.state.debugTest = runner.debug;
            }
        });
        runner.afterAll(() => {
            this.state.debugTest = null;
        });

        useWindowListener("resize", (ev) => this.onWindowResize(ev));
        useWindowListener("keydown", callHootKey, { capture: true });
        useHootKey(["Enter"], this.manualStart);
        useHootKey(["Escape"], this.abort);

        if (!runner.config.headless) {
            useHootKey(["Alt", "d"], this.toggleDebug);
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    abort(ev) {
        const { runner } = this.env;
        this.escapeKeyPresses++;
        setTimeout(() => this.escapeKeyPresses--, 500);

        if (runner.state.status === "running" && this.escapeKeyPresses >= 2) {
            ev.preventDefault();
            runner.stop();
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    manualStart(ev) {
        const { runner } = this.env;
        if (runner.state.status !== "ready") {
            return;
        }

        ev.preventDefault();

        if (runner.config.manual) {
            runner.manualStart();
        } else {
            refresh();
        }
    }

    onWindowResize() {
        this.env.runner.checkPresetForViewPort();
    }

    /**
     * @param {KeyboardEvent} ev
     */
    toggleDebug(ev) {
        ev.preventDefault();

        const { runner } = this.env;
        runner.config.debugTest = !runner.config.debugTest;
    }
}
