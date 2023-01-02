/** @odoo-module **/

import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useActiveElement } from "../ui/ui_service";
import { useForwardRefToParent } from "@web/core/utils/hooks";

import { Component, useChildSubEnv, useState, onMounted } from "@odoo/owl";
export class Dialog extends Component {
    setup() {
        this.modalRef = useForwardRefToParent("modalRef");
        useActiveElement("modalRef");
        this.data = useState(this.env.dialogData);
        this.state = useState({
            dragging: false,
            nextX: 0, nextY: 0,
            prevX: 0, prevY: 0,
        });
        onMounted(() => {
            this.element = $(this.modalRef.el).find('.modal-content')[0];
        })
        useHotkey("escape", () => {
            this.data.close();
        });
        this.id = `dialog_${this.data.id}`;
        useChildSubEnv({ inDialog: true, dialogId: this.id, closeDialog: this.data.close });

        owl.onWillDestroy(() => {
            if (this.env.isSmall) {
                this.data.scrollToOrigin();
            }
        });
    }

    get isFullscreen() {
        return this.props.fullscreen || this.env.isSmall;
    }

    onMouseUp() {
        this.state.dragging = false;
    }

    onMouseDown(e) {
        this.state.dragging = true;
        this.state.prevX = e.clientX;
        this.state.prevY = e.clientY;
    }

    onMouseMove(e) {
        if (this.state.dragging) {
            this.state.nextX = this.state.prevX - e.clientX;
            this.state.nextY = this.state.prevY - e.clientY;
            this.state.prevX = e.clientX;
            this.state.prevY = e.clientY;
            this.element.style.left = (this.element.offsetLeft - this.state.nextX) + "px";
            this.element.style.top = (this.element.offsetTop - this.state.nextY) + "px";
        }
    }
}
Dialog.template = "web.Dialog";
Dialog.props = {
    contentClass: { type: String, optional: true },
    bodyClass: { type: String, optional: true },
    fullscreen: { type: Boolean, optional: true },
    footer: { type: Boolean, optional: true },
    header: { type: Boolean, optional: true },
    size: { type: String, optional: true, validate: (s) => ["sm", "md", "lg", "xl"].includes(s) },
    technical: { type: Boolean, optional: true },
    title: { type: String, optional: true },
    modalRef: { type: Function, optional: true },
    slots: {
        type: Object,
        shape: {
            default: Object, // Content is not optional
            footer: { type: Object, optional: true },
        },
    },
    withBodyPadding: { type: Boolean, optional: true },
};
Dialog.defaultProps = {
    contentClass: "",
    bodyClass: "",
    fullscreen: false,
    footer: true,
    header: true,
    size: "lg",
    technical: true,
    title: "Odoo",
    withBodyPadding: true,
};
