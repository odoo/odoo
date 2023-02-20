/**
 * Creates a side-effect that runs based on the content of reactive objects.
 * @template {object[]} T
 * @param {(...args: [...T]) => void} cb callback for the effect
 * @param {[...T]} deps the reactive objects that the effect depends on
 */
function effect(cb, deps) {
    const reactiveDeps = reactive(deps, () => {
        cb(...reactiveDeps);
    });
    cb(...reactiveDeps);
}
// exports = { effect };