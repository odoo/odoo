import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * A declaration attaches named properties to a node, based on how the node is
 * matched:
 * - `within`: a selector matched against the node's ancestors (and itself) —
 *   the node belongs to a containing region (e.g. inside an inline `code`).
 * - `is`: a selector or a predicate matched against the node itself — the node
 *   has an intrinsic property (e.g. a media element being editable).
 *
 * Exactly one of `within`/`is` should be provided.
 *
 * @typedef {Object} NodeProperties
 * @property {string} [within] Containment selector (ancestor-or-self match).
 * @property {string | ((node: Node) => boolean)} [is] Node-self selector or predicate.
 * @property {*} [property] Any number of named properties — a boolean or a
 *      free-form value.
 */

/**
 * @typedef {NodeProperties[]} region_properties
 */

/**
 * @typedef {Object} RegionShared
 * @property { RegionPlugin['getProperty'] } getProperty
 */

/**
 * Computes node properties that determine how features behave around a given
 * node. A property is acquired either from a containing region (`within`, e.g.
 * the powerbox being disabled inside an inline `code` element) or from the node
 * itself (`is`, e.g. a media element being editable). Both feed the same lookup
 * so features don't each reimplement the same ancestor/self checks; they query
 * `getProperty` instead.
 */
export class RegionPlugin extends Plugin {
    static id = "region";
    static shared = ["getProperty"];

    /**
     * Whether `declaration`'s matcher accepts `node`: an ancestor-or-self match
     * for `within`, or a node-self match (selector or predicate) for `is`.
     *
     * @param {NodeProperties} declaration
     * @param {Node} node
     * @returns {boolean}
     */
    matches(declaration, node) {
        if (declaration.within) {
            return !!closestElement(node, declaration.within);
        }
        if (typeof declaration.is === "function") {
            return !!declaration.is(node);
        }
        return !!node.matches?.(declaration.is);
    }

    /**
     * Return the value of the property `name` for `node`, combining every
     * matching declaration that defines it, or `undefined` if none applies.
     * Callers provide their own default, e.g.:
     * ```js
     * this.dependencies.region.getProperty(node, "powerbox") ?? true;
     * ```
     *
     * How matches are combined depends on the value type:
     * - boolean: ANDed, so any `false` wins — a restrictive capability is
     *   disabled as soon as one declaration says so;
     * - otherwise: the first matching declaration (in resource order) wins — a
     *   prioritized value.
     *
     * @param {Node} node
     * @param {string} name
     * @returns {*}
     */
    getProperty(node, name) {
        let result;
        for (const declaration of this.getResource("region_properties")) {
            if (name in declaration && this.matches(declaration, node)) {
                const value = declaration[name];
                result = typeof value === "boolean" ? (result ?? true) && value : result ?? value;
            }
        }
        return result;
    }
}
