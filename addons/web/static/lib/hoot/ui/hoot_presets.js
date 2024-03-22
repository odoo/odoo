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
            <button
                t-ref="toggler"
                class="flex text-primary rounded p-2 transition-colors"
                title="Presets"
            >
                <i
                    class="fa font-bold w-4 h-4 flex items-center justify-center"
                    t-att-class="activePreset?.icon or 'fa-check-square-o'"
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
                        >
                            <input
                                type="checkbox"
                                class="appearance-none border border-primary rounded-sm w-4 h-4"
                                t-att-checked="config.preset === preset[0]"
                                t-on-change="() => config.preset = preset[0]"
                            />
                            <t t-if="preset[1].icon">
                                <i
                                    class="fa font-bold w-4 h-4 flex items-center justify-center"
                                    t-att-class="preset[1].icon"
                                />
                            </t>
                            <span t-esc="preset[1].label" />
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

    get activePreset() {
        return this.env.runner.presets.get(this.config.preset);
    }

    setup() {
        this.rootRef = useRef("root");
        this.togglerRef = useRef("toggler");
        this.config = useState(this.env.runner.config);
        this.state = useState({ open: false });

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
}
