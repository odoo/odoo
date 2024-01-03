/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { getRect } from "@web/../lib/hoot-dom/helpers/dom";
import { Suite } from "../core/suite";
import { Test } from "../core/test";
import { withParams } from "../core/url";
import { HootCopyButton } from "./hoot_copy_button";
import { HootTagButton } from "./hoot_tag_button";

/**
 * @typedef {{
 *  canCopy?: boolean;
 *  test: Test;
 * }} HootTestPathProps
 */

/** @extends Component<HootTestPathProps, import("../hoot").Environment> */
export class HootTestPath extends Component {
    static components = { HootCopyButton, HootTagButton };

    static props = {
        canCopy: Boolean,
        test: Test,
    };

    static template = xml`
        <t t-set="statusInfo" t-value="getStatusInfo()" />
        <div class="hoot-path d-flex align-items-center dropdown gap-1 text-nowrap overflow-hidden" t-on-pointerleave="removeTooltip">
            <span t-attf-class="hoot-circle hoot-bg-{{ statusInfo.className }}" t-att-title="statusInfo.text" />
            <span class="d-flex align-items-center overflow-hidden">
                <t t-foreach="props.test.path.slice(0, -1)" t-as="suite" t-key="suite.id">
                    <a
                        t-att-href="withParams('suite', suite.id)"
                        class="hoot-link hoot-text-muted text-nowrap fw-bold p-1 d-none d-md-inline"
                        t-att-class="{ 'hoot-text-skip': suite.config.skip }"
                        t-attf-title='Run "{{ suite.fullName }}"'
                        t-on-pointerenter="(ev) => this.setTooltip(ev, suite)"
                        t-esc="suite.name"
                    />
                    <span class="d-none d-md-inline" t-att-class="{ 'hoot-text-skip': suite.config.skip }">/</span>
                </t>
                <span
                    class="hoot-text-primary text-truncate fw-bold p-1"
                    t-att-class="{ 'hoot-text-skip': props.test.config.skip }"
                    t-att-title="props.test.name"
                >
                    <t t-esc="props.test.name" />
                    <t t-if="!props.test.config.skip">
                        <t t-set="expectLength" t-value="props.test.lastResults?.assertions?.length or 0" />
                        <span class="user-select-none" t-attf-title="{{ expectLength }} assertions passed">
                            (<t t-esc="expectLength" />)
                        </span>
                    </t>
                </span>
                <t t-if="props.canCopy">
                    <HootCopyButton text="props.test.name" altText="props.test.id" />
                </t>
                <t t-if="props.test.config.multi">
                    <strong class="hoot-text-abort text-nowrap mx-1">
                        x<t t-esc="props.test.visited" />
                        <t t-if="props.test.visited lt props.test.config.multi">
                            <t t-esc="'/' + props.test.config.multi" />
                        </t>
                    </strong>
                </t>
            </span>
            <t t-if="props.test.tags.length">
                <ul class="d-flex align-items-center gap-1 m-0 list-unstyled">
                    <t t-foreach="props.test.tags.slice(0, 5)" t-as="tag" t-key="tag.id">
                        <li class="d-flex">
                            <HootTagButton tag="tag" />
                        </li>
                    </t>
                </ul>
            </t>
            <t t-if="state.tooltipTarget">
                <t t-set="suiteInfo" t-value="getSuiteInfo(state.tooltipTarget)" />
                <div
                    class="hoot-dropdown position-absolute top-100 d-flex flex-column shadow rounded text-nowrap overflow-hidden"
                    t-attf-style="left: {{ state.tooltipX }}px; transform: translateX(-50%);"
                >
                    <h6 class="text-reset d-flex align-items-center justify-content-between gap-1 border-bottom p-2 pb-1 m-0">
                        <span>
                            Suite <span class="hoot-text-primary" t-esc="suiteInfo.name" />
                        </span>
                        <a
                            t-att-href="withParams('suite', suiteInfo.id, { ignore: true })"
                            class="hoot-btn-link hoot-text-fail rounded px-1"
                            title="Ignore suite"
                        >
                            <i class="fa fa-ban" />
                        </a>
                    </h6>
                    <ul class="list-unstyled p-2 ps-3 m-0">
                        <li>
                            <t t-if="suiteInfo.parent">
                                Parent suite: <strong class="hoot-text-primary" t-esc="suiteInfo.parent" />
                            </t>
                            <t t-else="">
                                Root suite (no parent)
                            </t>
                        </li>
                        <li>
                            Contains:
                            <t t-if="suiteInfo.suites">
                                <strong class="hoot-text-primary" t-esc="suiteInfo.suites" /> suites
                            </t>
                            <t t-if="suiteInfo.suites and suiteInfo.tests"> and </t>
                            <t t-if="suiteInfo.tests">
                                <strong class="hoot-text-primary" t-esc="suiteInfo.tests" /> tests
                            </t>
                        </li>
                        <li t-if="suiteInfo.assertions">
                            Assertions: <strong class="hoot-text-primary" t-esc="suiteInfo.assertions" />
                        </li>
                    </ul>
                </div>
            </t>
        </div>
    `;

    withParams = withParams;

    setup() {
        this.state = useState({
            /** @type {Suite | null} */
            tooltipTarget: null,
            tooltipX: 0,
        });
    }

    getStatusInfo() {
        switch (this.props.test.status) {
            case Test.ABORTED: {
                return { className: "abort", text: "aborted" };
            }
            case Test.FAILED: {
                return { className: "fail", text: "failed" };
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
     * @param {Suite} suite
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

    removeTooltip() {
        this.state.tooltipTarget = null;
        this.state.tooltipX = 0;
    }

    /**
     * @param {PointerEvent} ev
     * @param {Suite} suite
     */
    setTooltip(ev, suite) {
        const rect = getRect(ev.target);
        this.state.tooltipTarget = suite;
        this.state.tooltipX = rect.x + rect.width / 2;
    }
}
