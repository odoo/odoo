/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { refresh, subscribeToURLParams } from "../core/url";
import { HootLink } from "./hoot_link";
import { Test } from "../core/test";

/**
 * @typedef {{
 * }} HootButtonsProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { keys: $keys },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/** @extends {Component<HootButtonsProps, import("../hoot").Environment>} */
export class HootButtons extends Component {
    static components = { HootLink };

    static props = {};

    static template = xml`
        <div class="${HootButtons.name} flex rounded gap-px overflow-hidden">
            <t t-set="isRunning" t-value="runnerState.status === 'running'" />
            <button
                class="flex items-center bg-btn gap-2 px-2 py-1 transition-colors"
                t-on-click="onRunClick"
                t-att-title="isRunning ? 'Stop (Esc)' : 'Run'"
            >
                <i t-attf-class="fa fa-{{ isRunning ? 'stop' : 'play' }}" />
                <span class="hidden sm:inline" t-esc="isRunning ? 'Stop' : 'Run'" />
            </button>
            <t t-if="state.failed.length">
                <HootLink
                    type="'test'"
                    id="state.failed"
                    class="'bg-btn px-2 py-1 transition-colors animate-slide-left'"
                    title="'Run failed tests'"
                >
                    Run failed
                </HootLink>
            </t>
            <t t-if="env.runner.hasFilter">
                <HootLink class="'bg-btn px-2 py-1 transition-colors animate-slide-left'">
                    Run all
                </HootLink>
            </t>
        </div>
    `;

    setup() {
        const { runner } = this.env;
        this.state = useState({
            failed: [],
        });
        this.runnerState = useState(runner.state);

        runner.__afterPostTest(({ id, status }) => {
            if (status === Test.FAILED) {
                this.state.failed.push(id);
            }
        });

        subscribeToURLParams(...$keys(runner.config));
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
                    runner.start();
                } else {
                    refresh();
                }
                break;
            }
            case "running": {
                runner.stop();
                break;
            }
        }
    }
}
