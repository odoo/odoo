import { toggleFn } from "@mail/utils/common/signal";

import { Component, signal } from "@odoo/owl";

import { useExternalListener, useLayoutEffect, useRef, useSubEnv } from "@web/owl2/utils";
import { useNavigation } from "@web/core/navigation/navigation";
import { usePosition } from "@web/core/position/position_hook";
import { getFirstElementOfNode } from "@web/core/dropdown/dropdown";

/**
 * CallDropdown is an alternative to the web popover for calls to make them available
 * in cases where they cannot be overlays (main components), such as in picture-in-picture mode.
 */
export class CallDropdown extends Component {
    static template = "discuss.CallDropdown";
    static props = {
        position: { type: String, optional: true },
        class: { type: String, optional: true },
        menuClass: { type: String, optional: true },
        slots: { optional: true },
        openByDefault: { type: Boolean, optional: true },
        state: { type: Object, optional: true },
    };
    static defaultProps = {
        position: "bottom",
        class: "",
        menuClass: "",
        openByDefault: false,
    };

    setup() {
        super.setup();
        this.menuRef = useRef("menu");
        this.isOpen = signal(this.props.openByDefault);
        usePosition("menu", () => this.triggerRef.el, {
            position: this.props.position,
            margin: 4,
            flip: true,
        });
        useExternalListener(this.window, "click", this.onClickAway, { capture: true });
        useExternalListener(this.window, "keydown", this.onKeydown);
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
