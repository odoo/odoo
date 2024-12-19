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
    ordinal,
} from "../hoot_utils";
import { HootLink } from "./hoot_link";
import { HootTechnicalValue } from "./hoot_technical_value";

/**
 * @typedef {import("../core/expect").CaseEvent} CaseEvent
 * @typedef {import("../core/expect").CaseEventType} CaseEventType
 * @typedef {import("../core/expect").CaseResult} CaseResult
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Boolean,
    Object: { entries: $entries, fromEntries: $fromEntries, keys: $keys },
    WeakMap,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {string} label
 * @param {string} owner
 */
const stackTemplate = (label, owner) => {
    // Defined with string concat because line returns are taken into account in <pre> tags.
    const preContent =
        /* xml */ `<t t-foreach="parseStack(${owner}.stack)" t-as="part" t-key="part_index">` +
        /* xml */ `<t t-if="typeof part === 'string'" t-esc="part" />` +
        /* xml */ `<span t-else="" t-att-class="part.className" t-esc="part.value" />` +
        /* xml */ `</t>`;
    return /* xml */ `
        <t t-if="${owner}?.stack">
            <div class="flex col-span-2 gap-x-2 px-2">
                <span class="text-rose">
                    ${label}:
                </span>
                <pre class="hoot-technical m-0">${preContent}</pre>
            </div>
        </t>
    `;
};

const ASSERTION_TEMPLATE = /* xml */ `
    <div
        t-attf-class="text-{{ event.pass ? 'emerald' : 'rose' }} flex items-center gap-1 px-2 truncate"
    >
        <t t-esc="assertionCount + '.'" />
        <t t-if="event.label">
            <!-- TODO: add documentation links once they exist -->
            <a href="#" class="text-cyan hover:text-primary flex gap-1 items-center">
                <i t-if="event.hasFlag('rejects')" class="fa fa-times text-cyan" />
                <i t-elif="event.hasFlag('resolves')" class="fa fa-arrow-right text-cyan" />
                <i t-if="event.hasFlag('not')" class="fa fa-exclamation text-cyan" />
                <strong t-esc="event.label" />
            </a>
        </t>
        <span
            class="flex gap-1 truncate items-center"
            t-att-title="event.message"
        >
            <t t-foreach="event.messageParts" t-as="part" t-key="part_index">
                <t t-if="part.type">
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
    <t t-set="timestamp" t-value="formatTime(event.ts - (result.ts || 0), 'ms')" />
    <small class="text-gray flex items-center" t-att-title="timestamp">
        <t t-esc="'@' + timestamp" />
    </small>
    <t t-if="!event.pass">
        <t t-if="event.failedDetails">
            <div class="hoot-info grid col-span-2 gap-x-2 px-2">
                <t t-foreach="event.failedDetails" t-as="details" t-key="details_index">
                    <HootTechnicalValue value="details[0]" />
                    <HootTechnicalValue value="details[1]" />
                </t>
            </div>
        </t>
        ${stackTemplate("Source", "event")}
    </t>
`;

const ERROR_TEMPLATE = /* xml */ `
    <div class="text-rose flex items-center gap-1 px-2 truncate">
        <i class="fa fa-exclamation" />
        <strong t-esc="event.label" />
        <span class="flex truncate" t-esc="event.message" />
    </div>
    <t t-set="timestamp" t-value="formatTime(event.ts - (result.ts || 0), 'ms')" />
    <small class="text-gray flex items-center" t-att-title="timestamp">
        <t t-esc="'@' + timestamp" />
    </small>
    ${stackTemplate("Source", "event")}
    ${stackTemplate("Cause", "event.cause")}
`;

const EVENT_TEMPLATE = /* xml */ `
    <div class="flex items-center gap-1 px-2 truncate">
        <!-- TODO: add documentation links once they exist -->
        <a href="#" t-attf-class="text-{{ eventColor }} flex gap-1 items-center">
            <i class="fa" t-att-class="eventIcon" />
            <strong t-esc="event.label" />
        </a>
        <span
            class="flex gap-1 truncate items-center"
            t-att-title="event.message"
        >
            <t t-foreach="event.messageParts" t-as="part" t-key="part_index">
                <t t-if="part.type">
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
    <t t-set="timestamp" t-value="formatTime(event.ts - (result.ts || 0), 'ms')" />
    <small class="text-gray flex items-center" t-att-title="timestamp">
        <t t-esc="'@' + timestamp" />
    </small>
`;

const CASE_EVENT_TYPES_INVERSE = $fromEntries($entries(CASE_EVENT_TYPES).map(([k, v]) => [v, k]));
const EVENT_PROPERTIES = {
    assertion: ["fa-check", "emerald"],
    error: ["fa-exclamation", "rose"],
    interaction: ["fa-bolt", "purple"],
    query: ["fa-search text-sm", "amber"],
    step: ["fa-arrow-right text-sm", "orange"],
};

const R_STACK_LINE_START = isFirefox()
    ? /^\s*(?<prefix>@)(?<rest>.*)/i
    : /^\s*(?<prefix>at)(?<rest>.*)/i;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

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
            class="${HootTestResult.name}
                flex flex-col border-b overflow-auto
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
                <t t-foreach="results" t-as="result" t-key="result_index">
                    <t t-if="results.length > 1">
                        <div t-attf-class="text-{{ result.pass ? 'emerald' : 'rose' }} mx-2 mb-1" >
                            <t t-esc="ordinal(result_index + 1)" /> run:
                        </div>
                    </t>
                    <div class="hoot-result-detail grid gap-1 rounded overflow-x-auto p-1 mx-2 animate-slide-down">
                        <t t-if="!filteredEvents.get(result)?.length">
                            <em class="text-gray px-2 py-1">No test event to show</em>
                        </t>
                        <t t-foreach="filteredEvents.get(result) || []" t-as="event" t-key="event.id">
                            <t t-set="sType" t-value="getTypeName(event.type)" />
                            <t t-set="eventIcon" t-value="EVENT_PROPERTIES[sType][0]" />
                            <t t-set="eventColor" t-value="EVENT_PROPERTIES[sType][1]" />
                            <t t-if="sType === 'assertion'">
                                <t t-set="assertionCount" t-value="(assertionCount || 0) + 1" />
                                ${ASSERTION_TEMPLATE}
                            </t>
                            <t t-elif="sType === 'error'">
                                ${ERROR_TEMPLATE}
                            </t>
                            <t t-else="">
                                ${EVENT_TEMPLATE}
                            </t>
                        </t>
                    </div>
                </t>
                <div class="flex flex-col">
                    <nav class="flex items-center gap-2 p-2 text-gray">
                        <t t-foreach="availableEventTypes" t-as="sType" t-key="sType">
                            <t t-set="eventColor" t-value="EVENT_PROPERTIES[sType][1]" />
                            <button
                                type="button"
                                class="p-1 border-b-2 transition-color"
                                t-att-class="availableEventTypes[sType] and 'text-' + eventColor + ' border-' + eventColor"
                                t-attf-title="{{ availableEventTypes[sType] ? 'Hide' : 'Show' }} {{ sType }} events"
                                t-on-click.stop="() => this.toggleEventType(sType)"
                            >
                                <i class="fa" t-att-class="EVENT_PROPERTIES[sType][0]" />
                            </button>
                        </t>
                        <button
                            type="button"
                            class="text-sm px-1 ms-auto hover:text-primary"
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
                        <pre
                            class="p-2 m-2 mt-0 rounded bg-white text-black dark:bg-black dark:text-white animate-slide-down overflow-auto"
                        ><code class="language-javascript" t-out="props.test.code" /></pre>
                    </t>
                </div>
            </t>
        </div>
    `;

    CASE_EVENT_TYPES = CASE_EVENT_TYPES;
    EVENT_PROPERTIES = EVENT_PROPERTIES;

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
        this.uiState = useState(this.env.ui);

        /** @type {ReturnType<typeof this.getFilteredEvents>[0]} */
        this.availableEventTypes;
        /** @type {ReturnType<typeof this.getFilteredEvents>[1]} */
        this.filteredEvents;

        onWillRender(() => {
            [this.availableEventTypes, this.filteredEvents] = this.getFilteredEvents();
        });
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
     * @returns {[Record<CaseEventType, number>, WeakMap<CaseResult, CaseEvent[]>]}
     */
    getFilteredEvents() {
        // Spawn object with all keys to keep them consistently ordered accross
        // all test results
        const availableEventTypes = $fromEntries($keys(EVENT_PROPERTIES).map((k) => [k, null]));
        const filteredEvents = new WeakMap();
        for (const result of this.results) {
            const filteredResultEvents = [];
            for (const event of result.events) {
                const sType = CASE_EVENT_TYPES_INVERSE[event.type];
                availableEventTypes[sType] ||= this.uiState.displayedEvents & event.type;
                if (availableEventTypes[sType]) {
                    filteredResultEvents.push(event);
                }
            }
            filteredEvents.set(result, filteredResultEvents);
        }
        for (const type in availableEventTypes) {
            if (availableEventTypes[type] === null) {
                delete availableEventTypes[type];
            }
        }
        return [availableEventTypes, filteredEvents];
    }

    /**
     * @param {number} nType
     */
    getTypeName(nType) {
        return CASE_EVENT_TYPES_INVERSE[nType];
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

    /**
     * @param {import("../core/expect").CaseEventType} sType
     */
    toggleEventType(sType) {
        const nType = CASE_EVENT_TYPES[sType];
        if (this.uiState.displayedEvents & nType) {
            this.uiState.displayedEvents &= ~nType;
        } else {
            this.uiState.displayedEvents |= nType;
        }
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;

        if (!("assertion" in this.availableEventTypes || "error" in this.availableEventTypes)) {
            // If the test result doesn't have "assertion" nor "error" events:
            // -> automatically toggle the first event type found as to not display
            //  empty results on open.
            const firstResultWithEvent = this.results.find((result) => result.events.length);
            if (firstResultWithEvent) {
                this.uiState.displayedEvents |= firstResultWithEvent.events[0].type;
            }
        }
    }
}
