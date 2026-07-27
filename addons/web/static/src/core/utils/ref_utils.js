import { untrack } from "@odoo/owl";

/**
 * Resolve the element backing a ref regardless of its kind:
 * - undefined/optional ref   -> undefined (no crash; mirrors the old `ref.el`)
 * - legacy object refs (useRef) -> `.el`
 * - Owl 3 native signal refs -> a zero-argument callable, resolved by calling it.
 *
 * @param {{ el?: HTMLElement } | (() => HTMLElement) | null | undefined} ref
 * @returns {HTMLElement | null | undefined}
 */
export function resolveRefEl(ref) {
    if (ref == null) {
        return undefined;
    }
    // Legacy contract: object refs (useRef) expose the element through `.el`.
    if (typeof ref !== "function") {
        return ref.el;
    }
    // Owl 3 native signal ref: a zero-argument getter. Call it to read the element.
    // Untrack the read so resolving a ref's element never subscribes the caller
    // to the signal: this mirrors the legacy `useRef().el` contract (which read
    // the underlying signal through `owl.untrack`). Without this, reading the ref
    // during a render phase (e.g. `useInputField`'s layout-effect dependency
    // computation, run in `onWillRender`) registers a spurious render dependency,
    // causing the component to re-patch when the ref signal is set on mount.
    return untrack(ref);
}
