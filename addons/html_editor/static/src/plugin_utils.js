/**
 * @typedef {import("plugins").PluginConstructor} PluginConstructor
 **/

/**
 * @param {PluginConstructor[]} plugins
 * @returns {PluginConstructor[]}
 */
export function sortPlugins(plugins) {
    const initialPlugins = new Set(plugins);
    const inResult = new Set();
    // need to sort them
    const result = [];
    let P;

    function findPlugin() {
        for (const P of initialPlugins) {
            if (P.dependencies.every((dep) => inResult.has(dep))) {
                initialPlugins.delete(P);
                return P;
            }
        }
    }
    while ((P = findPlugin())) {
        inResult.add(P.id);
        result.push(P);
    }
    if (initialPlugins.size) {
        const cycle = findDependencyCycle([...initialPlugins]);
        if (cycle) {
            throw new Error(`Circular dependencies: ${cycle.join(" -> ")}`);
        } else {
            const messages = [];
            for (const P of initialPlugins) {
                messages.push(
                    `"${P.id}" is missing (${P.dependencies
                        .filter((d) => !inResult.has(d))
                        .join(", ")})`
                );
            }
            throw new Error(`Missing dependencies: ${messages.join(", ")}`);
        }
    }
    return result;
}

/**
 * Finds one circular dependency among the plugins left after sorting with
 * @see sortPlugins failed.
 * Returning the first cycle is enough to explain why the plugins cannot be
 * sorted and avoids enumerating every possible cycle.
 *
 * @param {PluginConstructor[]} plugins
 * @param {string} [id]
 * @param {Object} [state]
 * @param {Set<string>} state.visiting
 * @param {Set<string>} state.visited
 * @param {string[]} state.path
 * @returns {string[] | null}
 */
function findDependencyCycle(plugins, id, state) {
    // Base case: try every plugin. Return as soon as a cycle has been found.
    if (!id) {
        state = {
            visiting: new Set(),
            visited: new Set(),
            path: [],
        };
        for (const P of plugins) {
            const cycle = findDependencyCycle(plugins, P.id, state);
            if (cycle) {
                return cycle;
            }
        }
        return null;
    }

    // Recursive case.
    const { visiting, visited, path } = state;
    path.push(id);

    // Return if a cycle has been found.
    if (visiting.has(id)) {
        return path.slice(path.indexOf(id));
    }

    const P = plugins.find((Plugin) => Plugin.id === id);

    // Ignore fully checked plugins and dependencies that are not among the
    // plugins under investigation.
    if (!P || visited.has(id)) {
        return null;
    }

    visiting.add(id);

    // Visit the dependencies of the given plugin and return as soon as a cycle
    // is found.
    for (const dependencyId of P.dependencies) {
        const cycle = findDependencyCycle(plugins, dependencyId, state);
        if (cycle) {
            return cycle;
        }
    }

    // No cycle starts through this plugin, so remove it from the current
    // branch and prevent later traversals from checking it again.
    path.pop();
    visiting.delete(id);
    visited.add(id);
    return null;
}
