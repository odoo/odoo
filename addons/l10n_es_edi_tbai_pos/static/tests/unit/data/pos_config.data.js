import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    company_id: 254,
}));

patch(PosConfig.prototype, {
    _load_pos_data_read(data) {
        const records = super._load_pos_data_read(data);
        records[0]._l10n_es_pos_fiscal_mode = "tbai";
        return records;
    },
});
