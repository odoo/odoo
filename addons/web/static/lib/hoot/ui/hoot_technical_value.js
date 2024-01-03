/** @odoo-module */

import { Component, xml as owlXml, toRaw, useState } from "@odoo/owl";
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

const { Object, Set, console } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @template T
 * @param {T} value
 */
const deepCopy = (value) => {
    if (value && typeof value === "object") {
        if (isNode(value)) {
            // Nodes
            return value.cloneNode(true);
        } else if (isIterable(value)) {
            // Iterables
            const copy = [...value].map(deepCopy);
            if (value instanceof Set || value instanceof Map) {
                return new value.constructor(copy);
            } else {
                return copy;
            }
        } else if (value instanceof Markup) {
            // Markup helpers
            value.content = deepCopy(value.content);
            return value;
        } else if (value instanceof Date) {
            // Dates
            return new Date(value);
        } else {
            // Other objects
            return JSON.parse(JSON.stringify(value));
        }
    }
    return value;
};

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
                <pre class="hoot-technical m-0" t-att-class="value.className">
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
                <t>&lt;</t>
                    <span class="hoot-html-tag" t-esc="elParts.tag" />
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
            <pre class="hoot-technical m-0">
                <button class="hoot-object-type inline-flex items-center" t-on-click="onClick">
                    <t t-esc="getConstructor()" />
                    <i t-attf-class="fa fa-caret-{{ state.open ? 'up' : 'down' }}" />
                </button>
                <t> </t>
                <t t-if="state.open">
                    <t t-if="isIterable(value)">
                        <t>[</t>
                        <ul class="ps-3">
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
                        <ul class="ps-3">
                            <t t-foreach="value" t-as="key" t-key="key">
                                <li class="flex">
                                    <span class="hoot-key" t-esc="key" />: <HootTechnicalValue value="value[key]" />
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
                    <t>"</t><t t-esc="value" /><t>"</t>
                </t>
                <t t-else="" t-esc="toExplicitString(value)" />
            </span>
        </t>
    `;

    toSelector = toSelector;
    isIterable = isIterable;
    isNode = isNode;
    toExplicitString = toExplicitString;

    setup() {
        this.logged = false;
        this.isMarkup = this.props.value instanceof Markup;
        this.value = deepCopy(toRaw(this.props.value));
        this.state = useState({ open: false });
    }

    onClick() {
        this.log(this.value);
        this.state.open = !this.state.open;
    }

    getConstructor() {
        const { name } = this.value.constructor;
        return `${name}(${Object.keys(this.value).length})`;
    }

    displayComma(value) {
        return value && typeof value === "object" ? "" : ",";
    }

    log() {
        if (this.logged) {
            return;
        }
        this.logged = true;
        console.log(this.value);
    }
}
