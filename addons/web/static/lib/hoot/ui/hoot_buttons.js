/** @odoo-module */

import { Component, signal, types as t, xml } from "@odoo/owl";
import { refresh } from "../core/url";
import { STORAGE, storageSet } from "../hoot_utils";
import { HootLink } from "./hoot_link";
import { getConfigPlugin, getRunnerPlugin } from "./runner_plugin";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { clearTimeout, setTimeout } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const DISABLE_TIMEOUT = 500;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class HootButtons extends Component {
    static components = { HootLink };
    static template = xml`
        <t t-set="isRunning" t-value="this.runner.status() === 'running'" />
        <t t-set="showAll" t-value="this.runner.hasRemovableFilter" />
        <t t-set="showFailed" t-value="this.runner.failedIds().size" />
        <div
            class="${HootButtons.name} relative"
            t-on-pointerenter="this.onPointerEnter"
            t-on-pointerleave="this.onPointerLeave"
        >
            <div class="flex rounded gap-px overflow-hidden">
            <button
                type="button"
                class="flex items-center bg-btn gap-2 px-2 py-1 transition-colors"
                t-on-click.stop="this.onRunClick"
                t-att-title="isRunning ? 'Stop (Esc)' : 'Run'"
                t-att-disabled="this.isDisabled()"
            >
                <i t-attf-class="fa fa-{{ isRunning ? 'stop' : 'play' }}" />
                <span t-out="isRunning ? 'Stop' : 'Run'" />
            </button>
            <t t-if="showAll or showFailed">
                <button
                    type="button"
                    class="bg-btn px-2 py-1 transition-colors animate-slide-left"
                    t-on-click.stop="this.onToggleClick"
                >
                    <i class="fa fa-caret-down transition" t-att-class="{ 'rotate-180': this.isOpen() }" />
                </button>
            </t>
            </div>
            <t t-if="this.isOpen()">
                <div
                    class="
                        w-fit absolute animate-slide-down
                        flex flex-col end-0
                        bg-base text-base shadow rounded z-2"
                >
                    <t t-if="showAll">
                        <HootLink
                            class="'p-3 whitespace-nowrap transition-colors hover:bg-gray-300 dark:hover:bg-gray-700'"
                            title="'Run all tests'"
                        >
                            Run <strong class="text-primary">all</strong> tests
                        </HootLink>
                    </t>
                    <t t-if="showFailed">
                        <HootLink
                            class="'p-3 whitespace-nowrap transition-colors hover:bg-gray-300 dark:hover:bg-gray-700'"
                            title="'Run failed tests'"
                            ids="{ id: this.runner.failedIds() }"
                            onClick="this.onRunFailedClick"
                        >
                            Run <strong class="text-rose">failed</strong> tests
                        </HootLink>
                        <HootLink
                            class="'p-3 whitespace-nowrap transition-colors hover:bg-gray-300 dark:hover:bg-gray-700'"
                            title="'Run failed suites'"
                            ids="{ id: this.getFailedSuiteIds() }"
                            onClick="this.onRunFailedClick"
                        >
                            Run <strong class="text-rose">failed</strong> suites
                        </HootLink>
                    </t>
                </div>
            </t>
        </div>
    `;

    // Props & plugins
    config = getConfigPlugin();
    runner = getRunnerPlugin();

    // Reactive values
    isDisabled = signal(false, { type: t.boolean() });
    isOpen = signal(false, { type: t.boolean() });

    // Other members
    disableTimeout = 0;

    getFailedSuiteIds() {
        const { tests } = this.runner;
        const suiteIds = [];
        for (const id of this.runner.failedIds()) {
            const test = tests.get(id);
            if (test && !suiteIds.includes(test.parent.id)) {
                suiteIds.push(test.parent.id);
            }
        }
        return suiteIds;
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerLeave(ev) {
        if (ev.pointerType !== "mouse") {
            return;
        }
        this.isOpen.set(false);
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerEnter(ev) {
        if (ev.pointerType !== "mouse") {
            return;
        }
        if (!this.isRunning) {
            this.isOpen.set(true);
        }
    }

    onRunClick() {
        switch (this.runner.status()) {
            case "done": {
                refresh();
                break;
            }
            case "ready": {
                if (this.config.manual()) {
                    this.runner.manualStart();
                } else {
                    refresh();
                }
                break;
            }
            case "running": {
                this.runner.stop();
                if (this.disableTimeout) {
                    clearTimeout(this.disableTimeout);
                }
                this.isDisabled.set(true);
                this.disableTimeout = setTimeout(() => this.isDisabled.set(false), DISABLE_TIMEOUT);
                break;
            }
        }
    }

    onRunFailedClick() {
        storageSet(STORAGE.failed, []);
    }

    onToggleClick() {
        this.isOpen.set(!this.isOpen());
    }
}
