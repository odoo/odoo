/** @odoo-module */

import { Component, props, signal, t, xml } from "@odoo/owl";
import { useAutofocus, useHootKey, useWindowListener } from "../hoot_utils";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class HootDropdown extends Component {
    static template = xml`
        <div class="${HootDropdown.name} relative" t-att-class="this.props.className" t-ref="this.rootRef">
            <button
                t-ref="this.togglerRef"
                class="flex rounded p-2 transition-colors"
                t-att-class="this.props.buttonClassName"
            >
                <t t-call-slot="toggler" open="this.isOpen()" />
            </button>
            <t t-if="this.isOpen()">
                <div
                    class="
                        hoot-dropdown absolute animate-slide-down
                        flex flex-col end-0 p-3 gap-2
                        bg-base text-base mt-1 shadow rounded z-2"
                >
                    <button class="fixed end-2 top-2 p-1 text-rose sm:hidden" t-on-click="() => this.isOpen.set(false)">
                        <i class="fa fa-times w-5 h-5" />
                    </button>
                    <t t-call-slot="menu" open="this.isOpen()" />
                </div>
            </t>
        </div>
    `;

    // Props & plugins
    props = props({
        buttonClassName: t.string().optional(),
        className: t.string().optional(),
        slots: t.object(["toggler", "menu"]),
    });

    // Reactive values
    isOpen = signal(false, { type: t.boolean() });
    rootRef = signal(null, { type: t.ref(HTMLDivElement) });
    togglerRef = signal(null, { type: t.ref(HTMLButtonElement) });

    setup() {
        useAutofocus(this.rootRef);
        useHootKey(["Escape"], this.close.bind(this));
        useWindowListener(
            "click",
            (ev) => {
                const path = ev.composedPath();
                if (!path.includes(this.rootRef())) {
                    this.isOpen.set(false);
                } else if (path.includes(this.togglerRef())) {
                    this.isOpen.set(!this.isOpen());
                }
            },
            { capture: true }
        );
    }

    /**
     * @param {KeyboardEvent} ev
     */
    close(ev) {
        if (this.isOpen()) {
            ev.preventDefault();
            this.isOpen.set(false);
        }
    }
}
