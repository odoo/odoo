import { Plugin, useListener, usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { unique, zip } from "@web/core/utils/arrays";
import { ORM } from "@web/core/orm_plugin";
import { GlobalBusPlugin } from "@web/core/global_bus_plugin";

export const ERROR_INACCESSIBLE_OR_MISSING = Symbol("INACCESSIBLE OR MISSING RECORD ID");

function isId(val) {
    // normally, ids are positive, but negative ids can happen in rare cases, such as merging records in migration
    return Number.isInteger(val) && val !== 0;
}

/**
 * @typedef {Record<string, (string|ERROR_INACCESSIBLE_OR_MISSING)>} DisplayNames
 */

export class NamePlugin extends Plugin {
    /** @private */
    orm = usePlugin(ORM);
    /** @private */
    bus = usePlugin(GlobalBusPlugin).bus;
    /** @private */
    cache = {};
    /** @private */
    batches = {};

    setup() {
        useListener(this.bus, "ACTION_MANAGER:UPDATE", () => this.clearCache());
    }

    clearCache() {
        this.cache = {};
    }

    /** @private */
    getMapping(resModel) {
        if (!this.cache[resModel]) {
            this.cache[resModel] = {};
        }
        return this.cache[resModel];
    }

    /**
     * @param {string} resModel valid resModel name
     * @param {DisplayNames} displayNames
     */
    addDisplayNames(resModel, displayNames) {
        const mapping = this.getMapping(resModel);
        for (const resId in displayNames) {
            mapping[resId] = Promise.withResolvers();
            mapping[resId].resolve(displayNames[resId]);
        }
    }

    /**
     * @param {string} resModel valid resModel name
     * @param {number[]} resIds valid ids
     * @returns {Promise<DisplayNames>}
     */
    async loadDisplayNames(resModel, resIds) {
        const mapping = this.getMapping(resModel);
        const proms = [];
        const resIdsToFetch = [];
        for (const resId of unique(resIds)) {
            if (!isId(resId)) {
                throw new Error(`Invalid ID: ${resId}`);
            }
            if (!(resId in mapping)) {
                mapping[resId] = Promise.withResolvers();
                resIdsToFetch.push(resId);
            }
            proms.push(mapping[resId].promise);
        }
        if (resIdsToFetch.length) {
            if (this.batches[resModel]) {
                this.batches[resModel].push(...resIdsToFetch);
            } else {
                this.batches[resModel] = resIdsToFetch;
                await Promise.resolve();
                const idsInBatch = unique(this.batches[resModel]);
                delete this.batches[resModel];

                const specification = { display_name: {} };
                this.orm.silent
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
}

services.add(NamePlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the name service are removed
 * -----------------------------------------------------------------------------
 */
export const nameService = {
    dependencies: ["orm"],
    async: ["loadDisplayNames"],
    start() {
        return usePlugin(NamePlugin);
    },
};

registry.category("services").add("name", nameService);
