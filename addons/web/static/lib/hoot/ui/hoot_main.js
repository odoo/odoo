/** @odoo-module */

import { Component, onMounted, useRef, useState, xml } from "@odoo/owl";
import { createURL } from "../core/url";
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
            Running in headless mode
            <a class="text-primary hoot-link" t-att-href="createURL({ headless: null })">
                Run with UI
            </a>
        </t>
        <t t-else="">
            <main
                t-ref="root"
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

    createURL = createURL;
    escapeKeyPresses = 0;

    setup() {
        const { runner } = this.env;
        this.state = useState({
            debugTest: null,
        });

        if (!runner.config.headless) {
            // Since Chrome 125 and for God knows why the "pointer" event listeners
            // are all ignored in the HOOT UI, so the buttons appearing on hover
            // are never displayed.
            //
            // Now for some reason adding a SINGLE listener on ANY button seems
            // to solve this issue. I've looked into it for hours already and this
            // is as far as I'll go on this matter. Good luck to anyone trying to
            // debug this mess.
            const unstuckListeners = () => {
                if (listenersUnstuck || !rootRef.el) {
                    return;
                }
                listenersUnstuck = true;
                rootRef.el.querySelector("button").addEventListener(
                    "pointerenter",
                    () => {
                        // Leave this empty (CALLBACK CANNOT BE NULL OR UNDEFINED)
                    },
                    { once: true }
                );
            };

            const rootRef = useRef("root");
            let listenersUnstuck = false;

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

                unstuckListeners();
            });

            onMounted(unstuckListeners);
            useWindowListener("keydown", (ev) => this.onWindowKeyDown(ev), { capture: true });
        }
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
}
