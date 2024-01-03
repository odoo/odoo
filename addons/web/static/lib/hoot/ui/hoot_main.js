/** @odoo-module */

import { Component, useSubEnv, xml } from "@odoo/owl";
import { createURL, setParams, urlParams } from "../core/url";
import { useWindowListener } from "../hoot_utils";
import { HootButtons } from "./hoot_buttons";
import { HootConfigDropdown } from "./hoot_config_dropdown";
import { HootReporting } from "./hoot_reporting";
import { HootSearch } from "./hoot_search";
import { HootSideBar } from "./hoot_side_bar";
import { HootStatusPanel } from "./hoot_status_panel";

/**
 * @typedef {{
 * }} HootMainProps
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootMainProps, import("../hoot").Environment>} */
export class HootMain extends Component {
    static components = {
        HootButtons,
        HootConfigDropdown,
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
            <main class="${HootMain.name} flex flex-col w-full h-full bg-base relative" t-att-class="{ 'hoot-animations': env.runner.config.fun }">
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
                        <HootConfigDropdown />
                    </nav>
                </header>
                <HootStatusPanel />
                <div class="flex h-full overflow-y-auto">
                    <HootSideBar />
                    <HootReporting />
                </div>
            </main>
        </t>
    `;

    createURL = createURL;

    setup() {
        const { runner } = this.env;

        useSubEnv({ runner });

        if (!runner.config.headless) {
            useWindowListener("keydown", this.onWindowKeyDown, { capture: true });
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeyDown(ev) {
        if (!ev.isTrusted) {
            return;
        }
        const { runner } = this.env;
        switch (ev.key) {
            case "d": {
                if (ev.altKey) {
                    ev.preventDefault();
                    setParams({ debugTest: !urlParams.debugTest });
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
                if (runner.state.status === "running") {
                    ev.preventDefault();
                    runner.stop();
                }
                break;
            }
        }
    }
}
