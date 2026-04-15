/** @odoo-module */

import { Component, props, signal, types as t, xml } from "@odoo/owl";
import { FILTER_SCHEMA } from "../core/config";
import { createUrlFromId } from "../core/url";
import { ensureArray, INCLUDE_LEVEL } from "../hoot_utils";
import { getRunnerPlugin } from "./runner_plugin";

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
 */
export class HootLink extends Component {
    static template = xml`
        <a
            t-att-class="this.props.class"
            t-att-href="this.href()"
            t-att-target="this.props.target"
            t-att-title="this.props.title"
            t-att-style="this.props.style"
            t-on-click.stop="this.onClick"
            t-on-focus="this.updateHref"
            t-on-pointerenter="this.updateHref"
        >
            <t t-call-slot="default" />
        </a>
    `;

    // Props & plugins
    props = props({
        "class?": t.string(),
        "ids?": t.record(t.or([t.string(), t.array(t.string())])),
        "onClick?": t.function([t.instanceOf(PointerEvent)]),
        "options?": t.object({
            "debug?": t.boolean(),
            "ignore?": t.boolean(),
        }),
        slots: t.object(["default"]),
        "style?": t.string(),
        "target?": t.string(),
        "title?": t.string(),
    });

    runner = getRunnerPlugin();

    // Reactive values
    href = signal("#", { type: t.string() });

    /**
     * @param {PointerEvent} ev
     */
    onClick(ev) {
        const { ids, options } = this.props;
        if (ids && ev.altKey) {
            const { includeSpecs } = this.runner;
            let appliedFilter = false;
            for (const [type, idOrIds] of $entries(ids)) {
                if (!(type in FILTER_SCHEMA)) {
                    continue;
                }
                const targetValue = options?.ignore ? -INCLUDE_LEVEL.url : +INCLUDE_LEVEL.url;
                for (const id of ensureArray(idOrIds)) {
                    const finalValue = includeSpecs[type][id] === targetValue ? 0 : targetValue;
                    this.runner.include(type, id, finalValue);
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
        const simplifiedIds = this.runner.simplifyUrlIds(ids);
        this.href.set(createUrlFromId(simplifiedIds, options));
    }
}
