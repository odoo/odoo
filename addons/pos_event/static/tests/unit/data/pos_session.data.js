import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";
import { patch } from "@web/core/utils/patch";

patch(PosSession.prototype, {
    _load_pos_data_models() {
        return [
            ...super._load_pos_data_models(),
            "event.event.ticket",
            "event.event",
            "event.question.answer",
            "event.question",
            "event.registration.answer",
            "event.registration",
            "event.slot",
        ];
    },
});
