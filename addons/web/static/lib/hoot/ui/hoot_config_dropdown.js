/** @odoo-module */

import { Component, useRef, useState, xml } from "@odoo/owl";
import { logLevels } from "../core/logger";
import { refresh } from "../core/url";
import { useAutofocus, useWindowListener } from "../hoot_utils";
import { generateSeed, internalRandom } from "../mock/math";
import { toggleColorScheme, useColorScheme } from "./hoot_colors";
import { HootCopyButton } from "./hoot_copy_button";

/**
 * @typedef {"dark" | "light"} ColorScheme
 *
 * @typedef {{
 * }} HootConfigDropdownProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { entries: $entries },
} = globalThis;

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
                <i class="fa fa-cog transition" t-att-class="{ 'rotate-90': state.open }" />
            </button>
            <t t-if="state.open">
                <form
                    class="hoot-dropdown animate-slide-down bg-base text-base mt-1 absolute flex flex-col end-0 px-2 py-3 shadow rounded shadow z-2"
                    t-on-submit.prevent="refresh"
                >
                    <div
                        class="flex items-center gap-1"
                        title="Determines the order of the tests execution"
                    >
                        <span class="p-1 me-auto">Execution order</span>
                        <t t-foreach="executionOrders" t-as="order" t-key="order.value">
                            <button
                                type="button"
                                class="px-1 transition-colors"
                                t-att-class="{ 'border rounded text-primary border-primary': config.order === order.value }"
                                t-att-title="order.title"
                                t-on-click.stop="() => this.setExecutionOrder(order.value)"
                            >
                                <i class="fa transition" t-att-class="{ [order.icon]: true }"/>
                            </button>
                        </t>
                    </div>
                    <label
                        class="flex items-center gap-3 p-1 mb-1"
                        title="Sets test timeout value (in milliseconds)"
                    >
                        <span>Timeout</span>
                        <input
                            type="text"
                            class="outline-none border-b border-primary px-1 w-full"
                            t-model.number="config.timeout"
                        />
                    </label>
                    <label
                        class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Sets the seed of the random generator"
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-att-checked="config.random"
                            t-on-change="onRandomChange"
                        />
                        <span>Random seed</span>
                    </label>
                    <t t-if="config.random">
                        <small class="flex items-center p-1 pt-0 gap-1">
                            <span class="text-muted whitespace-nowrap ms-1">Seed:</span>
                            <input
                                type="text"
                                autofocus=""
                                class="w-full outline-none border-b border-primary px-1"
                                t-model.number="config.random"
                            />
                            <button
                                type="button"
                                title="Generate new random seed"
                                t-on-click.stop="resetSeed"
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
                        title="Awaits user input before running the tests"
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-model="config.manual"
                        />
                        <span>Manual</span>
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
                                type="text"
                                autofocus=""
                                class="outline-none w-full border-b border-primary px-1"
                                t-model.number="config.bail"
                            />
                        </small>
                    </t>
                    <label
                        class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Controls the verbosity of the logs"
                    >
                        <input
                            type="checkbox"
                            class="appearance-none border border-primary rounded-sm w-4 h-4"
                            t-att-checked="config.loglevel"
                            t-on-change="onLogLevelChange"
                        />
                        <span>Log level</span>
                    </label>
                    <t t-if="config.loglevel">
                        <small class="flex items-center p-1 pt-0 gap-1">
                            <span class="text-muted whitespace-nowrap ms-1">Level:</span>
                            <select
                                autofocus=""
                                class="outline-none w-full bg-base text-base border-b border-primary px-1"
                                t-model.number="config.loglevel"
                            >
                                <t t-foreach="logLevels" t-as="level" t-key="level.value">
                                    <option
                                        t-att-value="level.value"
                                        t-esc="level.label"
                                    />
                                </t>
                            </select>
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

                    <button
                        type="button"
                        class="p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                        title="Toggle the color scheme of the UI"
                        t-on-click.stop="toggleColorScheme"
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

    executionOrders = [
        { value: "fifo", title: "First in, first out", icon: "fa-sort-numeric-asc" },
        { value: "lifo", title: "Last in, first out", icon: "fa-sort-numeric-desc" },
        { value: "random", title: "Random", icon: "fa-random" },
    ];
    logLevels = $entries(logLevels)
        .filter(([, value]) => value)
        .map(([label, value]) => ({ label, value }));

    refresh = refresh;
    toggleColorScheme = toggleColorScheme;

    setup() {
        this.rootRef = useRef("root");
        this.togglerRef = useRef("toggler");

        this.color = useColorScheme();
        this.config = useState(this.env.runner.config);
        this.state = useState({ open: false });

        useAutofocus(this.rootRef);
        useWindowListener("keydown", (ev) => {
            if (this.state.open && ev.key === "Escape") {
                ev.preventDefault();
                this.state.open = false;
            }
        });
        useWindowListener(
            "click",
            (ev) => {
                const path = ev.composedPath();
                if (!path.includes(this.rootRef.el)) {
                    this.state.open = false;
                } else if (path.includes(this.togglerRef.el)) {
                    this.state.open = !this.state.open;
                }
            },
            { capture: true }
        );
    }

    /**
     * @param {Event & { currentTarget: HTMLInputElement }} ev
     */
    onBailChange(ev) {
        this.config.bail = ev.currentTarget.checked ? 1 : 0;
    }

    /**
     * @param {Event & { currentTarget: HTMLInputElement }} ev
     */
    onLogLevelChange(ev) {
        this.config.loglevel = ev.currentTarget.checked ? logLevels.SUITES : logLevels.RUNNER;
    }

    /**
     * @param {Event & { currentTarget: HTMLInputElement }} ev
     */
    onRandomChange(ev) {
        if (ev.currentTarget.checked) {
            this.resetSeed();
        } else {
            this.config.random = 0;
        }
    }

    resetSeed() {
        const newSeed = generateSeed();
        this.config.random = newSeed;
        internalRandom.seed = newSeed;
    }

    /**
     * @param {"fifo" | "lifo" | "random"} order
     */
    setExecutionOrder(order) {
        this.config.order = order;
    }
}
