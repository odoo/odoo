/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { FILTER_SCHEMA } from "../core/config";
import { createUrlFromId } from "../core/url";
import { ensureArray, INCLUDE_LEVEL } from "../hoot_utils";

/**
 * @typedef {{
 *  class?: string;
 *  ids?: Record<import("../core/config").SearchFilter, string[]>;
 *  onClick?: (event: PointerEvent) => any;
 *  options?: import("../core/url").CreateUrlFromIdOptions;
 *  slots: { default: any };
 *  style?: string;
 *  target?: string;
 *  title?: string;
 * }} HootLinkProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { entries: $entries },
} = globalThis;

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
        ids: {
            type: Object,
            values: [String, { type: Array, element: String }],
            optional: true,
        },
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
    };

    setup() {
        this.state = useState({ href: "#" });
    }

    /**
     * @param {PointerEvent} ev
     */
    onClick(ev) {
        const { ids, options } = this.props;
        if (ids && ev.altKey) {
            const { includeSpecs } = this.env.runner.state;
            let appliedFilter = false;
            for (const [type, idOrIds] of $entries(ids)) {
                if (!(type in FILTER_SCHEMA)) {
                    continue;
                }
                const targetValue = options?.ignore ? -INCLUDE_LEVEL.url : +INCLUDE_LEVEL.url;
                for (const id of ensureArray(idOrIds)) {
                    const finalValue = includeSpecs[type][id] === targetValue ? 0 : targetValue;
                    this.env.runner.include(type, id, finalValue);
                    appliedFilter = true;
                }
            }

            if (appliedFilter) {
                ev.preventDefault();
            }
        } else {
            this.props.onClick?.(ev);
        }
    }

    updateHref() {
        const { ids, options } = this.props;
        const simplifiedIds = this.env.runner.simplifyUrlIds(ids);
        this.state.href = createUrlFromId(simplifiedIds, options);
    }
}
