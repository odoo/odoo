/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { FILTER_KEYS, FILTER_SCHEMA } from "../core/config";
import { createUrlFromId } from "../core/url";
import { INCLUDE_LEVEL } from "../hoot_utils";

/**
 * @typedef {{
 *  class?: string;
 *  id?: string;
 *  onClick?: (event: PointerEvent) => any;
 *  options?: import("../core/url").CreateUrlFromIdOptions;
 *  slots: { default: any };
 *  style?: string;
 *  target?: string;
 *  title?: string;
 *  type?: import("../core/config").SearchFilter;
 * }} HootLinkProps
 */

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Link component which computes its href lazily (i.e. on focus or pointerenter).
 *
 * @extends {Component<HootLinkProps, import("../hoot").Environment>}
 */
export class HootLink extends Component {
    static template = xml`
        <a
            t-att-class="props.class"
            t-att-href="state.href"
            t-att-target="props.target"
            t-att-title="props.title"
            t-att-style="props.style"
            t-on-click.stop="onClick"
            t-on-focus="updateHref"
            t-on-pointerenter="updateHref"
        >
            <t t-slot="default" />
        </a>
    `;
    static props = {
        class: { type: String, optional: true },
        id: { type: [String, { type: Array, element: String }], optional: true },
        options: {
            type: Object,
            shape: {
                debug: { type: Boolean, optional: true },
                ignore: { type: Boolean, optional: true },
            },
            optional: true,
        },
        slots: {
            type: Object,
            shape: {
                default: { type: Object, optional: true },
            },
        },
        style: { type: String, optional: true },
        target: { type: String, optional: true },
        title: { type: String, optional: true },
        type: { type: FILTER_KEYS.map((value) => ({ value })), optional: true },
    };

    setup() {
        this.state = useState({ href: "#" });
    }

    /**
     * @param {PointerEvent} ev
     */
    onClick(ev) {
        if (ev.altKey) {
            const { includeSpecs } = this.env.runner.state;
            const { id, type, options } = this.props;
            if (!(type in FILTER_SCHEMA)) {
                return;
            }

            ev.preventDefault();

            const targetValue = options?.ignore ? -INCLUDE_LEVEL.url : +INCLUDE_LEVEL.url;
            const finalValue = includeSpecs[type][id] === targetValue ? 0 : targetValue;
            this.env.runner.include(type, id, finalValue);
        } else {
            this.props.onClick?.(ev);
        }
    }

    updateHref() {
        const { id, type, options } = this.props;
        this.state.href = createUrlFromId(id, type, options);
    }
}
