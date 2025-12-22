/** @odoo-module */

import { Component, onWillRender, useState, xml } from "@odoo/owl";
import { isFirefox } from "../../hoot-dom/hoot_dom_utils";
import { Tag } from "../core/tag";
import { Test } from "../core/test";
import { subscribeToURLParams } from "../core/url";
import {
    CASE_EVENT_TYPES,
    formatHumanReadable,
    formatTime,
    getTypeOf,
    isLabel,
    Markup,
    ordinal,
} from "../hoot_utils";
import { HootCopyButton } from "./hoot_copy_button";
import { HootLink } from "./hoot_link";
import { HootTechnicalValue } from "./hoot_technical_value";

/**
 * @typedef {import("../core/expect").CaseEvent} CaseEvent
 * @typedef {import("../core/expect").CaseEventType} CaseEventType
 * @typedef {import("../core/expect").CaseResult} CaseResult
 * @typedef {import("./setup_hoot_ui").StatusFilter} StatusFilter
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Boolean,
    Object: { entries: $entries, fromEntries: $fromEntries },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {[number, CaseEvent][]} indexedResults
 * @param {number} events
 */
function filterEvents(indexedResults, events) {
    /** @type {Record<number, CaseEvent[]>} */
    const filteredEvents = {};
    for (const [i, result] of indexedResults) {
        filteredEvents[i] = result.getEvents(events);
    }
    return filteredEvents;
}

/**
 * @param {CaseEvent[]} results
 * @param {StatusFilter} statusFilter
 */
function filterResults(results, statusFilter) {
    const ordinalResults = [];
    const hasFailed = results.some((r) => !r.pass);
    const shouldPass = statusFilter === "passed";
    for (let i = 0; i < results.length; i++) {
        if (!hasFailed || results[i].pass === shouldPass) {
            ordinalResults.push([i + 1, results[i]]);
        }
    }
    return ordinalResults;
}

/**
 * @param {string} label
 * @param {string} owner
 */
function stackTemplate(label, owner) {
    // Defined with string concat because line returns are taken into account in <pre> tags.
    const preContent =
        /* xml */ `<t t-foreach="parseStack(${owner}.stack)" t-as="part" t-key="part_index">` +
        /* xml */ `<t t-if="typeof part === 'string'" t-esc="part" />` +
        /* xml */ `<span t-else="" t-att-class="part.className" t-esc="part.value" />` +
        /* xml */ `</t>`;
    return /* xml */ `
        <t t-if="${owner}?.stack">
            <div class="flex col-span-2 gap-x-2 px-2 mt-1">
                <span class="text-rose">
                    ${label}:
                </span>
                <pre class="hoot-technical m-0">${preContent}</pre>
            </div>
        </t>
    `;
}

const DOC_URL = `https://www.odoo.com/documentation/18.0/developer/reference/frontend/unit_testing/hoot.html#`;

const ERROR_TEMPLATE = /* xml */ `
    <div class="text-rose flex items-center gap-1 px-2 truncate">
        <i class="fa fa-exclamation" />
        <strong t-esc="event.label" />
        <span class="flex truncate" t-esc="event.message.join(' ')" />
    </div>
    <t t-set="timestamp" t-value="formatTime(event.ts - (result.ts || 0), 'ms')" />
    <small class="text-gray flex items-center" t-att-title="timestamp">
        <t t-esc="'@' + timestamp" />
    </small>
    ${stackTemplate("Source", "event")}
    ${stackTemplate("Cause", "event.cause")}
`;

const EVENT_TEMPLATE = /* xml */ `
    <div
        t-attf-class="text-{{ eventColor }} flex items-center gap-1 px-2 truncate"
    >
        <t t-if="sType === 'assertion'">
            <t t-esc="event.number + '.'" />
        </t>
        <t t-else="">
            <i class="fa" t-att-class="eventIcon" />
        </t>
        <a
            class="hover:text-primary flex gap-1 items-center"
            t-att-class="{ 'text-cyan': sType === 'assertion' }"
            t-att-href="DOC_URL + (event.docLabel or event.label)"
            target="_blank"
        >
            <t t-if="event.flags">
                <i t-if="event.hasFlag('rejects')" class="fa fa-times" />
                <i t-elif="event.hasFlag('resolves')" class="fa fa-arrow-right" />
                <i t-if="event.hasFlag('not')" class="fa fa-exclamation" />
            </t>
            <strong t-esc="event.label" />
        </a>
        <span class="flex gap-1 truncate items-center">
            <t t-foreach="event.message" t-as="part" t-key="part_index">
                <t t-if="isLabel(part)">
                    <t t-if="!part[1]">
                        <span t-esc="part[0]" />
                    </t>
                    <t t-elif="part[1].endsWith('[]')">
                        <strong class="hoot-array">
                            <t>[</t>
                            <span t-attf-class="hoot-{{ part[1].slice(0, -2) }}" t-esc="part[0].slice(1, -1)" />
                            <t>]</t>
                        </strong>
                    </t>
                    <t t-elif="part[1] === 'icon'">
                        <i t-att-class="part[0]" />
                    </t>
                    <t t-else="">
                        <strong t-attf-class="hoot-{{ part[1] }}">
                            <t t-if="part[1] === 'url'">
                                <a
                                    class="underline"
                                    t-att-href="part[0]"
                                    t-esc="part[0]"
                                    target="_blank"
                                />
                            </t>
                            <t t-else="">
                                <t t-esc="part[0]" />
                            </t>
                        </strong>
                    </t>
                </t>
                <t t-else="">
                    <span t-esc="part" />
                </t>
            </t>
        </span>
    </div>
    <t t-set="timestamp" t-value="formatTime(event.ts - (result.ts || 0), 'ms')" />
    <small class="flex items-center text-gray" t-att-title="timestamp">
        <t t-esc="'@' + timestamp" />
    </small>
    <t t-if="event.additionalMessage">
        <div class="flex items-center ms-4 px-2 gap-1 col-span-2">
            <em class="text-blue truncate" t-esc="event.additionalMessage" />
            <HootCopyButton text="event.additionalMessage" />
        </div>
    </t>
    <t t-if="!event.pass">
        <t t-if="event.failedDetails">
            <div class="hoot-info grid col-span-2 gap-x-2 px-2">
                <t t-foreach="event.failedDetails" t-as="details" t-key="details_index">
                    <t t-if="isMarkup(details, 'group')">
                        <div class="col-span-2 flex gap-2 ps-2 mt-1" t-att-class="details.className">
                            <t t-esc="details.groupIndex" />.
                            <HootTechnicalValue value="details.content" />
                        </div>
                    </t>
                    <t t-else="">
                        <HootTechnicalValue value="details[0]" />
                        <HootTechnicalValue value="details[1]" />
                    </t>
                </t>
            </div>
        </t>
        ${stackTemplate("Source", "event")}
    </t>
`;

const CASE_EVENT_TYPES_INVERSE = $fromEntries(
    $entries(CASE_EVENT_TYPES).map(([k, v]) => [v.value, k])
);

const R_STACK_LINE_START = isFirefox()
    ? /^\s*(?<prefix>@)(?<rest>.*)/i
    : /^\s*(?<prefix>at)(?<rest>.*)/i;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @typedef {{
 *  open?: boolean | "always";
 *  slots: any;
 *  test: Test;
 * }} TestResultProps
 */

/** @extends {Component<TestResultProps, import("../hoot").Environment>} */
export class HootTestResult extends Component {
    static components = { HootCopyButton, HootLink, HootTechnicalValue };

    static props = {
        open: [{ type: Boolean }, { value: "always" }],
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
            class="${HootTestResult.name}
                flex flex-col w-full border-b overflow-hidden
                border-gray-300 dark:border-gray-600"
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
                <t t-foreach="filteredResults" t-as="indexedResult" t-key="indexedResult[0]">
                    <t t-set="index" t-value="indexedResult[0]" />
                    <t t-set="result" t-value="indexedResult[1]" />
                    <t t-if="results.length > 1">
                        <div class="flex justify-between mx-2 my-1">
                            <span t-attf-class="text-{{ result.pass ? 'emerald' : 'rose' }}">
                                <t t-esc="ordinal(index)" /> run:
                            </span>
                            <t t-set="timestamp" t-value="formatTime(result.duration, 'ms')" />
                            <small class="text-gray flex items-center" t-att-title="timestamp">
                                <t t-esc="timestamp" />
                            </small>
                        </div>
                    </t>
                    <div class="hoot-result-detail grid gap-1 rounded overflow-x-auto p-1 mx-2 animate-slide-down">
                        <t t-if="!filteredEvents[index].length">
                            <em class="text-gray px-2 py-1">No test event to show</em>
                        </t>
                        <t t-foreach="filteredEvents[index]" t-as="event" t-key="event_index">
                            <t t-set="sType" t-value="getTypeName(event.type)" />
                            <t t-set="eventIcon" t-value="CASE_EVENT_TYPES[sType].icon" />
                            <t t-set="eventColor" t-value="
                                'pass' in event ?
                                    (event.pass ? 'emerald' : 'rose') :
                                    CASE_EVENT_TYPES[sType].color"
                            />
                            <t t-if="sType === 'error'">
                                ${ERROR_TEMPLATE}
                            </t>
                            <t t-else="">
                                ${EVENT_TEMPLATE}
                            </t>
                        </t>
                    </div>
                </t>
                <div class="flex flex-col overflow-y-hidden">
                    <nav class="flex items-center gap-2 p-2 text-gray">
                        <button
                            type="button"
                            class="flex items-center px-1 gap-1 text-sm hover:text-primary"
                            t-on-click.stop="toggleCode"
                        >
                            <t t-if="state.showCode">
                                Hide source code
                            </t>
                            <t t-else="">
                                Show source code
                            </t>
                        </button>
                    </nav>
                    <t t-if="state.showCode">
                        <div class="m-2 mt-0 rounded animate-slide-down overflow-auto">
                            <pre
                                class="language-javascript"
                                style="margin: 0"
                            ><code class="language-javascript" t-out="props.test.code" /></pre>
                        </div>
                    </t>
                </div>
            </t>
        </div>
    `;

    CASE_EVENT_TYPES = CASE_EVENT_TYPES;
    DOC_URL = DOC_URL;

    Tag = Tag;
    formatHumanReadable = formatHumanReadable;
    formatTime = formatTime;
    getTypeOf = getTypeOf;
    isLabel = isLabel;
    isMarkup = Markup.isMarkup;
    ordinal = ordinal;

    /** @type {ReturnType<typeof filterEvents>} */
    filteredEvents;
    /** @type {[number, CaseEvent][]} */
    filteredResults;

    setup() {
        subscribeToURLParams("*");

        const { runner, ui } = this.env;
        this.config = useState(runner.config);
        this.logs = useState(this.props.test.logs);
        this.results = useState(this.props.test.results);
        this.state = useState({
            showCode: false,
            showDetails: Boolean(this.props.open),
        });
        this.uiState = useState(ui);

        onWillRender(this.onWillRender.bind(this));
    }

    getClassName() {
        if (this.logs.error) {
            return "bg-rose-900";
        }
        switch (this.props.test.status) {
            case Test.ABORTED: {
                return "bg-amber-900";
            }
            case Test.FAILED: {
                if (this.props.test.config.todo) {
                    return "bg-purple-900";
                } else {
                    return "bg-rose-900";
                }
            }
            case Test.PASSED: {
                if (this.logs.warn) {
                    return "bg-amber-900";
                } else if (this.props.test.config.todo) {
                    return "bg-purple-900";
                } else {
                    return "bg-emerald-900";
                }
            }
            default: {
                return "bg-cyan-900";
            }
        }
    }

    /**
     * @param {number} nType
     */
    getTypeName(nType) {
        return CASE_EVENT_TYPES_INVERSE[nType];
    }

    onWillRender() {
        this.filteredResults = filterResults(this.results, this.uiState.statusFilter);
        this.filteredEvents = filterEvents(this.filteredResults, this.config.events);
    }

    /**
     * @param {string} stack
     */
    parseStack(stack) {
        const result = [];
        for (const line of stack.split("\n")) {
            const match = line.match(R_STACK_LINE_START);
            if (match) {
                result.push(
                    { className: "text-rose", value: match.groups.prefix },
                    match.groups.rest + "\n"
                );
            } else {
                result.push(line + "\n");
            }
        }
        return result;
    }

    toggleCode() {
        this.state.showCode = !this.state.showCode;
    }

    toggleDetails() {
        if (this.props.open === "always") {
            return;
        }
        this.state.showDetails = !this.state.showDetails;
    }
}
