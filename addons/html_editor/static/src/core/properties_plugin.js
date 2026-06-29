import { Plugin } from "@html_editor/plugin";

/**
 * A declaration associating properties with the nodes its predicate matches.
 *
 * `predicate` is either:
 * - a CSS selector, matched against the node itself (a text node never matches
 *   a selector);
 * - a function, e.g. `(node) => closestElement(node, "LI")` for properties
 *   acquired from a containing element.
 *
 * @typedef {Object} NodeProperties
 * @property {string | ((node: Node) => boolean)} predicate CSS selector or
 *      function matching the node.
 */

/**
 * @typedef {NodeProperties[]} properties
 */

/**
 * @typedef {Object} PropertiesShared
 * @property { PropertiesPlugin['get'] } get
 */

/**
 * Computes node properties that determine how features behave around a given
 * node, from the declarations matching it.
 */
export class PropertiesPlugin extends Plugin {
    static id = "properties";
    static shared = ["get"];

    /**
     * @param {NodeProperties} declaration
     * @param {Node} node
     * @returns {boolean}
     */
    matches(declaration, node) {
        if (typeof declaration.predicate === "function") {
            return !!declaration.predicate(node);
        }
        return !!node.matches?.(declaration.predicate);
    }

    /**
     * Return the value of the property `name` for `node`, combining every
     * matching declaration that defines it, or `defaultValue` if none applies, e.g.:
     * ```js
     * this.dependencies.properties.get(node, "powerbox", true);
     * ```
     *
     * How matches are combined depends on the value type:
     * - boolean: ANDed, so any `false` wins, a restrictive capability is
     *   disabled as soon as one declaration says so.
     * - otherwise: the first matching declaration (in resource order) wins.
     * - a mix of both: the booleans win, e.g. `removable: false` overrides
     *   `removable: "cascade"`.
     *
     * @param {Node} node
     * @param {string} name
     * @param {*} [defaultValue] returned when no declaration applies
     * @returns {*}
     */
    get(node, name, defaultValue) {
        let result;
        for (const declaration of this.getResource("properties")) {
            if (name in declaration && this.matches(declaration, node)) {
                const value = declaration[name];
                result = typeof value === "boolean" ? (result ?? true) && value : result ?? value;
            }
        }
        return result ?? defaultValue;
    }
}
