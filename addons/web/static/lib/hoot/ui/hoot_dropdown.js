/** @odoo-module */

import { Component, useRef, useState, xml } from "@odoo/owl";
import { useAutofocus, useHootKey, useWindowListener } from "../hoot_utils";

/**
 * @typedef {{
 *  buttonClassName?: string:
 *  className?: string:
 *  slots: Record<string, any>;
 * }} HootDropdownProps
 */

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootDropdownProps, import("../hoot").Environment>} */
export class HootDropdown extends Component {
    static template = xml`
        <div class="${HootDropdown.name} relative" t-att-class="props.className" t-ref="root">
            <button
                t-ref="toggler"
                class="flex rounded p-2 transition-colors"
                t-att-class="props.buttonClassName"
            >
                <t t-slot="toggler" open="state.open" />
            </button>
            <t t-if="state.open">
                <div
                    class="
                        hoot-dropdown absolute animate-slide-down
                        flex flex-col end-0 p-3 gap-2
                        bg-base text-base mt-1 shadow rounded z-2"
                >
                    <button class="fixed end-2 top-2 p-1 text-rose sm:hidden" t-on-click="() => state.open = false">
                        <i class="fa fa-times w-5 h-5" />
                    </button>
                    <t t-slot="menu" open="state.open" />
                </div>
            </t>
        </div>
    `;
    static props = {
        buttonClassName: { type: String, optional: true },
        className: { type: String, optional: true },
        slots: {
            type: Object,
            shape: {
                toggler: Object,
                menu: Object,
            },
        },
    };

    setup() {
        this.rootRef = useRef("root");
        this.togglerRef = useRef("toggler");
        this.state = useState({
            open: false,
        });

        useAutofocus(this.rootRef);
        useHootKey(["Escape"], this.close);
        useWindowListener(
            "click",
            (ev) => {
                const path = ev.composedPath();
                if (!path.includes(this.rootRef.el)) {
                    this.state.open = false;
                } else if (path.includes(this.togglerRef.el)) {
                    this.state.open = !this.state.open;
                }
            },
            { capture: true }
        );
    }

    /**
     * @param {KeyboardEvent} ev
     */
    close(ev) {
        if (this.state.open) {
            ev.preventDefault();
            this.state.open = false;
        }
    }
}
