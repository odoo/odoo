export function transformDiscussAction(component, id, action) {
    return {
        /** If set, this is considered as a danger (destructive) action. */
        get danger() {
            return typeof action.danger === "function" ? action.danger(component) : action.danger;
        },
        /** Unique id of this action. */
        id,
        /** Determines the order of this action (smaller first). */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
        },
        /** Component setup to execute when this action is registered. */
        setup: action.setup,
        /** If set, this is considered as a success (high-commitment positive) action. */
        get success() {
            return typeof action.success === "function"
                ? action.success(component)
                : action.success;
        },
    };
}
