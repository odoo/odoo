// @ts-check

/** @module @web/webclient/actions/action_constants - Constants (dialog sizes, context key regex, embedded action keys) and ID parsing for the action service */

/**
 * Constants and simple parsing for the action service.
 */

/** Map from Odoo dialog_size context values to Bootstrap modal size classes. */
export const DIALOG_SIZES = {
    "extra-large": "xl",
    large: "lg",
    medium: "md",
    small: "sm",
};

/** Regex matching context keys that should NOT be forwarded between actions. */
export const CTX_KEY_REGEX =
    /^(?:(?:default_|search_default_|show_).+|.+_view_ref|group_by|active_id|active_ids|orderedBy)$/;

/** Context keys added for the embedded actions feature. */
export const EMBEDDED_ACTIONS_CTX_KEYS = [
    "current_embedded_action_id",
    "parent_action_embedded_actions",
    "parent_action_id",
    "from_embedded_action",
];

/**
 * Parse a string or number into an array of active record IDs.
 *
 * @param {string|number} ids - comma-separated string or single number
 * @returns {number[]}
 */
export function parseActiveIds(ids) {
    const activeIds = [];
    if (typeof ids === "string") {
        activeIds.push(...ids.split(",").map(Number));
    } else if (typeof ids === "number") {
        activeIds.push(ids);
    }
    return activeIds;
}
