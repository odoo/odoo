import { toggleFn } from "@mail/utils/common/signal";

import { Component, props, signal, t, useListener } from "@odoo/owl";

import { useLayoutEffect, useRef, useSubEnv } from "@web/owl2/utils";
import { useNavigation } from "@web/core/navigation/navigation";
import { usePosition } from "@web/core/position/position_hook";
import { getFirstElementOfNode } from "@web/core/dropdown/dropdown";

/**
 * CallDropdown is an alternative to the web popover for calls to make them available
 * in cases where they cannot be overlays (main components), such as in picture-in-picture mode.
 */
export class CallDropdown extends Component {
    static template = "discuss.CallDropdown";

    setup() {
        super.setup();
        this.props = props({
            class: t.string().optional(""),
            menuClass: t.string().optional(""),
            openByDefault: t.boolean().optional(false),
            position: t.string().optional("bottom"),
        });
        this.menuRef = useRef("menu");
        this.isOpen = signal(this.props.openByDefault);
        usePosition("menu", () => this.triggerRef.el, {
            position: this.props.position,
            margin: 4,
            flip: true,
        });
        useListener(this.window, "click", (ev) => this.onClickAway(ev), { capture: true });
        useListener(this.window, "keydown", (ev) => this.onKeydown(ev));
        useSubEnv({ inCallDropdown: { close: () => this.close() } });
        this.navigation = useNavigation(this.menuRef, {
            isNavigationAvailable: () => this.isOpen(),
            getItems: () => {
                if (this.isOpen() && this.menuRef.el) {
                    return this.menuRef.el.querySelectorAll(
                        ":scope .o-navigable, :scope .o-dropdown"
                    );
                }
                return [];
            },
        });
        useLayoutEffect(
            (triggerEl, toggleOpenFn) => {
                if (triggerEl) {
                    const fn = (ev) => {
                        ev.preventDefault();
                        ev.stopPropagation();
                        toggleOpenFn();
                    };
                    triggerEl.addEventListener("click", fn);
                    return () => triggerEl.removeEventListener("click", fn);
                }
            },
            () => [this.triggerRef.el, toggleFn(this.isOpen)]
        );
    }

    get triggerRef() {
        return { el: getFirstElementOfNode(this.__owl__.bdom) };
    }

    get window() {
        return this.env.pipWindow || window;
    }

    close() {
        this.isOpen.set(false);
    }

    onClickAway(ev) {
        if (!this.isOpen()) {
            return;
        }
        const isOutsideClick =
            !this.triggerRef.el?.contains(ev.target) && !this.menuRef.el?.contains(ev.target);
        if (isOutsideClick) {
            this.close();
        }
    }

    onClickMenu(ev) {
        ev.stopPropagation();
    }

    onKeydown(ev) {
        if (ev.key === "Escape" && this.isOpen()) {
            ev.preventDefault();
            this.close();
        }
    }
}
