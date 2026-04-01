import { registry } from "@web/core/registry";
import { unique, zip } from "@web/core/utils/arrays";
import { Deferred } from "@web/core/utils/concurrency";

export const ERROR_INACCESSIBLE_OR_MISSING = Symbol("INACCESSIBLE OR MISSING RECORD ID");

function isId(val) {
    return Number.isInteger(val) && val >= 1;
}

/**
 * @typedef {Record<string, (string|ERROR_INACCESSIBLE_OR_MISSING)>} DisplayNames
 */

export const nameService = {
    dependencies: ["orm"],
    async: ["loadDisplayNames"],
    start(env, { orm }) {
        let cache = {};
        const batches = {};

        function clearCache() {
            cache = {};
        }

        env.bus.addEventListener("ACTION_MANAGER:UPDATE", clearCache);

        function getMapping(resModel) {
            if (!cache[resModel]) {
                cache[resModel] = {};
            }
            return cache[resModel];
        }

        /**
         * @param {string} resModel valid resModel name
         * @param {DisplayNames} displayNames
         */
        function addDisplayNames(resModel, displayNames) {
            const mapping = getMapping(resModel);
            for (const resId in displayNames) {
                mapping[resId] = new Deferred();
                mapping[resId].resolve(displayNames[resId]);
            }
        }

        /**
         * @param {string} resModel valid resModel name
         * @param {number[]} resIds valid ids
         * @returns {Promise<DisplayNames>}
         */
        async function loadDisplayNames(resModel, resIds) {
            const mapping = getMapping(resModel);
            const proms = [];
            const resIdsToFetch = [];
            for (const resId of unique(resIds)) {
                if (!isId(resId)) {
                    throw new Error(`Invalid ID: ${resId}`);
                }
                if (!(resId in mapping)) {
                    mapping[resId] = new Deferred();
                    resIdsToFetch.push(resId);
                }
                proms.push(mapping[resId]);
            }
            if (resIdsToFetch.length) {
                if (batches[resModel]) {
                    batches[resModel].push(...resIdsToFetch);
                } else {
                    batches[resModel] = resIdsToFetch;
                    await Promise.resolve();
                    const idsInBatch = unique(batches[resModel]);
                    delete batches[resModel];

                    const specification = { display_name: {} };
                    orm.silent
                        .webSearchRead(resModel, [["id", "in", idsInBatch]], {
                            specification,
                            context: { active_test: false },
                        })
                        .then(({ records }) => {
                            const displayNames = Object.fromEntries(
                                records.map((rec) => [rec.id, rec.display_name])
                            );
                            for (const resId of idsInBatch) {
                                mapping[resId].resolve(
                                    resId in displayNames
                                        ? displayNames[resId]
                                        : ERROR_INACCESSIBLE_OR_MISSING
                                );
                            }
                        });
                }
            }
            const names = await Promise.all(proms);
            return Object.fromEntries(zip(resIds, names));
        }

        return { addDisplayNames, clearCache, loadDisplayNames };
    },
};

registry.category("services").add("name", nameService);
