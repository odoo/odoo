/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { refresh, subscribeToURLParams, withParams } from "../core/url";
import { storage } from "../hoot_utils";

/**
 * @typedef {{}} HootButtonsProps
 */

/** @extends Component<HootButtonsProps, import("../hoot").Environment> */
export class HootButtons extends Component {
    static props = {};

    static template = xml`
        <div class="hoot-buttons d-flex overflow-hidden">
            <button
                class="hoot-abort hoot-btn hoot-btn-primary d-flex align-items-center gap-2 px-2 py-1"
                t-on-click="onRunClick"
                t-att-title="state.running ? 'Stop' : 'Run'"
            >
                <i t-attf-class="fa fa-{{ state.running ? 'stop' : 'play' }}" />
                <span class="d-none d-sm-inline" t-esc="state.running ? 'Stop' : 'Run'" />
            </button>
            <t t-if="state.failed.length">
                <a
                    class="hoot-run-failed hoot-btn hoot-btn-primary px-2 py-1"
                    href=""
                    t-on-click="onRunFailedClick"
                    title="Run failed tests"
                >
                    Run failed
                </a>
            </t>
            <t t-if="env.runner.hasFilter">
                <a class="hoot-run-all hoot-btn hoot-btn-primary px-2 py-1" t-att-href="withParams()">
                    Run all
                </a>
            </t>
        </div>
    `;

    withParams = withParams;

    setup() {
        const { runner } = this.env;
        const previousFails = storage("session").get("failed-tests", []);
        this.state = useState({ failed: previousFails, running: false });

        runner.beforeAll(() => {
            this.state.running = true;

            return () => (this.state.running = false);
        });
        runner.afterEach(({ id, status }) => {
            if (status !== Test.PASSED) {
                this.state.failed.push(id);
            }
        });

        subscribeToURLParams(...Object.keys(runner.config));
    }

    onRunClick() {
        const { runner } = this.env;
        switch (runner.status) {
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

    onRunFailedClick() {
        storage("session").set("failed-tests", this.state.failed);
    }
}
