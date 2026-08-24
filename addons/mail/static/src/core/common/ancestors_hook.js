import { useScope } from "@odoo/owl";

/**
 * Returns an object exposing `has(componentName)`, true when a component
 * named `componentName` is among the ancestors (or is itself) the component
 * calling this hook.
 *
 * @returns {{ has: (componentName: string) => boolean }}
 */
export function useAncestors() {
    const parents = new Set();
    let scope = useScope();
    while (scope) {
        parents.add(scope.componentName);
        scope = scope.parent;
    }
    return {
        has: (componentName) => parents.has(componentName),
    };
}
