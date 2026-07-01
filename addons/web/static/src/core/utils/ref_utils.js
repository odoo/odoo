import { untrack } from "@odoo/owl";

/**
 * Resolve the element backing a ref regardless of its kind, preserving every
 * legacy form and only ADDING the Owl 3 native signal case:
 * - undefined/optional ref       -> undefined (no crash; mirrors the old `ref.el`)
 * - object refs (useRef)         -> `.el`
 * - forwarded refs (useChildRef) -> a callable that ALSO exposes an `.el` getter
 *   once it has received its child value. `.el` must take precedence over
 *   calling it: calling such a ref with no argument sets its inner value to
 *   undefined and makes later `.el` reads throw. It also takes a value argument
 *   (arity 1), so we never call it; before it is mounted `.el` is simply absent
 *   (undefined), exactly like the original direct `ref.el` read.
 * - Owl 3 native signal refs     -> a zero-argument callable with no `.el`,
 *   resolved by calling it.
 *
 * @param {{ el?: HTMLElement } | (() => HTMLElement) | null | undefined} ref
 * @returns {HTMLElement | null | undefined}
 */
export function resolveRefEl(ref) {
    if (ref == null) {
        return undefined;
    }
    // Legacy contract: object refs (useRef) and mounted forwarded refs
    // (useChildRef) expose the element through `.el`. Matches the original
    // direct `ref.el`.
    if (typeof ref !== "function") {
        return ref.el;
    }
    // Forwarded refs (useChildRef) are callables that accept a value
    // (length === 1) and surface the element via an `.el` getter. Never call
    // them; read `.el` (undefined until mounted).
    if (ref.length > 0 || "el" in ref) {
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
