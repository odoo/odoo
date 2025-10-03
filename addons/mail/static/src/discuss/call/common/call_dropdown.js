import { Component, useRef, useState, useExternalListener, useSubEnv } from "@odoo/owl";
import { useNavigation } from "@web/core/navigation/navigation";
import { usePosition } from "@web/core/position/position_hook";

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
        this.triggerRef = useRef("trigger");
        this.menuRef = useRef("menu");
        this.state = useState({ isOpen: this.props.openByDefault });
        usePosition("menu", () => this.triggerRef.el, {
            position: this.props.position,
            margin: 4,
            flip: true,
        });
        useExternalListener(this.window, "click", this.onClickAway, { capture: true });
        useExternalListener(this.window, "keydown", this.onKeydown);
        useSubEnv({ inCallDropdown: { close: () => this.close() } });
        this.navigation = useNavigation(this.menuRef, {
            isNavigationAvailable: () => this.state.isOpen,
            getItems: () => {
                if (this.state.isOpen && this.menuRef.el) {
                    return this.menuRef.el.querySelectorAll(
                        ":scope .o-navigable, :scope .o-dropdown"
                    );
                }
                return [];
            },
        });
    }

    get window() {
        return this.env.pipWindow || window;
    }

    get isOpen() {
        return this.state.isOpen;
    }

    toggle() {
        this.isOpen ? this.close() : this.open();
    }

    open() {
        this.state.isOpen = true;
    }

    close() {
        this.state.isOpen = false;
    }

    handleClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.toggle();
    }

    onClickAway(ev) {
        if (!this.isOpen) {
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
        if (ev.key === "Escape" && this.isOpen) {
            ev.preventDefault();
            this.close();
        }
    }
}
