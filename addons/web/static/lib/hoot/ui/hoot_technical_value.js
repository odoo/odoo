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
import { isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { Markup, toExplicitString } from "../hoot_utils";

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
    console: { log: $log },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * Compacted version of {@link owlXml} removing all whitespace between tags.
 *
 * @type {typeof String.raw}
 */
const xml = (template, ...substitutions) =>
    owlXml({
        raw: String.raw(template, ...substitutions)
            .replace(/>\s+/g, ">")
            .replace(/\s+</g, "<"),
    });

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
        <t t-if="isMarkup">
            <t t-if="value.technical">
                <pre class="hoot-technical" t-att-class="value.className">
                    <t t-foreach="value.content" t-as="subValue" t-key="subValue_index">
                        <HootTechnicalValue value="subValue" />
                    </t>
                </pre>
            </t>
            <t t-else="">
                <t t-if="value.tagName === 't'" t-esc="value.content" />
                <t t-else="" t-tag="value.tagName" t-att-class="value.className" t-esc="value.content" />
            </t>
        </t>
        <t t-elif="isNode(value)">
            <t t-set="elParts" t-value="toSelector(value, { object: true })" />
            <button class="hoot-html" t-on-click="log">
                <t>&lt;<t t-esc="elParts.tag" /></t>
                <t t-if="elParts.id">
                    <span class="hoot-html-id" t-esc="elParts.id" />
                </t>
                <t t-if="elParts.class">
                    <span class="hoot-html-class" t-esc="elParts.class" />
                </t>
                <t>/&gt;</t>
            </button>
        </t>
        <t t-elif="value and typeof value === 'object'">
            <t t-set="labelSize" t-value="getLabelAndSize()" />
            <pre class="hoot-technical">
                <button class="hoot-object inline-flex items-center gap-1 me-1" t-on-click="onClick">
                    <t t-if="labelSize[1] > 0">
                        <i
                            class="fa fa-caret-right flex justify-center w-2 transition"
                            t-att-class="{ 'rotate-90': state.open }"
                        />
                    </t>
                    <t t-esc="labelSize[0]" />
                    <t t-if="state.promiseState">
                        &lt;
                        <span class="text-muted" t-esc="state.promiseState[0]" />
                        <t t-if="state.promiseState[0] !== 'pending'">
                            : <HootTechnicalValue value="state.promiseState[1]" />
                        </t>
                        &gt;
                    </t>
                    <t t-elif="labelSize[1] !== null">
                        (<t t-esc="labelSize[1]" />)
                    </t>
                </button>
                <t t-if="state.open and labelSize[1] > 0">
                    <t t-if="isIterable(value)">
                        <t>[</t>
                        <ul class="ps-4">
                            <t t-foreach="value" t-as="subValue" t-key="subValue_index">
                                <li class="flex">
                                    <HootTechnicalValue value="subValue" />
                                    <t t-esc="displayComma(subValue)" />
                                </li>
                            </t>
                        </ul>
                        <t>]</t>
                    </t>
                    <t t-else="">
                        <t>{</t>
                        <ul class="ps-4">
                            <t t-foreach="value" t-as="key" t-key="key">
                                <li class="flex">
                                    <span class="hoot-key" t-esc="key" />
                                    <span class="me-1">:</span>
                                    <HootTechnicalValue value="value[key]" />
                                    <t t-esc="displayComma(value[key])" />
                                </li>
                            </t>
                        </ul>
                        <t>}</t>
                    </t>
                </t>
            </pre>
        </t>
        <t t-else="">
            <span t-attf-class="hoot-{{ typeof value }}">
                <t t-if="typeof value === 'string'">
                    <t>"</t><t t-esc="explicitValue" /><t>"</t>
                </t>
                <t t-else="" t-esc="explicitValue" />
            </span>
        </t>
    `;

    toSelector = toSelector;
    isIterable = isIterable;
    isNode = isNode;

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
        if (this.value instanceof Date) {
            return [this.value.toISOString(), null];
        }
        if (this.value instanceof RegExp) {
            return [String(this.value), null];
        }
        return [this.value.constructor.name, this.getSize()];
    }

    getSize() {
        for (const Class of INVARIABLE_OBJECTS) {
            if (this.value instanceof Class) {
                return null;
            }
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
        $log(this.value);
    }

    wrapPromiseValue(promise) {
        if (!(promise instanceof Promise)) {
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
