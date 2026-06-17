/** @odoo-module */

import { Component, plugin, props, t, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { HootCopyButton } from "./hoot_copy_button";
import { HootLink } from "./hoot_link";
import { HootTagButton } from "./hoot_tag_button";
import { UiPlugin } from "./ui_plugin";

export class HootTestPath extends Component {
    static components = { HootCopyButton, HootLink, HootTagButton };
    static template = xml`
        <t t-set="statusInfo" t-value="this.getStatusInfo()" />
        <div class="flex items-center gap-1 whitespace-nowrap overflow-hidden">
            <t t-if="this.props.showStatus">
                <span
                    t-attf-class="inline-flex min-w-3 min-h-3 rounded-full bg-{{ statusInfo.className }}"
                    t-att-title="statusInfo.text"
                />
            </t>
            <span class="flex items-center overflow-hidden">
                <t t-if="this.ui.selectedSuiteId() and !this.props.full">
                    <span class="text-gray font-bold p-1 select-none hidden md:inline">...</span>
                    <span class="select-none hidden md:inline">/</span>
                </t>
                <t t-foreach="this.getTestPath()" t-as="suite" t-key="suite.id">
                    <t t-if="this.props.inert">
                        <span
                            class="text-gray whitespace-nowrap font-bold p-1 hidden md:inline transition-colors"
                            t-out="suite.name"
                        />
                    </t>
                    <t t-else="">
                        <HootLink
                            ids="{ id: suite.id }"
                            class="'text-gray hover:text-primary hover:underline whitespace-nowrap font-bold p-1 hidden md:inline transition-colors'"
                            title="'Run ' + suite.fullName"
                            t-out="suite.name"
                        />
                        <t t-if="suite.config.multi">
                            <strong class="text-amber whitespace-nowrap me-1">
                                x<t t-out="suite.config.multi" />
                            </strong>
                        </t>
                    </t>
                    <span class="select-none hidden md:inline" t-att-class="{ 'text-cyan': suite.config.skip }">/</span>
                </t>
                <span
                    class="text-primary truncate font-bold p-1"
                    t-att-class="{ 'text-cyan': this.props.test.config.skip }"
                    t-att-title="this.props.test.name"
                    t-out="this.props.test.name"
                />
                <t t-if="this.props.canCopy">
                    <HootCopyButton text="this.props.test.name" altText="this.props.test.id" />
                </t>
                <t t-set="results" t-value="this.props.test.results()" />
                <t t-if="results.length > 1">
                    <strong class="text-amber whitespace-nowrap mx-1">
                        x<t t-out="results.length" />
                    </strong>
                </t>
            </span>
            <t t-if="this.props.test.tags.length">
                <ul class="flex items-center gap-1">
                    <t t-foreach="this.props.test.tags.slice(0, 5)" t-as="tag" t-key="tag.name">
                        <li class="flex">
                            <HootTagButton tag="tag" />
                        </li>
                    </t>
                </ul>
            </t>
        </div>
    `;

    // Props & plugins
    props = props({
        canCopy: t.boolean().optional(),
        full: t.boolean().optional(),
        inert: t.boolean().optional(),
        showStatus: t.boolean().optional(),
        test: t.instanceOf(Test),
    });
    ui = plugin(UiPlugin);

    getStatusInfo() {
        switch (this.props.test.status()) {
            case Test.ABORTED: {
                return { className: "amber", text: "aborted" };
            }
            case Test.FAILED: {
                if (this.props.test.config.todo) {
                    return { className: "purple", text: "todo" };
                } else {
                    return { className: "rose", text: "failed" };
                }
            }
            case Test.PASSED: {
                if (this.props.test.config.todo) {
                    return { className: "purple", text: "todo" };
                } else {
                    return { className: "emerald", text: "passed" };
                }
            }
            default: {
                return { className: "cyan", text: "skipped" };
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
                assertions += job.lastResults?.counts.assertion || 0;
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
        const selectedSuiteId = this.ui.selectedSuiteId();
        const { test } = this.props;
        const path = test.path.slice(0, -1);
        if (this.props.full || !selectedSuiteId) {
            return path;
        }
        const index = path.findIndex((suite) => suite.id === selectedSuiteId) + 1;
        return path.slice(index);
    }
}
