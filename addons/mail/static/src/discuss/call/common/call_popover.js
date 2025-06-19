import { Component, useRef, useState, useExternalListener } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";

/**
 * CallPopover is an alternative to the web popover for calls to make them available
 * in cases where they cannot be overlays (main components), such as in picture-in-picture mode.
 */
export class CallPopover extends Component {
    static template = "discuss.CallPopover";
    static props = {
        position: { type: String, optional: true },
        class: { type: String, optional: true },
        contentClass: { type: String, optional: true },
        clickToClose: { type: Boolean, optional: true },
        slots: { optional: true },
        openByDefault: { type: Boolean, optional: true },
    };
    static defaultProps = {
        position: "bottom",
        class: "",
        contentClass: "",
        clickToClose: false,
        openByDefault: false,
    };

    setup() {
        super.setup();
        this.triggerRef = useRef("trigger");
        this.contentRef = useRef("content");
        this.state = useState({ isOpen: this.props.openByDefault });
        usePosition("content", () => this.triggerRef.el, {
            position: this.props.position,
            margin: 4,
            flip: true,
        });
        useExternalListener(this.window, "click", this.onDocumentClick, { capture: true });
        useExternalListener(this.window, "keydown", this.onKeydown);
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

    onTriggerClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.toggle();
    }

    onDocumentClick(ev) {
        if (!this.isOpen) {
            return;
        }
        const isOutsideClick =
            !this.triggerRef.el?.contains(ev.target) && !this.contentRef.el?.contains(ev.target);
        if (isOutsideClick) {
            this.close();
        }
    }

    onContentClick(ev) {
        if (this.props.clickToClose) {
            this.close();
        }
        ev.stopPropagation();
    }

    onKeydown(ev) {
        if (ev.key === "Escape" && this.isOpen) {
            ev.preventDefault();
            this.close();
        }
    }
}
