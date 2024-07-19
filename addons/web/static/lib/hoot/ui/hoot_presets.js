/** @odoo-module */

import { Component, useRef, useState, xml } from "@odoo/owl";
import { refresh } from "../core/url";
import { useWindowListener } from "../hoot_utils";

/**
 * @typedef {{
 * }} HootPresetsProps
 */

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootPresetsProps, import("../hoot").Environment>} */
export class HootPresets extends Component {
    static props = {};
    static template = xml`
        <div class="${HootPresets.name} relative" t-ref="root">
            <t t-set="hasCorrectViewPort" t-value="env.runner.checkPresetForViewPort()" />
            <t t-set="highlightClass" t-value="hasCorrectViewPort ? 'text-primary' : 'text-abort'" />
            <button
                t-ref="toggler"
                class="flex rounded p-2 transition-colors"
                t-att-class="highlightClass"
                t-att-title="hasCorrectViewPort ? 'Presets' : 'Invalid viewport (check console)'"
            >
                <i
                    class="fa font-bold w-4 h-4 flex items-center justify-center"
                    t-att-class="getPresetIcon()"
                />
            </button>
            <t t-if="state.open">
                <form
                    class="hoot-config-dropdown animate-slide-down bg-base text-base mt-1 absolute flex flex-col end-0 px-2 py-3 shadow rounded shadow z-2"
                    t-on-submit.prevent="refresh"
                >
                    <t t-foreach="env.runner.presets.entries()" t-as="preset" t-key="preset[0]">
                        <label
                            class="cursor-pointer flex items-center gap-1 p-1 hover:bg-gray-300 dark:hover:bg-gray-700"
                            t-att-title="preset[0] and 'Use the ' + preset[1].label + ' preset'"
                        >
                            <input
                                type="checkbox"
                                class="appearance-none border border-primary rounded-sm w-4 h-4"
                                t-att-checked="config.preset === preset[0]"
                                t-on-change="(ev) => this.onPresetChange(preset[0], ev)"
                            />
                            <t t-if="preset[1].icon">
                                <i
                                    class="fa font-bold w-4 h-4 flex items-center justify-center"
                                    t-attf-class="{{ preset[1].icon }} {{ config.preset === preset[0] ? highlightClass : '' }}"
                                />
                            </t>
                            <span
                                t-att-class="config.preset === preset[0] and highlightClass"
                                t-esc="preset[1].label"
                            />
                        </label>
                    </t>

                    <button class="flex bg-btn justify-center rounded mt-1 p-1 transition-colors">
                        Apply and refresh
                    </button>
                </form>
            </t>
        </div>
    `;

    refresh = refresh;

    setup() {
        const { runner } = this.env;
        this.rootRef = useRef("root");
        this.togglerRef = useRef("toggler");
        this.config = useState(runner.config);
        this.state = useState({ open: false });
        this.runnerState = useState(runner.state);

        useWindowListener("keydown", (ev) => {
            if (this.state.open && ev.key === "Escape") {
                ev.preventDefault();
                this.state.open = false;
            }
        });
        useWindowListener("click", (ev) => {
            const path = ev.composedPath();
            if (!path.includes(this.rootRef.el)) {
                this.state.open = false;
            } else if (path.includes(this.togglerRef.el)) {
                this.state.open = !this.state.open;
            }
        });
    }

    getPresetIcon() {
        const activePreset = this.env.runner.presets.get(this.config.preset);
        return activePreset?.icon || "fa-check-square-o";
    }

    onPresetChange(presetId, ev) {
        if (ev.target.checked) {
            this.config.preset = presetId;
        } else {
            this.config.preset = "";
            if (presetId === "") {
                ev.target.checked = true;
            }
        }
    }
}
