import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useActiveElement } from "../ui/ui_service";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { Component, onWillDestroy, useChildSubEnv, useExternalListener, useState } from "@odoo/owl";
import { throttleForAnimation } from "@web/core/utils/timing";
import { makeDraggableHook } from "../utils/draggable_hook_builder_owl";

const useDialogDraggable = makeDraggableHook({
    name: "useDialogDraggable",
    onWillStartDrag({ ctx, addCleanup, addStyle, getRect }) {
        const { height, width } = getRect(ctx.current.element);
        ctx.current.container = document.createElement("div");
        addStyle(ctx.current.container, {
            position: "fixed",
            top: "0",
            bottom: `${70 - height}px`,
            left: `${70 - width}px`,
            right: `${70 - width}px`,
        });
        ctx.current.element.after(ctx.current.container);
        addCleanup(() => ctx.current.container.remove());
    },
    onDrop({ ctx, getRect }) {
        const { top, left } = getRect(ctx.current.element);
        return {
            left: left - ctx.current.elementRect.left,
            top: top - ctx.current.elementRect.top,
        };
    },
});

export class Dialog extends Component {
    static template = "web.Dialog";
    static props = {
        contentClass: { type: String, optional: true },
        bodyClass: { type: String, optional: true },
        fullscreen: { type: Boolean, optional: true },
        footer: { type: Boolean, optional: true },
        header: { type: Boolean, optional: true },
        size: {
            type: String,
            optional: true,
            validate: (s) => ["sm", "md", "lg", "xl", "fs", "fullscreen"].includes(s),
        },
        technical: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        modalRef: { type: Function, optional: true },
        slots: {
            type: Object,
            shape: {
                default: Object, // Content is not optional
                header: { type: Object, optional: true },
                footer: { type: Object, optional: true },
            },
        },
        withBodyPadding: { type: Boolean, optional: true },
        onExpand: { type: Function, optional: true },
    };
    static defaultProps = {
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

    setup() {
        this.modalRef = useForwardRefToParent("modalRef");
        useActiveElement("modalRef");
        this.data = useState(this.env.dialogData);
        useHotkey("escape", () => this.onEscape());
        useHotkey(
            "control+enter",
            () => {
                const btns = document.querySelectorAll(
                    ".o_dialog:not(.o_inactive_modal) .modal-footer button"
                );
                const firstVisibleBtn = Array.from(btns).find((btn) => {
                    const styles = getComputedStyle(btn);
                    return styles.display !== "none";
                });
                if (firstVisibleBtn) {
                    firstVisibleBtn.click();
                }
            },
            { bypassEditableProtection: true }
        );
        this.id = `dialog_${this.data.id}`;
        useChildSubEnv({ inDialog: true, dialogId: this.id });
        this.isMovable = this.props.header;
        if (this.isMovable) {
            this.position = useState({ left: 0, top: 0 });
            useDialogDraggable({
                enable: () => !this.env.isSmall,
                ref: this.modalRef,
                elements: ".modal-content",
                handle: ".modal-header",
                ignore: "button, input",
                edgeScrolling: { enabled: false },
                onDrop: ({ top, left }) => {
                    this.position.left += left;
                    this.position.top += top;
                },
            });
            const throttledResize = throttleForAnimation(this.onResize.bind(this));
            useExternalListener(window, "resize", throttledResize);
        }
        onWillDestroy(() => {
            if (this.env.isSmall) {
                this.data.scrollToOrigin();
            }
        });
    }

    get isFullscreen() {
        return this.props.fullscreen || this.env.isSmall;
    }

    get contentStyle() {
        if (this.isMovable) {
            return `top: ${this.position.top}px; left: ${this.position.left}px;`;
        }
        return "";
    }

    onResize() {
        this.position.left = 0;
        this.position.top = 0;
    }

    onEscape() {
        return this.dismiss();
    }

    async dismiss() {
        if (this.data.dismiss) {
            await this.data.dismiss();
        }
        return this.data.close({ dismiss: true });
    }
}
