/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { Tag } from "../core/tag";
import { Test } from "../core/test";
import { subscribeToURLParams, withParams } from "../core/url";
import { formatTime } from "../hoot_utils";
import { HootTechnicalValue } from "./hoot_technical_value";
import { HootTestPath } from "./hoot_test_path";

/**
 * @typedef {{
 *  open: boolean;
 *  test: Test;
 * }} TestResultProps
 */

const MATCHERS_DOC_URL = `https://www.odoo.com/documentation/master/developer/tutorials/master_odoo_web_framework/05_testing.html`;

/** @extends Component<TestResultProps, import("../hoot").Environment> */
export class HootTestResult extends Component {
    static components = { HootTestPath, HootTechnicalValue };

    static props = {
        open: Boolean,
        test: Test,
    };

    static template = xml`
        <details
            class="hoot-result d-flex flex-column"
            t-att-class="className"
            t-att-open="props.open"
        >
            <summary class="px-3 d-flex align-items-center justify-content-between">
                <div class="d-flex gap-2 overflow-hidden">
                    <HootTestPath canCopy="true" test="props.test" />
                </div>
                <div class="d-flex ms-1 gap-2">
                    <small
                        class="text-nowrap"
                        t-attf-class="hoot-text-{{ props.test.config.skip ? 'skip' : 'muted' }}"
                    >
                        <t t-if="props.test.config.skip">
                            skipped
                        </t>
                        <t t-else="">
                            <t t-if="props.test.status === Test.ABORTED">
                                aborted after
                            </t>
                            <t t-esc="formatTime(props.test.lastResults.duration)" />
                        </t>
                    </small>
                    <div class="d-flex align-items-center gap-1">
                        <a
                            t-att-href="withParams('test', props.test.id)"
                            class="hoot-btn-link hoot-text-pass rounded px-1"
                            title="Run this test only"
                        >
                            <i class="fa fa-play" />
                        </a>
                        <a
                            t-att-href="withParams('test', props.test.id, { debug: true })"
                            class="hoot-btn-link hoot-text-pass rounded px-1"
                            title="Run this test only in debug mode"
                        >
                            <i class="fa fa-bug" />
                        </a>
                        <a
                            t-att-href="withParams('test', props.test.id, { ignore: true })"
                            class="hoot-btn-link hoot-text-fail rounded px-1"
                            title="Ignore test"
                        >
                            <i class="fa fa-ban" />
                        </a>
                    </div>
                </div>
            </summary>
            <t t-if="!props.test.config.skip">
                <div class="hoot-result-detail d-grid gap-1 rounded overflow-x-auto p-1 m-2 mt-0">
                    <t t-set="lastResults" t-value="props.test.lastResults" />
                    <t t-foreach="lastResults.assertions" t-as="assertion" t-key="assertion.id">
                        <div
                            t-attf-class="hoot-text-{{ assertion.pass ? 'pass' : 'fail' }} d-flex align-items-center gap-1 px-2 text-truncate"
                        >
                            <t t-esc="(assertion_index + 1) + '.'" />
                            <t t-if="assertion.label">
                                <i t-if="assertion.modifiers.rejects" class="fa fa-times hoot-text-skip" />
                                <i t-elif="assertion.modifiers.resolves" class="fa fa-arrow-right hoot-text-skip" />
                                <i t-if="assertion.modifiers.not" class="fa fa-exclamation hoot-text-skip" />
                                <a t-att-href="getLinkHref(assertion.label)" target="_blank" class="hoot-link hoot-text-skip">
                                    <strong t-esc="assertion.label" />
                                </a>
                            </t>
                            <t t-esc="assertion.message" />
                        </div>
                        <t t-set="timestamp" t-value="assertion.ts - lastResults.ts" />
                        <small class="hoot-text-muted d-flex align-items-center" t-att-title="timestamp">
                            <t t-esc="'@' + formatTime(timestamp)" />
                        </small>
                        <t t-if="!assertion.pass and assertion.info">
                            <div class="hoot-info hoot-span-2 d-grid">
                                <t t-foreach="assertion.info" t-as="info" t-key="info_index">
                                    <HootTechnicalValue value="info[0]" />
                                    <HootTechnicalValue value="info[1]" />
                                </t>
                            </div>
                        </t>
                    </t>
                    <t t-foreach="lastResults.errors" t-as="error" t-key="error_index">
                        <div class="px-2 hoot-text-fail hoot-span-2">
                            Error while running test "<t t-esc="props.test.name" />"
                        </div>
                        <div class="hoot-info hoot-span-2 d-grid">
                            <div class="hoot-info-line">
                                <span class="hoot-text-fail">Source:</span>
                                <pre
                                    class="hoot-technical m-0"
                                    t-esc="error.stack"
                                />
                            </div>
                        </div>
                    </t>
                </div>
            </t>
        </details>
    `;

    Tag = Tag;
    Test = Test;
    formatTime = formatTime;
    withParams = withParams;

    get className() {
        switch (this.props.test.status) {
            case Test.ABORTED: {
                return "hoot-abort";
            }
            case Test.FAILED: {
                return "hoot-fail";
            }
            case Test.PASSED: {
                return "hoot-pass";
            }
            default: {
                return "hoot-skip";
            }
        }
    }

    setup() {
        subscribeToURLParams("*");
    }

    /**
     * @param {string} label
     */
    getLinkHref(label) {
        return `${MATCHERS_DOC_URL}#${label}`;
    }
}
