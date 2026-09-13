// @ts-check
/** @odoo-module native */

import {
    Component,
    onWillDestroy,
    useChildSubEnv,
    useExternalListener,
    useState,
} from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { makeDraggableHook } from "@web/core/utils/dnd/draggable_hook_builder_owl";
import { uniqueId } from "@web/core/utils/functions";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { useActiveElement } from "@web/ui/active_element";

const useDialogDraggable = makeDraggableHook(
    /** @type {any} */ ({
        name: "useDialogDraggable",
        onWillStartDrag(
            /** @type {{ ctx: { current: any }, addCleanup: Function, addStyle: Function, getRect: Function }} */ {
                ctx,
                addCleanup,
                addStyle,
                getRect,
            },
        ) {
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
        onDrop(
            /** @type {{ ctx: { current: any }, getRect: Function }} */ {
                ctx,
                getRect,
            },
        ) {
            const { top, left } = getRect(ctx.current.element);
            return {
                left: left - ctx.current.elementRect.left,
                top: top - ctx.current.elementRect.top,
            };
        },
    }),
);

const log = makeLogger("web.ui.dialog");

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
            validate: (/** @type {any} */ s) =>
                ["sm", "md", "lg", "xl", "fs", "fullscreen"].includes(s),
        },
        technical: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        modalRef: { type: Function, optional: true },
        slots: {
            type: Object,
            shape: {
                default: Object,
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
        useLifecycleLog(log);
        this.modalRef = useForwardRefToParent("modalRef");
        useActiveElement("modalRef");
        this.data = useState(this.env.dialogData);
        useHotkey("escape", () => this.onEscape());
        useHotkey(
            "control+enter",
            () => {
                const btns = /** @type {HTMLButtonElement[]} */ ([
                    ...(this.modalRef.el?.querySelectorAll(".modal-footer button") ??
                        []),
                ]);
                const firstActiveBtn = btns.find(
                    (btn) => !btn.disabled && getComputedStyle(btn).display !== "none",
                );
                firstActiveBtn?.click();
            },
            { bypassEditableProtection: true },
        );
        this.id = uniqueId("dialog_");
        useChildSubEnv({ inDialog: true, dialogId: this.id });
        this.isMovable = this.props.header;
        if (this.isMovable) {
            this.position = useState({ left: 0, top: 0 });
            useDialogDraggable(
                /** @type {any} */ ({
                    enable: () => !this.env.isSmall,
                    ref: this.modalRef,
                    elements: ".modal-content",
                    handle: ".modal-header",
                    ignore: "button, input",
                    edgeScrolling: { enabled: false },
                    onDrop: (
                        /** @type {{ top: number, left: number }} */ { top, left },
                    ) => {
                        this.position.left += left;
                        this.position.top += top;
                    },
                }),
            );
            const throttledResize = useThrottleForAnimation(this.onResize.bind(this));
            useExternalListener(window, "resize", throttledResize);
        }
        onWillDestroy(() => {
            if (this.env.isSmall) {
                this.data.scrollToOrigin?.();
            }
        });
        this.bodyTabIndex = hasTouch() ? "0" : undefined;
    }

    /** @returns {boolean} */
    get isFullscreen() {
        return this.props.fullscreen || this.env.isSmall;
    }

    /** @returns {string} */
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
        if ((await this.data.dismiss?.()) === false) {
            return;
        }
        return this.data.close({ dismiss: true });
    }
}
