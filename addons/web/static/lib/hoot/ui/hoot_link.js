/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { FILTER_KEYS } from "../core/config";
import { EXCLUDE_PREFIX, createURL, urlParams } from "../core/url";
import { ensureArray } from "../hoot_utils";

/**
 * @typedef {{
 *  class?: string;
 *  disabled?: boolean;
 *  id?: string;
 *  options?: {
 *      debug?: boolean;
 *      ignore?: boolean;
 *  };
 *  slots: { default: any };
 *  style?: string;
 *  target?: string;
 *  title?: string;
 *  type?: keyof DEFAULT_FILTERS;
 * }} HootLinkProps
 */

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
            t-att-disabled="props.disabled"
            t-on-focus="computeHref"
            t-on-pointerenter="computeHref"
        >
            <t t-slot="default" />
        </a>
    `;
    static props = {
        class: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
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

    computeHref() {
        const clearAll = () => Object.keys(nextParams).forEach((key) => nextParams[key].clear());

        const { type, id, options } = this.props;
        const ids = ensureArray(id);
        const nextParams = Object.fromEntries(
            FILTER_KEYS.map((k) => [k, new Set(urlParams[k] || [])])
        );
        if (urlParams.filter) {
            nextParams.filter = new Set([urlParams.filter]);
        }

        switch (type) {
            case "suite": {
                if (options?.ignore) {
                    for (const id of ids) {
                        const exludedId = EXCLUDE_PREFIX + id;
                        if (nextParams.suite.has(exludedId)) {
                            nextParams.suite.delete(exludedId);
                        } else {
                            nextParams.suite.add(exludedId);
                        }
                    }
                } else {
                    clearAll();
                    for (const id of ids) {
                        nextParams.suite.add(id);
                    }
                }
                break;
            }
            case "tag": {
                if (options?.ignore) {
                    for (const id of ids) {
                        const exludedId = EXCLUDE_PREFIX + id;
                        if (nextParams.tag.has(exludedId)) {
                            nextParams.tag.delete(exludedId);
                        } else {
                            nextParams.tag.add(exludedId);
                        }
                    }
                } else {
                    clearAll();
                    for (const id of ids) {
                        nextParams.tag.add(id);
                    }
                }
                break;
            }
            case "test": {
                if (options?.ignore) {
                    for (const id of ids) {
                        const exludedId = EXCLUDE_PREFIX + id;
                        if (nextParams.test.has(exludedId)) {
                            nextParams.test.delete(exludedId);
                        } else {
                            nextParams.test.add(exludedId);
                        }
                    }
                } else {
                    clearAll();
                    for (const id of ids) {
                        nextParams.test.add(id);
                    }
                }
                break;
            }
            default: {
                clearAll();
            }
        }

        for (const key in nextParams) {
            if (!nextParams[key].size) {
                nextParams[key] = null;
            }
        }

        nextParams.debugTest = options?.debug ? true : null;

        this.state.href = createURL(nextParams);
    }
}
