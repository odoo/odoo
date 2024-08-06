import { PosData } from "@point_of_sale/app/models/data_service";
import { patch } from "@web/core/utils/patch";
import { batched } from "@web/core/utils/timing";

function nextAnimationFrame() {
    return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

patch(PosData.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("ORDER_UPDATE", this.loadMultiPosData.bind(this));

        this.multiPosLoadTimeout = null;
        this.multiPosSendTimeout = null;
        this.multiPosBatch = batched(this.sendMultiPosData.bind(this), () => nextAnimationFrame());
        this.multiPosSyncBusy = false;
        this.multiPosDataByKey = {
            upsert: {},
            delete: {},
        };

        // Monititor models changes
        for (const [model, config] of Object.entries(this.opts.trackedModels)) {
            for (const event of config.events) {
                this.models[model].addEventListener(event, (data) => {
                    this.generateMultiPosData(data);
                });
            }
        }
    },
    generateMultiPosData(data) {
        const record = this.models[data.model].get(data.id);
        const key = this.opts.trackedModels[data.model].key;
        const keyVal = data.values[key] || record?.[key];
        const event = ["update", "create"].includes(data.event) ? "upsert" : "delete";

        if (!keyVal || (!record && data.event !== "delete")) {
            return;
        }

        if (!this.multiPosDataByKey[event][data.model]) {
            this.multiPosDataByKey[event][data.model] = {};
        }

        try {
            if (event !== "delete") {
                const newData = this.dataFormatter(record);

                if (this.multiPosDataByKey[event][data.model][keyVal]) {
                    this.multiPosDataByKey[event][data.model][keyVal] = {
                        ...this.multiPosDataByKey[event][data.model][keyVal],
                        ...newData,
                    };
                } else {
                    this.multiPosDataByKey[event][data.model][keyVal] = newData;
                }
            } else {
                this.multiPosDataByKey[event][data.model][keyVal] = data.values;
                delete this.multiPosDataByKey["upsert"][data.model][keyVal];
            }
        } catch {
            return false;
        }

        this.multiPosBatch();
    },
    async sendMultiPosData() {
        if (this.multiPosSyncBusy) {
            return;
        }

        const copy = { ...this.multiPosDataByKey };
        this.multiPosSyncBusy = true;
        this.multiPosDataByKey = {
            upsert: {},
            delete: {},
        };

        try {
            await this.call("pos.session", "notify_model_changes", [odoo.pos_session_id, copy]);
        } catch {
            console.info("Failed sending sync data");
        }

        // Used to avoid websocket loop
        clearTimeout(this.multiPosSendTimeout);
        this.multiPosSendTimeout = setTimeout(() => {
            this.multiPosSyncBusy = false;
        }, 300);
    },
    async loadMultiPosData(data) {
        this.multiPosSyncBusy = true;

        // Get all keys that will be created or updated to avoid deleting
        // them and getting ui flickering
        const allKeys = new Set(
            Object.entries(data.upsert).flatMap(([model, records]) => {
                this.changePosOwner(model, Object.values(records));
                return Object.keys(records);
            })
        );

        for (const [model, records] of Object.entries(data.delete)) {
            const modelObj = this.models[model];
            const key = this.opts.trackedModels[model].key;

            Object.entries(records).map(([keyVal, r]) => {
                const record = modelObj.getBy(key, keyVal);
                if (record) {
                    // Delete record will not be able to remove protected keys from indexedRecords
                    // This is usefull to avoid removing a record who's will be updated just after
                    record.delete({ protectedKeys: allKeys });
                }
            });
        }

        const newRecords = Object.entries(data.upsert).reduce((acc, [model, records]) => {
            acc[model] = Object.values(records);
            return acc;
        }, {});

        const missingData = await this.missingRecursive(newRecords);
        this.models.loadData(missingData, [], true);

        // Used to avoid websocket loop, without this, some posts actions will trigger the sync again
        // and the sync will be stuck in a loop
        clearTimeout(this.multiPosLoadTimeout);
        this.multiPosLoadTimeout = setTimeout(() => {
            this.multiPosSyncBusy = false;
        }, 300);
    },
    // This function is used to change the owner of the record to the current PoS, user and session.
    // Without this change, the current PoS will not be able to pay the order.
    changePosOwner(model, records) {
        const modelFields = this.models[model].modelFields;

        for (const record of records) {
            for (const key in record) {
                if (modelFields[key] && modelFields[key].relation === "pos.session") {
                    record[key] = this.models["pos.session"].getFirst().id;
                } else if (modelFields[key] && modelFields[key].relation === "pos.config") {
                    record[key] = this.models["pos.config"].getFirst().id;
                } else if (modelFields[key] && modelFields[key].relation === "res.users") {
                    record[key] = this.models["res.users"].getFirst().id;
                }
            }
        }
    },
});
