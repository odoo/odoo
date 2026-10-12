import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";
import { patch } from "@web/core/utils/patch";

patch(PosConfig.prototype, {
    _load_self_data_models() {
        return [
            ...super._load_self_data_models(),
            "event.event.ticket",
            "event.event",
            "event.slot",
            "event.registration",
            "event.question",
            "event.question.answer",
            "event.registration.answer",
        ];
    },
});
