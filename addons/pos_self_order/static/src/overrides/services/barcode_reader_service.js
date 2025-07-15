import { patch } from "@web/core/utils/patch";
import { BarcodeReader } from "@point_of_sale/app/services/barcode_reader_service";

patch(BarcodeReader.prototype, {
    async _scan(code) {
        if (!code) {
            return;
        }

        const match = code.match(/pos-self\/(?<configId>\d+)\?.*?order_uuid=(?<uuid>[\w-]+)/);
        if (!match) {
            return await super._scan(code);
        }

        const { uuid } = match.groups;
        const parseBarcode = {
            type: "order",
            code: code,
            uuid: uuid,
        };

        const cbMaps = this.exclusiveCbMap ? [this.exclusiveCbMap] : [...this.cbMaps];

        if (Array.isArray(parseBarcode)) {
            cbMaps.map((cb) => cb.gs1?.(parseBarcode));
        } else {
            const cbs = cbMaps.map((cbMap) => cbMap[parseBarcode.type]).filter(Boolean);
            if (cbs.length === 0) {
                this.showNotFoundNotification(parseBarcode);
            }
            for (const cb of cbs) {
                await cb(parseBarcode);
            }
        }
    },
});
