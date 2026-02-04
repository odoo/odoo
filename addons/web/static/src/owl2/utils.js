import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";


/**
 * OWL2
 * This hook will run a callback when a component is mounted and patched, and
 * will run a cleanup function before patching and before unmounting the
 * the component.
 *
 * @template T
 * @param {Effect<T>} effect the effect to run on component mount and/or patch
 * @param {()=>[...T]} [computeDependencies=()=>[NaN]] a callback to compute
 *      dependencies that will decide if the effect needs to be cleaned up and
 *      run again. If the dependencies did not change, the effect will not run
 *      again. The default value returns an array containing only NaN because
 *      NaN !== NaN, which will cause the effect to rerun on every patch.
 */
export function useLayoutEffect(effect, computeDependencies = () => [NaN]) {
    let cleanup;
    let dependencies;
    onMounted(() => {
        dependencies = computeDependencies();
        cleanup = effect(...dependencies);
    });
    onPatched(() => {
        const newDeps = computeDependencies();
        const shouldReapply = newDeps.some((val, i) => val !== dependencies[i]);
        if (shouldReapply) {
            dependencies = newDeps;
            if (cleanup) {
                cleanup();
            }
            cleanup = effect(...dependencies);
        }
    });
    onWillUnmount(() => cleanup && cleanup());
}