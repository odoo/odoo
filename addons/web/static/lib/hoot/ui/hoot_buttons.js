/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { refresh, subscribeToURLParams } from "../core/url";
import { STORAGE, storageGet, storageSet } from "../hoot_utils";
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
        <div class="${HootButtons.name} relative">
            <t t-set="isRunning" t-value="runnerState.status === 'running'" />
            <t t-set="showAll" t-value="env.runner.hasFilter" />
            <t t-set="showFailed" t-value="state.failed.length" />
            <t t-set="failedSuites" t-value="getFailedSuiteIds()" />
            <div class="flex rounded gap-px overflow-hidden">
            <button
                class="flex items-center bg-btn gap-2 px-2 py-1 transition-colors"
                t-on-click="onRunClick"
                t-att-title="isRunning ? 'Stop (Esc)' : 'Run'"
                t-att-disabled="state.disable"
            >
                <i t-attf-class="fa fa-{{ isRunning ? 'stop' : 'play' }}" />
                <span t-esc="isRunning ? 'Stop' : 'Run'" />
            </button>
            <t t-if="showAll or showFailed">
                <button
                    class="bg-btn px-2 py-1 transition-colors animate-slide-left"
                    t-on-click="() => state.open = !state.open"
                >
                    <i class="fa fa-caret-down" />
                </button>
            </t>
            </div>
            <t t-if="state.open">
                <div
                    class="animate-slide-down w-fit absolute flex flex-col end-0 shadow rounded overflow-hidden shadow z-2"
                >
                    <t t-if="showAll">
                        <HootLink class="'bg-btn p-2 whitespace-nowrap transition-colors'">
                            Run <strong>all</strong>
                        </HootLink>
                    </t>
                    <t t-if="showFailed">
                        <HootLink
                            type="'test'"
                            id="state.failed"
                            class="'bg-btn p-2 whitespace-nowrap transition-colors'"
                            title.translate="Run failed tests"
                            onClick="onRunFailedClick"
                        >
                            Run failed <strong>tests</strong>
                        </HootLink>
                        <HootLink
                            type="'suite'"
                            id="failedSuites"
                            class="'bg-btn p-2 whitespace-nowrap transition-colors'"
                            title.translate="Run failed suites"
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
        let failed = storageGet(STORAGE.failed) || [];
        const existingFailed = failed.filter((id) => runner.tests.has(id));
        if (existingFailed.length !== failed.length) {
            failed = existingFailed;
            storageSet(STORAGE.failed, existingFailed);
        }
        this.state = useState({
            disable: false,
            failed,
            open: false,
        });
        this.runnerState = useState(runner.state);
        this.disableTimeout = 0;

        runner.afterPostTest(({ id, status }) => {
            if (status === Test.FAILED) {
                this.state.failed.push(id);
                storageSet(STORAGE.failed, this.state.failed);
            } else {
                const index = this.state.failed.indexOf(id);
                if (index >= 0) {
                    this.state.failed.splice(index, 1);
                    storageSet(STORAGE.failed, this.state.failed);
                }
            }
        });

        subscribeToURLParams(...$keys(runner.config));
    }

    getFailedSuiteIds() {
        const { tests } = this.env.runner;
        const suiteIds = [];
        for (const id of this.state.failed) {
            const test = tests.get(id);
            if (test && !suiteIds.includes(test.parent.id)) {
                suiteIds.push(test.parent.id);
            }
        }
        return suiteIds;
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
}
