/** @odoo-module */

import {
    Component,
    onWillRender,
    onWillUpdateProps,
    xml as owlXml,
    toRaw,
    useState,
} from "@odoo/owl";
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

/**
 * @typedef {{
 *  value?: any;
 * }} TechnicalValueProps
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

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<TechnicalValueProps, import("../hoot").Environment>} */
export class HootTechnicalValue extends Component {
    static components = { HootTechnicalValue };

    static props = {
        value: { optional: true },
    };

    static template = xml`
        <t t-if="this.isMarkup">
            <t t-if="this.value.type === 'technical'">
                <pre class="hoot-technical" t-att-class="this.value.className">
                    <t t-foreach="this.value.content" t-as="subValue" t-key="subValue_index">
                        <HootTechnicalValue value="subValue" />
                    </t>
                </pre>
            </t>
            <t t-else="">
                <t t-if="this.value.tagName === 't'" t-out="this.value.content" />
                <t t-else="" t-tag="this.value.tagName" t-att-class="this.value.className" t-out="this.value.content" />
            </t>
        </t>
        <t t-elif="this.isNode(this.value)">
            <t t-set="elParts" t-value="this.toSelector(this.value, { object: true })" />
            <button
                class="hoot-html"
                t-on-click.stop="this.log"
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
        <t t-elif="this.SPECIAL_SYMBOLS.includes(this.value)">
            <span class="italic">
                &lt;<t t-out="this.symbolValue(this.value)" />&gt;
            </span>
        </t>
        <t t-elif="typeof this.value === 'symbol'">
            <span>
                Symbol(<span class="hoot-string" t-out="this.stringify(this.symbolValue(this.value))" />)
            </span>
        </t>
        <t t-elif="this.value and typeof this.value === 'object'">
            <t t-set="labelSize" t-value="this.getLabelAndSize()" />
            <pre class="hoot-technical">
                <button
                    class="hoot-object inline-flex items-center gap-1 me-1"
                    t-on-click.stop="this.onClick"
                >
                    <t t-if="labelSize[1] > 0">
                        <i
                            class="fa fa-caret-right"
                            t-att-class="{ 'rotate-90': this.state.open }"
                        />
                    </t>
                    <t t-out="labelSize[0]" />
                    <t t-if="this.state.promiseState">
                        &lt;
                        <span class="text-gray" t-out="this.state.promiseState[0]" />
                        <t t-if="this.state.promiseState[0] !== 'pending'">
                            : <HootTechnicalValue value="this.state.promiseState[1]" />
                        </t>
                        &gt;
                    </t>
                    <t t-elif="labelSize[1] !== null">
                        (<t t-out="labelSize[1]" />)
                    </t>
                </button>
                <t t-if="this.state.open and labelSize[1] > 0">
                    <t t-if="this.isIterable(this.value)">
                        <t>[</t>
                        <ul class="ps-4">
                            <t t-foreach="this.value" t-as="subValue" t-key="subValue_index">
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
                            <t t-foreach="this.value" t-as="key" t-key="key">
                                <li class="flex">
                                    <span class="hoot-key" t-out="key" />
                                    <span class="me-1">:</span>
                                    <HootTechnicalValue value="this.value[key]" />
                                    <t t-out="this.displayComma(this.value[key])" />
                                </li>
                            </t>
                        </ul>
                        <t>}</t>
                    </t>
                </t>
            </pre>
        </t>
        <t t-else="">
            <span t-attf-class="hoot-{{ this.getTypeOf(this.value) }}">
                <t t-out="typeof this.value === 'string' ? this.stringify(this.explicitValue) : this.explicitValue" />
            </span>
        </t>
    `;

    getTypeOf = getTypeOf;
    isIterable = isIterable;
    isNode = isNode;
    stringify = stringify;
    toSelector = toSelector;

    SPECIAL_SYMBOLS = [S_ANY, S_CIRCULAR, S_NONE];

    get explicitValue() {
        return toExplicitString(this.value);
    }

    setup() {
        this.logged = false;
        this.state = useState({
            open: false,
            promiseState: null,
        });
        this.wrapPromiseValue(this.props.value);

        onWillRender(() => {
            this.isMarkup = Markup.isMarkup(this.props.value);
            this.value = toRaw(this.props.value);
            this.isSafe = isSafe(this.value);
        });
        onWillUpdateProps((nextProps) => {
            this.state.open = false;
            this.wrapPromiseValue(nextProps.value);
        });
    }

    onClick() {
        this.log(this.value);
        this.state.open = !this.state.open;
    }

    getLabelAndSize() {
        if (isInstanceOf(this.value, Date)) {
            return [this.value.toISOString(), null];
        }
        if (isInstanceOf(this.value, RegExp)) {
            return [String(this.value), null];
        }
        return [this.value.constructor.name, this.getSize()];
    }

    getSize() {
        for (const Class of INVARIABLE_OBJECTS) {
            if (isInstanceOf(this.value, Class)) {
                return null;
            }
        }
        if (!this.isSafe) {
            return 0;
        }
        const values = isIterable(this.value) ? [...this.value] : $keys(this.value);
        return values.length;
    }

    displayComma(value) {
        return value && typeof value === "object" ? "" : ",";
    }

    log() {
        if (this.logged) {
            return;
        }
        this.logged = true;
        logger.debug(this.value);
    }

    /**
     * @param {Symbol} symbol
     */
    symbolValue(symbol) {
        return symbol.toString().slice(7, -1);
    }

    wrapPromiseValue(promise) {
        if (!isPromise(promise)) {
            return;
        }
        this.state.promiseState = ["pending", null];
        Promise.resolve(promise).then(
            (value) => {
                this.state.promiseState = ["fulfilled", value];
                return value;
            },
            (reason) => {
                this.state.promiseState = ["rejected", reason];
                throw reason;
            }
        );
    }
}
