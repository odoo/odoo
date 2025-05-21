/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { refresh, subscribeToURLParams } from "../core/url";
import { STORAGE, storageSet } from "../hoot_utils";
import { HootLink } from "./hoot_link";

/**
 * @typedef {{
 * }} HootButtonsProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    clearTimeout,
    Object: { keys: $keys },
    setTimeout,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const DISABLE_TIMEOUT = 500;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootButtonsProps, import("../hoot").Environment>} */
export class HootButtons extends Component {
    static components = { HootLink };

    static props = {};

    static template = xml`
        <t t-set="isRunning" t-value="runnerState.status === 'running'" />
        <t t-set="showAll" t-value="env.runner.hasFilter" />
        <t t-set="showFailed" t-value="runnerState.failedIds.size" />
        <t t-set="failedSuites" t-value="getFailedSuiteIds()" />
        <div
            class="${HootButtons.name} relative"
            t-on-pointerenter="onPointerEnter"
            t-on-pointerleave="onPointerLeave"
        >
            <div class="flex rounded gap-px overflow-hidden">
            <button
                type="button"
                class="flex items-center bg-btn gap-2 px-2 py-1 transition-colors"
                t-on-click.stop="onRunClick"
                t-att-title="isRunning ? 'Stop (Esc)' : 'Run'"
                t-att-disabled="state.disable"
            >
                <i t-attf-class="fa fa-{{ isRunning ? 'stop' : 'play' }}" />
                <span t-esc="isRunning ? 'Stop' : 'Run'" />
            </button>
            <t t-if="showAll or showFailed">
                <button
                    type="button"
                    class="bg-btn px-2 py-1 transition-colors animate-slide-left"
                    t-on-click.stop="onToggleClick"
                >
                    <i class="fa fa-caret-down transition" t-att-class="{ 'rotate-180': state.open }" />
                </button>
            </t>
            </div>
            <t t-if="state.open">
                <div
                    class="animate-slide-down w-fit absolute flex flex-col end-0 shadow rounded overflow-hidden shadow z-2"
                >
                    <t t-if="showAll">
                        <HootLink class="'bg-btn p-2 whitespace-nowrap transition-colors'">
                            Run <strong>all</strong> tests
                        </HootLink>
                    </t>
                    <t t-if="showFailed">
                        <HootLink
                            ids="{ test: runnerState.failedIds }"
                            class="'bg-btn p-2 whitespace-nowrap transition-colors'"
                            title="'Run failed tests'"
                            onClick="onRunFailedClick"
                        >
                            Run failed <strong>tests</strong>
                        </HootLink>
                        <HootLink
                            ids="{ suite: failedSuites }"
                            class="'bg-btn p-2 whitespace-nowrap transition-colors'"
                            title="'Run failed suites'"
                            onClick="onRunFailedClick"
                        >
                            Run failed <strong>suites</strong>
                        </HootLink>
                    </t>
                </div>
            </t>
        </div>
    `;

    setup() {
        const { runner } = this.env;
        this.state = useState({
            disable: false,
            open: false,
        });
        this.runnerState = useState(runner.state);
        this.disableTimeout = 0;

        subscribeToURLParams(...$keys(runner.config));
    }

    getFailedSuiteIds() {
        const { tests } = this.env.runner;
        const suiteIds = [];
        for (const id of this.runnerState.failedIds) {
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
        this.state.open = false;
    }

    /**
     * @param {PointerEvent} ev
     */
    onPointerEnter(ev) {
        if (ev.pointerType !== "mouse") {
            return;
        }
        if (!this.isRunning) {
            this.state.open = true;
        }
    }

    onRunClick() {
        const { runner } = this.env;
        switch (runner.state.status) {
            case "done": {
                refresh();
                break;
            }
            case "ready": {
                if (runner.config.manual) {
                    runner.manualStart();
                } else {
                    refresh();
                }
                break;
            }
            case "running": {
                runner.stop();
                if (this.disableTimeout) {
                    clearTimeout(this.disableTimeout);
                }
                this.state.disable = true;
                this.disableTimeout = setTimeout(
                    () => (this.state.disable = false),
                    DISABLE_TIMEOUT
                );
                break;
            }
        }
    }

    onRunFailedClick() {
        storageSet(STORAGE.failed, []);
    }

    onToggleClick() {
        this.state.open = !this.state.open;
    }
}
