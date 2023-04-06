/** @odoo-module **/

import { Cache } from "@web/core/utils/cache";
import { registry } from "@web/core/registry";

/**
 * @typedef {Object} LoadFieldsOptions
 * @property {string[]|false} [fieldNames]
 * @property {string[]} [attributes]
 */

export const fieldService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const cache = new Cache(
            (resModel, options) => {
                return orm
                    .call(resModel, "fields_get", [options.fieldNames, options.attributes])
                    .catch((error) => {
                        cache.clear(resModel, options);
                        return Promise.reject(error);
                    });
            },
            (resModel, options) =>
                JSON.stringify([resModel, options.fieldNames, options.attributes])
        );

        env.bus.addEventListener("CLEAR-CACHES", () => cache.invalidate());

        /**
         * @param {string} resModel
         * @param {LoadFieldsOptions} [options]
         * @returns {Promise<object>}
         */
        async function loadFields(resModel, options = {}) {
            if (typeof resModel !== "string" || !resModel) {
                throw new Error(`Invalid model name: ${resModel}`);
            }
            return cache.read(resModel, options);
        }

        /**
         * @param {string} resModel valid model name
         * @param {Object} fieldDefs
         * @param {string[]} names
         */
        async function _loadPath(resModel, fieldDefs, names) {
            const [name, ...remainingNames] = names;
            const modelsInfo = [{ resModel, fieldDefs }];

            const fieldDef = fieldDefs[name];
            if (name !== "*" && !fieldDef) {
                return { isInvalid: "path", names, modelsInfo };
            }

            if (!remainingNames.length) {
                return { names, modelsInfo };
            }

            if (name === "*") {
                return { isInvalid: "path", names, modelsInfo };
            }

            if (fieldDef.relation) {
                const subResult = await _loadPath(
                    fieldDef.relation,
                    await loadFields(fieldDef.relation),
                    remainingNames
                );
                const result = {
                    names,
                    modelsInfo: [...modelsInfo, ...subResult.modelsInfo],
                };
                if (subResult.isInvalid) {
                    result.isInvalid = "path";
                }
                return result;
            }

            return { isInvalid: "path", names, modelsInfo };
        }

        /**
         * Note: the symbol * can be used at the end of path (e.g path="*" or path="user_id.*").
         * It says to load the fields of the appropriate model.
         * @param {string} resModel
         * @param {string} path
         * @returns {Promise<Object>}
         */
        async function loadPath(resModel, path = "*") {
            const fieldDefs = await loadFields(resModel);
            if (typeof path !== "string" || !path) {
                throw new Error(`Invalid path: ${path}`);
            }
            return _loadPath(resModel, fieldDefs, path.split("."));
        }

        return { loadFields, loadPath };
    },
};

registry.category("services").add("field", fieldService);
