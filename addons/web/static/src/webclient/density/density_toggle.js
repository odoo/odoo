// @ts-check

/** @module @web/webclient/density/density_toggle - Systray toggle that cycles through content density modes (default/compact/condensed) */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const DENSITY_META = {
    default: { icon: "fa fa-expand", next: "compact", label: "Default" },
    compact: { icon: "fa fa-compress", next: "condensed", label: "Compact" },
    condensed: { icon: "fa fa-bars", next: "default", label: "Condensed" },
};

/**
 * Systray toggle that cycles through content density modes.
 *
 * Cycles: default (cozy) → compact → condensed → default.
 * No page reload — CSS class toggle is instant.
 */
export class DensityToggle extends Component {
    static template = "web.DensityToggle";
    static props = {};

    /** Initialize density service and reactive state. */
    setup() {
        this.densityService = useService("density");
        this.state = useState({ density: this.densityService.current });
    }

    /** @returns {string} Font Awesome icon class for the current density. */
    get icon() {
        return DENSITY_META[this.state.density]?.icon ?? "fa fa-expand";
    }

    /** @returns {string} Tooltip text describing current density and next on click. */
    get title() {
        const meta = DENSITY_META[this.state.density];
        return `${meta?.label ?? "Default"} density (click for ${meta?.next ?? "compact"})`;
    }

    /** Cycle to the next density mode and update reactive state. */
    async toggle() {
        await this.densityService.cycle();
        this.state.density = this.densityService.current;
    }
}

export const densityToggle = { Component: DensityToggle };

registry.category("systray").add("web.density_toggle", densityToggle, { sequence: 6 });
