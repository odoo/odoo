// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Data } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/** @type {[element: Element, key: string][]} */
const instanceKeys = [];

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Bootstrap keeps its component instances, and their listeners, in global
 * registries until they are disposed, which is rarely done explicitly (e.g. for
 * instances created by its data API, such as `data-bs-toggle` attributes). These
 * instances would otherwise retain their element, and everything it references.
 */
export function disposeBootstrapInstances() {
    for (const [element, key] of instanceKeys.splice(0)) {
        Data.get(element, key)?.dispose();
    }
}

//-----------------------------------------------------------------------------
// Execution
//-----------------------------------------------------------------------------

if (Data) {
    const { set } = Data;
    Data.set = function (element, key) {
        instanceKeys.push([element, key]);
        return set.apply(this, arguments);
    };
}
