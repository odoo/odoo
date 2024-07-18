/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { HootCopyButton } from "./hoot_copy_button";
import { HootLink } from "./hoot_link";
import { HootTagButton } from "./hoot_tag_button";

/**
 * @typedef {{
 *  canCopy?: boolean;
 *  full?: boolean;
 *  inert?: boolean;
 *  showStatus?: boolean;
 *  test: Test;
 * }} HootTestPathProps
 */

/** @extends {Component<HootTestPathProps, import("../hoot").Environment>} */
export class HootTestPath extends Component {
    static components = { HootCopyButton, HootLink, HootTagButton };

    static props = {
        canCopy: { type: Boolean, optional: true },
        full: { type: Boolean, optional: true },
        inert: { type: Boolean, optional: true },
        showStatus: { type: Boolean, optional: true },
        test: Test,
    };

    static template = xml`
        <t t-set="statusInfo" t-value="getStatusInfo()" />
        <div class="flex items-center gap-1 whitespace-nowrap overflow-hidden">
            <t t-if="props.showStatus">
                <span
                    t-attf-class="inline-flex min-w-3 min-h-3 rounded-full bg-{{ statusInfo.className }}"
                    t-att-title="statusInfo.text"
                />
            </t>
            <span class="flex items-center overflow-hidden">
                <t t-if="uiState.selectedSuiteId and !props.full">
                    <span class="text-muted font-bold p-1 select-none hidden md:inline">...</span>
                    <span class="select-none hidden md:inline">/</span>
                </t>
                <t t-foreach="getTestPath()" t-as="suite" t-key="suite.id">
                    <t t-if="props.inert">
                        <span
                            class="text-muted whitespace-nowrap font-bold p-1 select-text hidden md:inline transition-colors"
                            t-esc="suite.name"
                        />
                    </t>
                    <t t-else="">
                        <HootLink
                            type="'suite'"
                            id="suite.id"
                            class="'hoot-link text-muted whitespace-nowrap font-bold p-1 select-text hidden md:inline transition-colors'"
                            title="'Run ' + suite.fullName"
                            t-esc="suite.name"
                        />
                        <t t-if="suite.config.multi">
                            <strong class="text-abort whitespace-nowrap me-1">
                                x<t t-esc="suite.config.multi" />
                            </strong>
                        </t>
                    </t>
                    <span class="select-none hidden md:inline" t-att-class="{ 'text-skip': suite.config.skip }">/</span>
                </t>
                <span
                    class="text-primary truncate font-bold p-1"
                    t-att-class="{ 'text-skip': props.test.config.skip }"
                    t-att-title="props.test.name"
                    t-esc="props.test.name"
                />
                <t t-if="props.canCopy">
                    <HootCopyButton text="props.test.name" altText="props.test.id" />
                </t>
                <t t-if="props.test.runCount > 1">
                    <strong class="text-abort whitespace-nowrap mx-1">
                        x<t t-esc="props.test.runCount" />
                    </strong>
                </t>
            </span>
            <t t-if="props.test.tags.length">
                <ul class="flex items-center gap-1">
                    <t t-foreach="props.test.tags.slice(0, 5)" t-as="tag" t-key="tag.name">
                        <li class="flex">
                            <HootTagButton tag="tag" />
                        </li>
                    </t>
                </ul>
            </t>
        </div>
    `;

    setup() {
        this.uiState = useState(this.env.ui);
    }

    getStatusInfo() {
        switch (this.props.test.status) {
            case Test.ABORTED: {
                return { className: "abort", text: "aborted" };
            }
            case Test.FAILED: {
                if (this.props.test.config.todo) {
                    return { className: "todo", text: "todo" };
                } else {
                    return { className: "fail", text: "failed" };
                }
            }
            case Test.PASSED: {
                if (this.props.test.config.todo) {
                    return { className: "todo", text: "todo" };
                } else {
                    return { className: "pass", text: "passed" };
                }
            }
            default: {
                return { className: "skip", text: "skipped" };
            }
        }
    }

    /**
     * @param {import("../core/suite").Suite} suite
     */
    getSuiteInfo(suite) {
        let suites = 0;
        let tests = 0;
        let assertions = 0;
        for (const job of suite.jobs) {
            if (job instanceof Test) {
                tests++;
                assertions += job.lastResults?.assertions.length || 0;
            } else {
                suites++;
            }
        }
        return {
            id: suite.id,
            name: suite.name,
            parent: suite.parent?.name || null,
            suites,
            tests,
            assertions,
        };
    }

    getTestPath() {
        const { selectedSuiteId } = this.uiState;
        const { test } = this.props;
        const path = test.path.slice(0, -1);
        if (this.props.full || !selectedSuiteId) {
            return path;
        }
        const index = path.findIndex((suite) => suite.id === selectedSuiteId) + 1;
        return path.slice(index);
    }
}
