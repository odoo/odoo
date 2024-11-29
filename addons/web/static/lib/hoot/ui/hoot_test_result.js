/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { Tag } from "../core/tag";
import { Test } from "../core/test";
import { subscribeToURLParams } from "../core/url";
import { formatHumanReadable, formatTime, getTypeOf, ordinal } from "../hoot_utils";
import { HootLink } from "./hoot_link";
import { HootTechnicalValue } from "./hoot_technical_value";

/**
 * @typedef {{
 *  open: boolean;
 *  slots: any;
 *  test: Test;
 * }} TestResultProps
 */

/** @extends {Component<TestResultProps, import("../hoot").Environment>} */
export class HootTestResult extends Component {
    static components = { HootLink, HootTechnicalValue };

    static props = {
        open: Boolean,
        slots: {
            type: Object,
            shape: {
                default: Object,
            },
        },
        test: Test,
    };

    static template = xml`
        <div
            class="${HootTestResult.name} flex flex-col border-b border-gray-300 dark:border-gray-600"
            t-att-class="getClassName()"
        >
            <button
                type="button"
                class="px-3 flex items-center justify-between"
                t-on-click.stop="toggleDetails"
            >
                <t t-slot="default" />
            </button>
            <t t-if="state.showDetails and !props.test.config.skip">
                <t t-foreach="results" t-as="result" t-key="result_index">
                    <t t-if="results.length > 1">
                        <div t-attf-class="text-{{ result.pass ? 'pass' : 'fail' }} mx-2 mb-1" >
                            <t t-esc="ordinal(result_index + 1)" /> run:
                        </div>
                    </t>
                    <div class="hoot-result-detail grid gap-1 rounded overflow-x-auto p-1 mx-2 mb-1 animate-slide-down">
                        <t t-foreach="result.assertions || []" t-as="assertion" t-key="assertion.id">
                            <div
                                t-attf-class="text-{{ assertion.pass ? 'pass' : 'fail' }} flex items-center gap-1 px-2 truncate"
                            >
                                <t t-esc="(assertion_index + 1) + '.'" />
                                <t t-if="assertion.label">
                                    <i t-if="assertion.modifiers.rejects" class="fa fa-times text-skip" />
                                    <i t-elif="assertion.modifiers.resolves" class="fa fa-arrow-right text-skip" />
                                    <i t-if="assertion.modifiers.not" class="fa fa-exclamation text-skip" />
                                    <!-- TODO: add documentation links once they exist -->
                                    <a href="#" class="hoot-link text-skip">
                                        <strong t-esc="assertion.label" />
                                    </a>
                                </t>
                                <span
                                    class="flex gap-1 truncate items-center"
                                    t-att-title="assertion.message"
                                >
                                    <t t-foreach="assertion.messageParts" t-as="part" t-key="part_index">
                                        <t t-if="part.type and part.type !== 'raw'">
                                            <t t-if="part.type.endsWith('[]')">
                                                <strong class="hoot-array">
                                                    <t>[</t>
                                                    <span t-attf-class="hoot-{{ part.type.slice(0, -2) }}" t-esc="part.slice(1, -1)" />
                                                    <t>]</t>
                                                </strong>
                                            </t>
                                            <t t-else="">
                                                <strong t-attf-class="hoot-{{ part.type }}" t-esc="part" />
                                            </t>
                                        </t>
                                        <t t-else="">
                                            <span t-esc="part" />
                                        </t>
                                    </t>
                                </span>
                            </div>
                            <t t-set="timestamp" t-value="formatTime(assertion.ts - (result.ts || 0), 'ms')" />
                            <small class="text-muted flex items-center" t-att-title="timestamp">
                                <t t-esc="'@' + timestamp" />
                            </small>
                            <t t-if="!assertion.pass and assertion.failedDetails">
                                <div class="hoot-info grid gap-x-2 col-span-2">
                                    <t t-foreach="assertion.failedDetails" t-as="details" t-key="details_index">
                                        <HootTechnicalValue value="details[0]" />
                                        <HootTechnicalValue value="details[1]" />
                                    </t>
                                </div>
                            </t>
                        </t>
                        <t t-foreach="result.errors || []" t-as="error" t-key="error_index">
                            <div class="px-2 text-fail col-span-2">
                                Error while running test "<t t-esc="props.test.name" />"
                            </div>
                            <div class="hoot-info grid gap-x-2 col-span-2">
                                <div class="hoot-info-line grid gap-x-2">
                                    <span class="text-fail">Source:</span>
                                    <pre
                                        class="hoot-technical m-0"
                                        t-esc="error.stack"
                                    />
                                </div>
                            </div>
                            <t t-if="error.cause">
                                <div class="hoot-info grid col-span-2">
                                    <div class="hoot-info-line grid gap-x-2">
                                        <span class="text-fail">Cause:</span>
                                        <pre
                                            class="hoot-technical m-0"
                                            t-esc="error.cause.stack"
                                        />
                                    </div>
                                </div>
                            </t>
                        </t>
                    </div>
                </t>
                <div class="m-2 mt-0 flex flex-col">
                    <button
                        type="button"
                        class="hoot-link text-muted text-sm px-1"
                        t-on-click.stop="toggleCode"
                    >
                        <t t-if="state.showCode">
                            Hide source code
                        </t>
                        <t t-else="">
                            Show source code
                        </t>
                    </button>
                    <t t-if="state.showCode">
                        <pre
                            class="p-2 rounded bg-white text-black dark:bg-black dark:text-white animate-slide-down overflow-auto"
                        ><code class="language-javascript" t-out="props.test.code" /></pre>
                    </t>
                </div>
            </t>
        </div>
    `;

    Tag = Tag;
    formatHumanReadable = formatHumanReadable;
    formatTime = formatTime;
    getTypeOf = getTypeOf;
    ordinal = ordinal;

    setup() {
        subscribeToURLParams("*");

        this.logs = useState(this.props.test.logs);
        this.results = useState(this.props.test.results);
        this.state = useState({
            showCode: false,
            showDetails: this.props.open,
        });
    }

    getClassName() {
        if (this.logs.error) {
            return "bg-fail-900";
        }
        switch (this.props.test.status) {
            case Test.ABORTED: {
                return "bg-abort-900";
            }
            case Test.FAILED: {
                if (this.props.test.config.todo) {
                    return "bg-todo-900";
                } else {
                    return "bg-fail-900";
                }
            }
            case Test.PASSED: {
                if (this.logs.warn) {
                    return "bg-abort-900";
                } else if (this.props.test.config.todo) {
                    return "bg-todo-900";
                } else {
                    return "bg-pass-900";
                }
            }
            default: {
                return "bg-skip-900";
            }
        }
    }

    toggleCode() {
        this.state.showCode = !this.state.showCode;
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }
}
