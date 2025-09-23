export const difference = function (s) {
    if (!(s instanceof Set)) {
        throw new Error("argument must be a Set");
    }
    return new Set([...this].filter((e) => !s.has(e)));
};

// Safari < 17 (09/2023) doesn't support Set.difference, but this version is
// quite recent enough for **public** users
if (!Set.prototype.difference) {
    Object.defineProperty(Set.prototype, "difference", {
        enumerable: false,
        value: difference,
    });
}
