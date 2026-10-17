import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * A declaration associating properties with nodes matching a given condition.
 *
 * A declaration must define exactly one of the following:
 * - `within`: a selector matched against the node's ancestors (and itself).
 * - `is`: a selector or a predicate matched against the node itself.
 *
 * Exactly one of `within`/`is` should be provided.
 *
 * @typedef {Object} NodeProperties
 * @property {string} [within] CSS selector matching an ancestor or the node
 *      itself.
 * @property {string | ((node: Node) => boolean)} [is] CSS selector or predicate
 *      matching the node itself.
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
 * node. A property is acquired either from a containing region (`within`) or
 * from the node itself (`is`).
 */
export class RegionPlugin extends Plugin {
    static id = "region";
    static shared = ["getProperty"];

    indexDeclarations() {
        /** @type {Map<string, NodeProperties[]>} */
        this.declarationsByName = new Map();
        for (const declaration of this.getResource("region_properties")) {
            for (const name in declaration) {
                if (name !== "is" && name !== "within") {
                    if (!this.declarationsByName.has(name)) {
                        this.declarationsByName.set(name, []);
                    }
                    this.declarationsByName.get(name).push(declaration);
                }
            }
        }
    }

    /**
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
     * - boolean: ANDed, so any `false` wins, a restrictive capability is
     *   disabled as soon as one declaration says so.
     * - otherwise: the first matching declaration (in resource order) wins.
     * - a mix of both: the booleans win, e.g. `removable: false` overrides
     *   `removable: "cascade"`.
     *
     * @param {Node} node
     * @param {string} name
     * @returns {*}
     */
    getProperty(node, name) {
        if (!this.declarationsByName) {
            this.indexDeclarations();
        }
        let result;
        for (const declaration of this.declarationsByName.get(name) ?? []) {
            if (this.matches(declaration, node)) {
                const value = declaration[name];
                result = typeof value === "boolean" ? (result ?? true) && value : result ?? value;
                if (result === false) {
                    // Nothing overrides a `false`.
                    return false;
                }
            }
        }
        return result;
    }
}
