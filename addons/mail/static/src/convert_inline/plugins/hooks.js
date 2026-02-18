/**
 * Assign dependency functions to a plugin
 *
 * @param {Plugin} plugin
 * @param {string} dependency
 * @param {Array<string>} functions
 */
export function useShorthands(plugin, dependency, functions) {
    for (const fn of functions) {
        plugin[fn] = plugin.dependencies[dependency][fn];
    }
}
