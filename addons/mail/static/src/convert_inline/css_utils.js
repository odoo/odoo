export const BLOCKED_PSEUDO_CLASSES = new Set([
    "active",
    "focus",
    "focus-within",
    "hover",
    "link",
    "target",
    "visited",
]);
export const INDIRECT_CSS_PROPERTY_VALUES = new Set([
    "inherit",
    "initial",
    "unset",
    "revert",
    "revert-layer",
]);
export const ALLOWED_CSS_DISPLAY_VALUES = new Set(["block", "inline", "inline-block", "none"]);
export const BLOCKED_CSS_POSITION_VALUES = new Set(["absolute", "sticky", "fixed"]);
