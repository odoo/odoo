/** @odoo-module */

import { Component, useRef, useState, xml } from "@odoo/owl";
import { refresh } from "../core/url";
import { useWindowListener } from "../hoot_utils";
import { MockMath, generateSeed, internalRandom } from "../mock/math";
import { toggleColorScheme, useColorScheme } from "./hoot_colors";
import { HootCopyButton } from "./hoot_copy_button";

/**
 * @typedef {"dark" | "light"} ColorScheme
 *
 * @typedef {{
 * }} HootConfigDropdownProps
 */

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootConfigDropdownProps, import("../hoot").Environment>} */
export class HootConfigDropdown extends Component {
    static components = { HootCopyButton };

    static props = {};

    static template = xml`
        <div class="${HootConfigDropdown.name}" t-ref="root">
            <button
                t-ref="toggler"
                class="flex bg-btn rounded p-2 transition-colors"
                title="Configuration"
            >
                <i class="fa fa-cog" />
            </button>
            <t t-if="state.open">
                <form
                    class="hoot-config-dropdown animate-slide-down bg-base text-base mt-1 absolute flex flex-col end-0 px-2 py-3 shadow rounded shadow z-10"
                    t-on-submit.prevent="refresh"
                >
                    <label
                        class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Shuffles tests and suites order within their parent suite"
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-att-checked="config.random"
                            t-on-change="onRandomChange"
                        />
                        <span>Random order</span>
                    </label>
                    <t t-if="config.random">
                        <small class="flex items-center p-1 pt-0 gap-1">
                            <span class="text-muted whitespace-nowrap ms-1">Seed:</span>
                            <input
                                type="text"
                                class="w-full outline-none border-b border-primary px-1 w-full"
                                t-model.number="config.random"
                            />
                            <button
                                type="button"
                                title="Generate new random seed"
                                t-on-click="resetSeed"
                            >
                                <i class="fa fa-repeat" />
                            </button>
                            <HootCopyButton text="config.random.toString()" />
                        </small>
                    </t>
                    <label
                        class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Re-run current tests in headless mode (no UI)"
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-model="config.headless"
                        />
                        <span>Headless</span>
                    </label>
                    <label
                        class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Re-run current tests and abort after a given amount of failed tests"
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-att-checked="config.bail"
                            t-on-change="onBailChange"
                        />
                        <span>Bail</span>
                    </label>
                    <t t-if="config.bail">
                        <small class="flex items-center p-1 pt-0 gap-1">
                            <span class="text-muted whitespace-nowrap ms-1">Failed tests:</span>
                            <input
                                type="number"
                                class="outline-none w-full border-b border-primary px-1"
                                t-model.number="config.bail"
                            />
                        </small>
                    </t>
                    <label
                        class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Re-run current tests without catching any errors"
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-model="config.notrycatch"
                        />
                        <span>No try/catch</span>
                    </label>
                    <label
                        class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title='Activates "incentives" to help you stay motivated'
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-model="config.fun"
                        />
                        <span>Enable incentives</span>
                    </label>
                    <label
                        class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Checks keys on global objects after each test"
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-model="config.watchkeys"
                        />
                        <span>Watch global keys</span>
                    </label>
                    <t t-if="config.watchkeys">
                        <small class="flex items-center p-1 pt-0 gap-1">
                            <span class="text-muted whitespace-nowrap ms-1">Keys:</span>
                            <input
                                type="text"
                                class="w-full outline-none border-b border-primary px-1 w-full"
                                t-model.number="config.watchkeys"
                            />
                        </small>
                    </t>

                    <button
                        type="button"
                        class="p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Toggle the color scheme of the UI"
                        t-on-click="toggleColorScheme"
                    >
                        <i t-attf-class="fa fa-{{ color.scheme === 'light' ? 'moon' : 'sun' }}-o" />
                        Color scheme
                    </button>

                    <button class="flex bg-btn justify-center rounded mt-1 p-1 transition-colors">
                        Apply and refresh
                    </button>
                </form>
            </t>
        </div>
    `;

    refresh = refresh;
    toggleColorScheme = toggleColorScheme;

    setup() {
        this.rootRef = useRef("root");
        this.togglerRef = useRef("toggler");

        this.color = useColorScheme();
        this.config = useState(this.env.runner.config);
        this.state = useState({ open: false });

        useWindowListener("keydown", (ev) => {
            if (this.state.open && ev.key === "Escape") {
                ev.preventDefault();
                this.state.open = false;
            }
        });
        useWindowListener("click", (ev) => {
            const path = ev.composedPath();
            if (!path.includes(this.rootRef.el)) {
                this.state.open = false;
            } else if (path.includes(this.togglerRef.el)) {
                this.state.open = !this.state.open;
            }
        });
    }

    onBailChange(ev) {
        this.config.bail = ev.target.checked ? 1 : 0;
    }

    onRandomChange(ev) {
        if (ev.target.checked) {
            this.resetSeed();
        } else {
            this.config.random = 0;
        }
    }

    resetSeed() {
        this.config.random = generateSeed();
        internalRandom.seed = this.config.random;
        MockMath.random.seed = this.config.random;
    }
}
