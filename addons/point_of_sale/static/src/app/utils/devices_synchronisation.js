import { Domain } from "@web/core/domain";
import { logPosMessage } from "./pretty_console_log";

const CONSOLE_COLOR = "#b56be3";
/**
 * Class representing the synchronization of records.
 * This class handles the setup and management of dynamic (flexible) models
 * that can be created in the frontend and static models that are predefined.
 */
export default class DevicesSynchronisation {
    constructor(dynamicModels, staticModels, posStore) {
        this.setup(dynamicModels, staticModels, posStore);
    }

    /**
     * Setup the record synchronization with dynamic and static models.
     * @param {Array} dynamicModels - Models that can be created in the frontend.
     * @param {Array} staticModels - Predefined models that are static.
     * @param {Object} posStore - The posStore instance.
     */
    setup(dynamicModels, staticModels, posStore) {
        this.dynamicModels = new Set(dynamicModels);
        this.staticModels = new Set(staticModels);
        this.pos = posStore;
        this.models = posStore.models;

        // Connect websocket to receive synchronisation notification
        this.pos.data.connectWebSocket("SYNCHRONISATION", this.collect.bind(this));
    }

    /**
     * Dispatch the synchronization of records.
     * This method will dispatch the synchronization of records to the
     * backend to inform others devices that a record has been updated,
     * @param {Object} data - The data that needs to be synchronized.
     */
    async dispatch(data) {
        const recordIds = Object.entries(data).reduce((acc, [model, records]) => {
            if (!this.staticModels.has(model)) {
                return acc;
            }
            acc[model] = records.map((record) => record.id);
            return acc;
        }, {});

        logPosMessage("Synchronisation", "dispatch", "Disptaching synchronization", CONSOLE_COLOR);
        await this.pos.data.call("pos.config", "notify_synchronisation", [
            odoo.pos_config_id,
            odoo.pos_session_id,
            odoo.login_number,
            recordIds,
        ]);
    }

    /**
     * Collect the synchronization of records.
     * This method will collect the synchronization of records from the backend
     * to update the records in the frontend.
     * @param {Object} data - The data that needs to be synchronized.
     * @param {Number} data.login_number - Session login number.
     * @param {Number} data.session_id - Current session id.
     * @param {Object} data.static_records - Records data that need to be synchronized.
     */
    async collect(data) {
        const { static_records, session_id, login_number } = data;
        const isSameDevice = odoo.login_number == login_number || odoo.pos_session_id != session_id;

        logPosMessage(
            "Synchronisation",
            "collect",
            `Incoming synchronization from ${isSameDevice ? "this" : "another"} device`,
            CONSOLE_COLOR
        );

        if (isSameDevice) {
            return;
        }

        if (Object.keys(static_records).length) {
            this.processStaticRecords(static_records);
        }

        return await this.readDataFromServer();
    }

    /**
     * Read data from the server.
     * This method will read the data from the server to update the records in the frontend
     * and synchronize the records with other devices.
     */
    async readDataFromServer() {
        const serverOpenOrders = this.pos.getOpenOrders().filter((o) => typeof o.id === "number");
        const { domain, recordIds } = this.constructOrdersDomain(serverOpenOrders);
        let response = {};
        try {
            response = await this.pos.data.call("pos.config", "read_config_open_orders", [
                odoo.pos_config_id,
                domain,
                recordIds,
            ]);
        } catch (error) {
            logPosMessage(
                "Synchronisation",
                "readDataFromServer",
                `Error reading open orders data from server: ${error}`,
                CONSOLE_COLOR
            );
            return;
        }

        if (Object.keys(response.dynamic_records).length) {
            const missing = await this.pos.data.missingRecursive(response.dynamic_records);
            const { dynamicR, staticR } = Object.entries(missing).reduce(
                (acc, [model, records]) => {
                    if (this.dynamicModels.has(model)) {
                        acc.dynamicR[model] = records;
                    } else if (this.staticModels.has(model)) {
                        acc.staticR[model] = records;
                    }
                    return acc;
                },
                { dynamicR: {}, staticR: {} }
            );

            this.processStaticRecords(staticR);
            await this.processDynamicRecords(dynamicR);
        }

        if (Object.keys(response.deleted_record_ids).length) {
            this.processDeletedRecords(response.deleted_record_ids);
        }
    }

    /**
     * Process the static records.
     * This method will process the static records to update the records in the frontend.
     * @param {Object} staticRecords - Records data that need to be synchronized.
     */
    processStaticRecords(staticRecords) {
        return this.models.connectNewData(staticRecords);
    }

    /**
     * Process the dynamic records.
     * This method will process the dynamic records to update the records in the frontend.
     * @param {Object} dynamicRecords - Record write dates by ids and models.
     */
    async processDynamicRecords(dynamicRecords) {
        return this.models.connectNewData(dynamicRecords);
    }

    /**
     * Process the deleted records.
     * This method will process the deleted records to update the records in the frontend.
     * @param {Object} deletedRecords - Ids of inexisting records in the backend by models.
     */
    processDeletedRecords(deletedRecords) {
        for (const [model, ids] of Object.entries(deletedRecords)) {
            const records = this.models[model].readMany(ids);
            this.models[model].deleteMany(records.filter(Boolean), { silent: true });
        }
    }

    /**
     * Get the open orders.
     * This method will get local open orders with a server id.
     * @returns {Array} - Array of domain conditions.
     */
    constructOrdersDomain() {
        const dynamicModels = this.dynamicModels;
        const recordsToCheck = Array.from(dynamicModels).reduce((acc, model) => {
            acc[model] = this.models[model].filter(
                (r) => !this.pos.data.opts.databaseTable[model]?.condition(r)
            );
            return acc;
        }, {});

        const recordIdsByModel = {};
        const domainByModel = Object.entries(recordsToCheck).reduce((acc, [model, records]) => {
            const serverRecs = records.filter((r) => typeof r.id === "number");
            const ids = serverRecs.map((r) => r.id);
            const config = this.pos.config;
            const domains = [];

            if (ids.length === 0 && model !== "pos.order") {
                return acc;
            }

            recordIdsByModel[model] = ids;
            for (const record of serverRecs) {
                const recordDateTime = record.write_date.plus({ seconds: 1 }).toUTC();
                const recordDateTimeString = recordDateTime.toFormat("yyyy-MM-dd HH:mm:ss", {
                    numberingSystem: "latn",
                });
                domains.push(
                    new Domain([
                        ["id", "=", record.id],
                        ["write_date", ">=", recordDateTimeString],
                    ])
                );
            }

            let domain = Domain.or(domains);
            if (model === "pos.order") {
                domain = Domain.or([
                    domain,
                    new Domain([
                        ["id", "not in", ids],
                        ["state", "=", "draft"],
                        ["config_id", "in", [config.id, ...config.trusted_config_ids]],
                    ]),
                ]);

                acc[model] = domain.toList();
            }

            return acc;
        }, {});

        return { domain: domainByModel, recordIds: recordIdsByModel };
    }
}
