/** @odoo-module */

import { LoadableDataSource } from "./data_source";
import { MetadataRepository } from "./metadata_repository";

const { EventBus } = owl;

/** *
 * @typedef {object} DataSourceServices
 * @property {MetadataRepository} metadataRepository
 * @property {import("@web/core/orm_service")} orm
 * @property {() => void} notify
 *
 * @typedef {new (services: DataSourceServices, params: object) => any} DataSourceConstructor
 */

export class DataSources extends EventBus {
    constructor(orm) {
        super();
        this._orm = orm.silent;
        this._metadataRepository = new MetadataRepository(orm);
        this._metadataRepository.addEventListener("labels-fetched", () => this.notify());
        /** @type {Object.<string, any>} */
        this._dataSources = {};
    }

    /**
     * Create a new data source but do not register it.
     *
     * @param {DataSourceConstructor} cls Class to instantiate
     * @param {object} params Params to give to data source
     *
     * @returns {any}
     */
    create(cls, params) {
        return new cls(
            {
                orm: this._orm,
                metadataRepository: this._metadataRepository,
                notify: () => this.notify(),
            },
            params
        );
    }

    /**
     * Create a new data source and register it with the following id.
     *
     * @param {string} id
     * @param {DataSourceConstructor} cls Class to instantiate
     * @param {object} params Params to give to data source
     *
     * @returns {any}
     */
    add(id, cls, params) {
        this._dataSources[id] = this.create(cls, params);
        return this._dataSources[id];
    }

    async load(id, reload = false) {
        const dataSource = this.get(id);
        if (dataSource instanceof LoadableDataSource) {
            await dataSource.load({ reload });
        }
    }

    /**
     * Retrieve the data source with the following id.
     *
     * @param {string} id
     *
     * @returns {any}
     */
    get(id) {
        return this._dataSources[id];
    }

    /**
     * Check if the following is correspond to a data source.
     *
     * @param {string} id
     *
     * @returns {boolean}
     */
    contains(id) {
        return id in this._dataSources;
    }

    /**
     * Notify that a data source has been updated. Could be useful to
     * request a re-evaluation.
     */
    notify() {
        this.trigger("data-source-updated");
    }

    async waitForAllLoaded() {
        await Promise.all(
            Object.values(this._dataSources).map(
                (ds) => ds instanceof LoadableDataSource && ds.load()
            )
        );
    }
}
