import { proxy, useListener } from "@odoo/owl";
import { useLayoutEffect } from "@web/owl2/utils";

// Resolve the element backing a ref regardless of its kind, preserving every legacy form and only
// ADDING the Owl 3 signal case:
// - undefined/optional ref       -> undefined (no crash; mirrors the old `ref.el`)
// - object refs (useRef)         -> `.el`
// - forwarded refs (useChildRef) -> a callable that ALSO exposes an `.el` getter once it has
//                                   received its child value. `.el` must take precedence over
//                                   calling it; calling such a ref with no argument sets its
//                                   inner value to undefined and makes later `.el` reads throw
//                                   "Cannot read properties of undefined (reading 'el')".
//                                   It also takes a value argument (arity 1), so we never call
//                                   it: before it is mounted `.el` is simply absent (undefined),
//                                   exactly like the original direct `ref.el` read.
// - Owl 3 native signal refs     -> a zero-argument callable with no `.el`; resolved by calling.
function resolveRefEl(ref) {
    if (ref == null) {
        return undefined;
    }
    // Legacy contract: object refs (useRef) and mounted forwarded refs (useChildRef) expose
    // the element through `.el`. Matches the original direct `ref.el`.
    if (typeof ref !== "function") {
        return ref.el;
    }
    // Forwarded refs (useChildRef) are callables that accept a value (length === 1) and surface
    // the element via an `.el` getter. Never call them; read `.el` (undefined until mounted).
    if (ref.length > 0 || "el" in ref) {
        return ref.el;
    }
    // Owl 3 native signal ref: a zero-argument getter. Call it to read the element.
    return ref();
}

export function useDropdownAutoVisibility(overlayState, popoverRef) {
    if (!overlayState) {
        return;
    }
    const state = proxy(overlayState);
    const getEl = () => resolveRefEl(popoverRef);
    useLayoutEffect(
        () => {
            const el = getEl();
            if (el) {
                if (!state.isOverlayVisible) {
                    el.style.visibility = "hidden";
                } else {
                    el.style.visibility = "visible";
                }
            }
        },
        () => [state.isOverlayVisible]
    );
}

export function useToolbarDropdownFocus(dropdown, buttonRef) {
    useListener(
        document,
        "keydown",
        (ev) => {
            if (ev.key === "Escape" && dropdown.isOpen) {
                resolveRefEl(buttonRef)?.focus();
            }
        },
        { capture: true }
    );
}
