import { useEffect, useRef } from "@odoo/owl";
import { router, stateToUrl } from "@web/core/browser/router";

export function useMiddleClick({ refName, clickParams }) {
    const ref = useRef(refName || "middleclick");
    let _onCtrlClick;
    if (clickParams) {
        if (clickParams.onCtrlClick) {
            _onCtrlClick = clickParams.onCtrlClick;
        } else if (clickParams.record) {
            _onCtrlClick = (ev) => {
                const actionStack = [
                    ...router.current.actionStack,
                    {
                        action: clickParams.record.action,
                        model: clickParams.record.resModel,
                        resId: clickParams.record.resId,
                    },
                ];
                const href = stateToUrl({
                    actionStack,
                });
                ev?.preventDefault();
                ev?.stopPropagation();
                window.open(href);
            };
        }
    }
    const handleClick = (ev) => {
        if (!ev.target.classList.contains("middle_clickable")) {
            // keep the default browser behavior if the click on the element is not explicitly handled by the hook
            return;
        }
        if ((ev.ctrlKey && ev.button === 0) || ev.button === 1) {
            if (_onCtrlClick) {
                _onCtrlClick(ev);
            }
        }
    };
    const styleControlPressed = (ev) => {
        if (ev.key === "Control") {
            document.body.classList.add("ctrl_key_pressed");
        }
    };
    const styleControlUp = (ev) => {
        if (ev.key === "Control") {
            resetStyleAndRouter();
        }
    };
    const resetStyleAndRouter = () => {
        document.body.classList.remove("ctrl_key_pressed");
    };
    useEffect(
        () => {
            if (ref.el) {
                const el = ref.el;
                el.classList.add("middle_clickable");
                if (clickParams.record) {
                    el.classList.add("middle_clickable_record");
                }
                el.addEventListener("click", handleClick, { capture: true });
                window.addEventListener("keydown", styleControlPressed);
                window.addEventListener("keyup", styleControlUp);
                // we must do a reset when the page loses focus while the key is still pressed
                window.addEventListener("blur", resetStyleAndRouter);
                return () => {
                    el.removeEventListener("click", handleClick);
                    window.removeEventListener("keydown", styleControlPressed);
                    window.removeEventListener("keyup", styleControlUp);
                    window.removeEventListener("blur", resetStyleAndRouter);
                    resetStyleAndRouter();
                };
            }
        },
        () => [ref.el]
    );
}
