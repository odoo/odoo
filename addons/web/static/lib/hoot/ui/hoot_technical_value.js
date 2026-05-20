/** @odoo-module */

import { Component, xml as owlXml, props, signal, types as t, toRaw } from "@odoo/owl";
import { isNode, toSelector } from "@web/../lib/hoot-dom/helpers/dom";
import { isInstanceOf, isIterable, isPromise } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { logger } from "../core/logger";
import {
    getTypeOf,
    isSafe,
    Markup,
    S_ANY,
    S_CIRCULAR,
    S_NONE,
    stringify,
    toExplicitString,
} from "../hoot_utils";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { keys: $keys },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {unknown} value
 */
function makePromiseWrapperSignal(value) {
    if (!isPromise(value)) {
        return null;
    }

    const promiseSignal = signal(["pending", null], {
        type: t.tuple([t.selection(["pending", "fulfilled", "rejected"]), t.any()]),
    });

    Promise.resolve(value).then(
        (value) => promiseSignal.set(["fulfilled", value]),
        (reason) => promiseSignal.set(["rejected", reason])
    );

    return promiseSignal;
}

/**
 * Compacted version of {@link owlXml} removing all whitespace between tags.
 *
 * @type {typeof String.raw}
 */
function xml(template, ...substitutions) {
    return owlXml({
        raw: String.raw(template, ...substitutions)
            .replace(/>\s+/g, ">")
            .replace(/\s+</g, "<"),
    });
}

const INVARIABLE_OBJECTS = [Promise, RegExp];
const SPECIAL_SYMBOLS = [S_ANY, S_CIRCULAR, S_NONE];

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class HootTechnicalValue extends Component {
    static components = { HootTechnicalValue };
    static template = xml`
        <t t-if="this.isMarkup(this.rawValue)">
            <t t-if="this.rawValue.type === 'technical'">
                <pre class="hoot-technical" t-att-class="this.rawValue.className">
                    <t t-foreach="this.rawValue.content" t-as="subValue" t-key="subValue_index">
                        <HootTechnicalValue value="subValue" />
                    </t>
                </pre>
            </t>
            <t t-else="">
                <t t-if="this.rawValue.tagName === 't'" t-out="this.rawValue.content" />
                <t
                    t-else=""
                    t-tag="this.rawValue.tagName"
                    t-att-class="this.rawValue.className"
                    t-out="this.rawValue.content"
                />
            </t>
        </t>
        <t t-elif="this.isNode(this.rawValue)">
            <t t-set="elParts" t-value="this.toSelector(this.rawValue, { object: true })" />
            <button
                class="hoot-html"
                t-on-click.stop="this.onClick"
            >
                <t>&lt;<t t-out="elParts.tag" /></t>
                <t t-if="elParts.id">
                    <span class="hoot-html-id" t-out="elParts.id" />
                </t>
                <t t-if="elParts.class">
                    <span class="hoot-html-class" t-out="elParts.class" />
                </t>
                <t>/&gt;</t>
            </button>
        </t>
        <t t-elif="this.isSpecialSymbol()">
            <span class="italic">
                &lt;<t t-out="this.symbolValue()" />&gt;
            </span>
        </t>
        <t t-elif="typeof this.rawValue === 'symbol'">
            <span>
                Symbol(<span class="hoot-string" t-out="this.stringify(this.symbolValue())" />)
            </span>
        </t>
        <t t-elif="this.rawValue and typeof this.rawValue === 'object'">
            <t t-set="labelSize" t-value="this.getLabelAndSize()" />
            <pre class="hoot-technical">
                <button
                    class="hoot-object inline-flex items-center gap-1 me-1"
                    t-on-click.stop="this.onClick"
                >
                    <t t-if="labelSize[1] > 0">
                        <i
                            class="fa fa-caret-right"
                            t-att-class="{ 'rotate-90': this.isOpen() }"
                        />
                    </t>
                    <t t-out="labelSize[0]" />
                    <t t-if="this.promiseState">
                        &lt;
                        <span class="text-gray" t-out="this.promiseState()[0]" />
                        <t t-if="this.promiseState()[0] !== 'pending'">
                            : <HootTechnicalValue value="this.promiseState()[1]" />
                        </t>
                        &gt;
                    </t>
                    <t t-elif="labelSize[1] !== null">
                        (<t t-out="labelSize[1]" />)
                    </t>
                </button>
                <t t-if="this.isOpen() and labelSize[1] > 0">
                    <t t-if="this.isIterable(this.rawValue)">
                        <t>[</t>
                        <ul class="ps-4">
                            <t t-foreach="this.rawValue" t-as="subValue" t-key="subValue_index">
                                <li class="flex">
                                    <HootTechnicalValue value="subValue" />
                                    <t t-out="this.displayComma(subValue)" />
                                </li>
                            </t>
                        </ul>
                        <t>]</t>
                    </t>
                    <t t-else="">
                        <t>{</t>
                        <ul class="ps-4">
                            <t t-foreach="this.rawValue" t-as="key" t-key="key">
                                <li class="flex">
                                    <span class="hoot-key" t-out="key" />
                                    <span class="me-1">:</span>
                                    <HootTechnicalValue value="this.rawValue[key]" />
                                    <t t-out="this.displayComma(this.rawValue[key])" />
                                </li>
                            </t>
                        </ul>
                        <t>}</t>
                    </t>
                </t>
            </pre>
        </t>
        <t t-else="">
            <span t-attf-class="hoot-{{ this.getTypeOf(this.rawValue) }}">
                <t t-out="typeof this.rawValue === 'string'
                    ? this.stringify(this.toExplicitString(this.rawValue))
                    : this.toExplicitString(this.rawValue)"
                />
            </span>
        </t>
    `;

    // Props & plugins
    props = props({
        "value?": t.any(),
    });

    rawValue = toRaw(this.props.value);

    // Reactive values
    isOpen = signal(false, { type: t.boolean() });
    promiseState = makePromiseWrapperSignal(this.rawValue);

    // Other members
    logged = false;

    getTypeOf = getTypeOf;
    isIterable = isIterable;
    isMarkup = Markup.isMarkup;
    isNode = isNode;
    stringify = stringify;
    toExplicitString = toExplicitString;
    toSelector = toSelector;

    /**
     * @param {unknown} value
     */
    displayComma(value) {
        return value && typeof value === "object" ? "" : ",";
    }

    getLabelAndSize() {
        if (isInstanceOf(this.rawValue, Date)) {
            return [this.rawValue.toISOString(), null];
        }
        if (isInstanceOf(this.rawValue, RegExp)) {
            return [String(this.rawValue), null];
        }
        return [this.rawValue.constructor.name, this.getSize()];
    }

    getSize() {
        for (const Class of INVARIABLE_OBJECTS) {
            if (isInstanceOf(this.rawValue, Class)) {
                return null;
            }
        }
        if (!isSafe(this.rawValue)) {
            return 0;
        }
        const values = isIterable(this.rawValue) ? [...this.rawValue] : $keys(this.rawValue);
        return values.length;
    }

    isSpecialSymbol() {
        return SPECIAL_SYMBOLS.includes(this.rawValue);
    }

    onClick() {
        this.isOpen.set(!this.isOpen());

        if (this.logged) {
            return;
        }
        this.logged = true;
        logger.debug(this.rawValue);
    }

    symbolValue() {
        return this.rawValue.toString().slice(7, -1);
    }
}
