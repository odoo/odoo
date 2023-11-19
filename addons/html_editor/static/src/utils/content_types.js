export const CTYPES = {
    // Short for CONTENT_TYPES
    // Inline group
    CONTENT: 1,
    SPACE: 2,

    // Block group
    BLOCK_OUTSIDE: 4,
    BLOCK_INSIDE: 8,

    // Br group
    BR: 16,
};
export function ctypeToString(ctype) {
    return Object.keys(CTYPES).find((key) => CTYPES[key] === ctype);
}
export const CTGROUPS = {
    // Short for CONTENT_TYPE_GROUPS
    INLINE: CTYPES.CONTENT | CTYPES.SPACE,
    BLOCK: CTYPES.BLOCK_OUTSIDE | CTYPES.BLOCK_INSIDE,
    BR: CTYPES.BR,
};
