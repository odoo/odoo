/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { CONFIG_KEYS } from "../core/config";
import { LOG_LEVELS } from "../core/logger";
import { refresh } from "../core/url";
import { CASE_EVENT_TYPES, strictEqual } from "../hoot_utils";
import { generateSeed, internalRandom } from "../mock/math";
import { toggleColorScheme, useColorScheme } from "./hoot_colors";
import { HootCopyButton } from "./hoot_copy_button";

/**
 * @typedef {"dark" | "light"} ColorScheme
 *
 * @typedef {{
 * }} HootConfigMenuProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { entries: $entries, keys: $keys, values: $values },
} = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootConfigMenuProps, import("../hoot").Environment>} */
export class HootConfigMenu extends Component {
    static components = { HootCopyButton };
    static props = {};
    static template = xml`
        <form class="contents" t-on-submit.prevent="refresh">
            <h3 class="pb-1 border-b text-gray border-gray">Behavior</h3>
            <t t-if="hasPresets()">
                <div class="flex items-center gap-1">
                    <t t-set="hasCorrectViewPort" t-value="env.runner.checkPresetForViewPort()" />
                    <t t-set="highlightClass" t-value="hasCorrectViewPort ? 'text-primary' : 'text-amber'" />
                    <span class="me-auto">Preset</span>
                    <t t-foreach="env.runner.presets" t-as="presetKey" t-key="presetKey">
                        <t t-set="preset" t-value="env.runner.presets[presetKey]" />
                        <button
                            type="button"
                            class="border rounded transition-colors hover:bg-gray-300 dark:hover:bg-gray-700"
                            t-att-class="{ ['border-primary ' + highlightClass]: config.preset === presetKey }"
                            t-att-title="presetKey ? preset.label : 'No preset'"
                            t-on-click.stop="() => this.onPresetChange(presetKey)"
                        >
                            <i t-attf-class="fa w-5 h-5 {{ preset.icon or 'fa-ban' }}" />
                        </button>
                    </t>
                </div>
            </t>
            <div
                class="flex items-center gap-1"
                title="Determines the order of the tests execution"
            >
                <span class="me-auto">Execution order</span>
                <t t-foreach="executionOrders" t-as="order" t-key="order.value">
                    <button
                        type="button"
                        class="border rounded transition-colors hover:bg-gray-300 dark:hover:bg-gray-700"
                        t-att-class="{ 'text-primary border-primary': config.order === order.value }"
                        t-att-title="order.title"
                        t-on-click.stop="() => this.setExecutionOrder(order.value)"
                    >
                        <i class="fa w-5 h-5" t-att-class="{ [order.icon]: true }"/>
                    </button>
                </t>
            </div>
            <t t-if="config.order === 'random'">
                <small class="flex items-center p-1 pt-0 gap-1">
                    <span class="text-gray whitespace-nowrap ms-1">Seed:</span>
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
                class="flex items-center gap-3"
                title="Sets test timeout value (in milliseconds)"
            >
                <span class="shrink-0">Test timeout</span>
                <input
                    type="text"
                    class="outline-none border-b border-primary px-1 w-full"
                    t-model.number="config.timeout"
                />
            </label>
            <label
                class="flex items-center gap-3"
                title="Sets network delay (in milliseconds)"
            >
                <span class="shrink-0">Network delay</span>
                <input
                    type="text"
                    class="outline-none border-b border-primary px-1 w-full"
                    t-model="config.networkDelay"
                />
            </label>
            <label
                class="cursor-pointer flex items-center gap-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                title="Awaits user input before running the tests"
            >
                <input
                    type="checkbox"
                    class="appearance-none border border-primary rounded-sm w-4 h-4"
                    t-model="config.manual"
                />
                <span>Run tests manually</span>
            </label>
            <label
                class="cursor-pointer flex items-center gap-1 hover:bg-gray-300 dark:hover:bg-gray-700"
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
                    <span class="text-gray whitespace-nowrap ms-1">Failed tests:</span>
                    <input
                        type="text"
                        autofocus=""
                        class="outline-none w-full border-b border-primary px-1"
                        t-model.number="config.bail"
                    />
                </small>
            </t>
            <label
                class="cursor-pointer flex items-center gap-1 hover:bg-gray-300 dark:hover:bg-gray-700"
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
                    <span class="text-gray whitespace-nowrap ms-1">Level:</span>
                    <select
                        autofocus=""
                        class="outline-none w-full bg-base text-base border-b border-primary px-1"
                        t-model.number="config.loglevel"
                    >
                        <t t-foreach="LOG_LEVELS" t-as="level" t-key="level.value">
                            <option
                                t-att-value="level.value"
                                t-esc="level.label"
                            />
                        </t>
                    </select>
                </small>
            </t>
            <label
                class="cursor-pointer flex items-center gap-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                title="Re-run current tests without catching any errors"
            >
                <input
                    type="checkbox"
                    class="appearance-none border border-primary rounded-sm w-4 h-4"
                    t-model="config.notrycatch"
                />
                <span>No try/catch</span>
            </label>

            <!-- Display -->
            <h3 class="mt-2 pb-1 border-b text-gray border-gray">Display</h3>
            <div class="flex items-center gap-1">
                <span class="me-auto">Events</span>
                <t t-foreach="CASE_EVENT_TYPES" t-as="sType" t-key="sType">
                    <t t-set="isDisplayed" t-value="isEventDisplayed(sType)" />
                    <t t-set="eventColor" t-value="isDisplayed ? CASE_EVENT_TYPES[sType].color : 'gray'" />
                    <button
                        type="button"
                        t-attf-class="p-1 border-b-2 transition-color text-{{ eventColor }} border-{{ eventColor }}"
                        t-attf-title="{{ isDisplayed ? 'Hide' : 'Show' }} {{ sType }} events"
                        t-on-click.stop="(ev) => this.toggleEventType(ev, sType)"
                    >
                        <i class="fa" t-att-class="CASE_EVENT_TYPES[sType].icon" />
                    </button>
                </t>
            </div>
            <button
                type="button"
                class="flex items-center gap-1"
                t-on-click.stop="toggleSortResults"
            >
                <span class="me-auto">Sort by duration</span>
                <span
                    class="flex items-center gap-1 transition-colors"
                    t-att-class="{ 'text-primary': uiState.sortResults }"
                >
                    <t t-if="uiState.sortResults === 'asc'">
                        ascending
                    </t>
                    <t t-elif="uiState.sortResults === 'desc'">
                        descending
                    </t>
                    <t t-else="">
                        none
                    </t>
                    <i t-attf-class="fa fa-sort-numeric-{{ uiState.sortResults or 'desc' }}" />
                </span>
            </button>
            <label
                class="cursor-pointer flex items-center gap-1 hover:bg-gray-300 dark:hover:bg-gray-700"
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
                class="cursor-pointer flex items-center gap-1 hover:bg-gray-300 dark:hover:bg-gray-700"
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
                class="flex items-center gap-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                title="Toggle the color scheme of the UI"
                t-on-click.stop="toggleColorScheme"
            >
                <i t-attf-class="fa fa-{{ color.scheme === 'light' ? 'moon' : 'sun' }}-o w-4 h-4" />
                Color scheme
            </button>

            <!-- Refresh button -->
            <button
                class="flex bg-btn justify-center rounded mt-1 p-1 transition-colors"
                t-att-disabled="doesNotNeedRefresh()"
            >
                Apply and refresh
            </button>
        </form>
    `;

    CASE_EVENT_TYPES = CASE_EVENT_TYPES;

    executionOrders = [
        { value: "fifo", title: "First in, first out", icon: "fa-sort-numeric-asc" },
        { value: "lifo", title: "Last in, first out", icon: "fa-sort-numeric-desc" },
        { value: "random", title: "Random", icon: "fa-random" },
    ];
    LOG_LEVELS = $entries(LOG_LEVELS)
        .filter(([, value]) => value)
        .map(([label, value]) => ({ label, value }));

    refresh = refresh;
    toggleColorScheme = toggleColorScheme;

    setup() {
        const { runner, ui } = this.env;
        this.color = useColorScheme();
        this.config = useState(runner.config);
        this.uiState = useState(ui);
    }

    doesNotNeedRefresh() {
        return CONFIG_KEYS.every((key) =>
            strictEqual(this.config[key], this.env.runner.initialConfig[key])
        );
    }

    hasPresets() {
        return $keys(this.env.runner.presets).filter(Boolean).length > 0;
    }

    /**
     * @param {keyof CASE_EVENT_TYPES} sType
     */
    isEventDisplayed(sType) {
        return this.config.events & CASE_EVENT_TYPES[sType].value;
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
        this.config.loglevel = ev.currentTarget.checked ? LOG_LEVELS.suites : LOG_LEVELS.runner;
    }

    /**
     * @param {string} presetId
     */
    onPresetChange(presetId) {
        this.config.preset = this.config.preset === presetId ? "" : presetId;
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

        if (order === "random" && !this.config.random) {
            this.resetSeed();
        } else if (this.config.random) {
            this.config.random = 0;
        }
    }

    /**
     * @param {PointerEvent} ev
     * @param {import("../core/expect").CaseEventType} sType
     */
    toggleEventType(ev, sType) {
        const nType = CASE_EVENT_TYPES[sType].value;
        if (this.config.events & nType) {
            if (ev.altKey) {
                this.config.events = 0;
            } else {
                this.config.events &= ~nType;
            }
        } else {
            if (ev.altKey) {
                // Aggregate all event types
                this.config.events = $values(CASE_EVENT_TYPES).reduce((acc, t) => acc + t.value, 0);
            } else {
                this.config.events |= nType;
            }
        }
    }

    toggleSortResults() {
        this.uiState.resultsPage = 0;
        if (!this.uiState.sortResults) {
            this.uiState.sortResults = "desc";
        } else if (this.uiState.sortResults === "desc") {
            this.uiState.sortResults = "asc";
        } else {
            this.uiState.sortResults = false;
        }
    }
}
