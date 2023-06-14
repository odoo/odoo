/* @odoo-module */

const patchableSymbol = Symbol("patchable");

export function makeFnPatchable(func) {
    const res = function (...args) {
        let currIndex = -1;
        const patches = [...res.patches];
        const localThis = { _super: undefined };

        function _call(target, ...args) {
            currIndex++;
            localThis._super =
                patches.length > currIndex ? _call.bind(null, patches[currIndex + 1]) : undefined;
            const r = target.call(localThis, ...args);
            currIndex--;
            return r;
        }

        return _call(patches[0], ...args);
    };
    res.patches = [func];
    res[patchableSymbol] = true;
    return res;
}

export function patchFn(func, patch) {
    if (!func[patchableSymbol]) {
        throw new Error(`Cannot patch unpatchable function "${func.name}"`);
    }
    func.patches.unshift(patch);
}
