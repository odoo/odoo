import { Mutex } from "@web/core/utils/concurrency";
import { checkFileSize } from "@web/core/utils/files";

export class BinaryFileManager {
    constructor(resModel, fields, parameters, context, orm, notificationService) {
        this.resModel = resModel;
        this.fields = [".id", ...fields];
        this.parameters = parameters;

        this.context = context;
        this.orm = orm;
        this.notificationService = notificationService;

        this.maxBatchSize = this.parameters.maxBatchSize * 0.95; // 0.95 for not calculated payload overhead
        this.delayAfterEachBatch = this.parameters.delayAfterEachBatch * 1000;

        this.dataToSend = {};

        this.mutex = new Mutex();
    }

    async addFile(id, field, file) {
        let data = await this._readFile(file);
        if (typeof data === "string" && data.startsWith("data:")) {
            // Remove data:image/*;base64,
            data = data.split(",")[1];
        }
        const dataSize = data.length;
        if (!checkFileSize(dataSize, this.notificationService)) {
            return;
        }

        if (this.getCurrentSize() + dataSize >= this.maxBatchSize) {
            await this.mutex.exec(async () => await this._send());
        }
        if (!(id in this.dataToSend)) {
            this.dataToSend[id] = Array(this.fields.length);
            this.dataToSend[id][0] = id;
        }
        const indexOfField = this.fields.indexOf(field, 1);
        this.dataToSend[id][indexOfField] = data;
    }

    async sendLastPayload() {
        if (Object.keys(this.dataToSend).length > 0) {
            await this.mutex.exec(async () => await this._send());
        }
    }

    async _send() {
        await new Promise((resolve) => {
            setTimeout(resolve, this.delayAfterEachBatch);
        });
        const data = Object.values(this.dataToSend);
        this.dataToSend = {};
        const context = {
            ...this.context,
            import_file: true,
            tracking_disable: this.parameters.tracking_disable,
            name_create_enabled_fields: this.parameters.name_create_enabled_fields || {},
            import_set_empty_fields: this.parameters.import_set_empty_fields || [],
            import_skip_records: this.parameters.import_skip_records || [],
        };
        let res;
        try {
            res = await this.orm.call(this.resModel, "load", [], {
                fields: this.fields,
                data,
                context,
            });
        } catch (error) {
            console.error(error);
            return { error };
        }
        return res;
    }

    _readFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onerror = (event) => reject(event);
            reader.onabort = (event) => reject(event);
            reader.onload = (event) => resolve(event.target.result);
            reader.readAsDataURL(file);
        });
    }

    getCurrentSize() {
        return JSON.stringify(this.dataToSend).length;
    }
}
