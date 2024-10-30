/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { createUrl } from "../core/url";
import { useWindowListener } from "../hoot_utils";
import { HootButtons } from "./hoot_buttons";
import { HootConfigDropdown } from "./hoot_config_dropdown";
import { HootDebugToolBar } from "./hoot_debug_toolbar";
import { HootPresets } from "./hoot_presets";
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
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootMainProps, import("../hoot").Environment>} */
export class HootMain extends Component {
    static components = {
        HootButtons,
        HootConfigDropdown,
        HootDebugToolBar,
        HootPresets,
        HootReporting,
        HootSearch,
        HootSideBar,
        HootStatusPanel,
    };

    static props = {};

    static template = xml`
        <t t-if="env.runner.config.headless">
            <div class="absolute bottom-0 start-1/2 -translate-x-1/2
                flex z-4 mb-4 px-4 py-2 gap-2 whitespace-nowrap
                text-xl rounded-full shadow bg-gray-200 dark:bg-gray-800"
            >
                Running in headless mode
                <a class="text-primary hoot-link" t-att-href="createUrl({ headless: null })">
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
                        <div class="flex gap-1">
                            <HootPresets />
                            <HootConfigDropdown />
                        </div>
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

        useWindowListener("keydown", (ev) => this.onWindowKeyDown(ev));
        useWindowListener("resize", (ev) => this.onWindowResize(ev));
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeyDown(ev) {
        const { runner } = this.env;
        switch (ev.key) {
            case "d": {
                if (ev.altKey) {
                    ev.preventDefault();
                    runner.config.debugTest = !runner.config.debugTest;
                }
                break;
            }
            case "Enter": {
                if (runner.state.status === "ready") {
                    ev.preventDefault();
                    runner.start();
                }
                break;
            }
            case "Escape": {
                this.escapeKeyPresses++;
                setTimeout(() => this.escapeKeyPresses--, 500);

                if (ev.ctrlKey && runner.config.debugTest) {
                    runner.config.debugTest = false;
                }
                if (runner.state.status === "running" && this.escapeKeyPresses >= 2) {
                    ev.preventDefault();
                    runner.stop();
                }
                break;
            }
        }
    }

    onWindowResize() {
        this.env.runner.checkPresetForViewPort();
    }
}
