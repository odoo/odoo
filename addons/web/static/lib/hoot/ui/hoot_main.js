/** @odoo-module */

import { Component, onMounted, useExternalListener, useSubEnv, xml } from "@odoo/owl";
import { createURL, setParams, urlParams } from "../core/url";
import { HootButtons } from "./hoot_buttons";
import { HootConfigDropdown } from "./hoot_config_dropdown";
import { HootReporting } from "./hoot_reporting";
import { HootSearch } from "./hoot_search";

/**
 * @typedef {{}} HootMainProps
 */

/** @extends Component<HootMainProps, import("../hoot").Environment> */
export class HootMain extends Component {
    static components = {
        HootConfigDropdown,
        HootButtons,
        HootSearch,
        HootReporting,
    };

    static props = {};

    static template = xml`
        <t t-if="env.runner.config.headless">
            Running in headless mode
            <a t-att-href="createURL({ headless: null })">
                Run with UI
            </a>
        </t>
        <t t-else="">
            <main class="hoot d-flex flex-column mh-100" t-att-class="{ 'hoot-animations': env.runner.config.fun }">
                <header class="hoot-panel d-flex flex-column">
                    <nav class="hoot-controls py-1 px-2">
                        <h1 class="hoot-logo hoot-text-primary m-0 user-select-none" title="Hierarchically Organized Odoo Tests">
                            <strong class="d-flex">HOOT</strong>
                        </h1>
                        <HootButtons />
                        <HootSearch />
                        <HootConfigDropdown />
                    </nav>
                </header>
                <HootReporting />
            </main>
        </t>
    `;

    createURL = createURL;

    setup() {
        const { runner } = this.env;

        useSubEnv({ runner });

        if (!runner.config.headless) {
            useExternalListener(window, "keydown", (ev) => this.onWindowKeyDown(ev), {
                capture: true,
            });
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
                if (runner.status === "ready") {
                    ev.preventDefault();
                    runner.start();
                }
                break;
            }
            case "Escape": {
                if (runner.status === "running") {
                    ev.preventDefault();
                    runner.stop();
                }
                break;
            }
        }
    }
}
