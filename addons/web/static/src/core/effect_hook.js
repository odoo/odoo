/** @odoo-module */
const { onMounted, onWillPatch, onPatched, onWillUnmount } = owl.hooks;

const NO_OP = () => {};
/**
 * @callback Effect
 * @param {...any} dependencies the dependecies computed by computeDependencies
 * @returns {()=>void)?} a cleanup function that reverses the side
 *      effects of the effect callback.
 */

/**
 * This hook will run a callback when a component is mounted and patched, and
 * will run a cleanup function before patching and before unmounting the
 * the component.
 *
 * @param {Effect} effect the effect to run on component mount and/or patch
 * @param {()=>any[]} [computeDependencies=()=>[NaN]] a callback to compute
 *      dependencies that will decide if the effect needs to be cleaned up and
 *      run again. If the dependencies did not change, the effect will not run
 *      again. The default value returns an array containing only NaN because
 *      NaN !== NaN, which will cause the effect to rerun on every patch.
 */
export function useEffect(effect, computeDependencies = () => [NaN]) {
    let cleanup, dependencies;
    onMounted(() => {
        dependencies = computeDependencies();
        cleanup = effect(...dependencies) || NO_OP;
    });

    let shouldReapplyOnPatch = false;
    onWillPatch(() => {
        const newDeps = computeDependencies();
        shouldReapplyOnPatch = newDeps.some((val, i) => val !== dependencies[i]);
        if (shouldReapplyOnPatch) {
            cleanup();
            dependencies = newDeps;
        }
    });
    onPatched(() => {
        if (shouldReapplyOnPatch) {
            cleanup = effect(...dependencies) || NO_OP;
        }
    });

    onWillUnmount(() => cleanup());
}
