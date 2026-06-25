import { useChildSubEnv } from "@web/owl2/utils";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useActiveElement } from "../ui/ui_service";
import { useBackButton, useForwardRefToParent } from "@web/core/utils/hooks";
import { Component, onWillDestroy, props, proxy, t, useListener } from "@odoo/owl";
import { throttleForAnimation } from "@web/core/utils/timing";
import { makeDraggableHook } from "../utils/draggable_hook_builder_owl";
import { hasTouch } from "@web/core/browser/feature_detection";

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
        document.body.classList.add("o_modal_dragged");
        addCleanup(() => {
            document.body.classList.remove("o_modal_dragged");
            ctx.current.container.remove();
        });
    },
    onDrop({ ctx, getRect }) {
        const { top, left } = getRect(ctx.current.element);
        return {
            left: left - ctx.current.elementRect.left,
            top: top - ctx.current.elementRect.top,
        };
    },
});

export const dialogProps = {
    contentClass: t.string().optional(""),
    bodyClass: t.string().optional(""),
    fullscreen: t.boolean().optional(false),
    footer: t.boolean().optional(true),
    header: t.boolean().optional(true),
    size: t.selection(["sm", "md", "lg", "xl", "fs", "fullscreen"]).optional("lg"),
    technical: t.boolean().optional(true),
    title: t.string().optional("Odoo"),
    modalRef: t.function().optional(),
    slots: t.object({
        default: t.object(), // Content is not optional
        header: t.object().optional(),
        footer: t.object().optional(),
    }),
    withBodyPadding: t.boolean().optional(true),
    onExpand: t.function().optional(),
};

export class Dialog extends Component {
    static template = "web.Dialog";
    // don't do this, it is only temporary to allow the dialog props to be
    // overridden.
    static props = dialogProps;
    props = props(this.constructor.props);

    setup() {
        this.modalRef = useForwardRefToParent("modalRef");
        useActiveElement("modalRef");
        this.data = proxy(this.env.dialogData);
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
                    // Allows the active element to be blurred before triggering the click on the button
                    firstVisibleBtn.focus();
                    firstVisibleBtn.click();
                }
            },
            { bypassEditableProtection: true }
        );
        this.id = `dialog_${this.data.id}`;
        useChildSubEnv({ inDialog: true, dialogId: this.id });
        this.isMovable = this.props.header;
        if (this.isMovable) {
            this.position = proxy({ left: 0, top: 0 });
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
            useListener(window, "resize", throttledResize);
        }
        onWillDestroy(() => {
            if (this.env.isSmall) {
                this.data.scrollToOrigin();
            }
        });
        this.bodyTabIndex = hasTouch() ? "0" : undefined;
        useBackButton(() => this.dismiss());
    }

    get size() {
        return this.props.size;
    }

    get isFullscreen() {
        return this.props.fullscreen || (this.env.isSmall && this.design !== "minimal");
    }

    get design() {
        return ["sm", "md"].includes(this.size) ? "minimal" : "default";
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
