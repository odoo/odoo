import { models } from "@web/../tests/web_test_helpers";
import { isIterable } from "@web/core/utils/arrays";

const { DateTime } = luxon;

export class PosPrepOrder extends models.ServerModel {
    _name = "pos.prep.order";

    create() {
        const prepOrder = super.create(...arguments);
        this.write(isIterable(prepOrder) ? prepOrder : [prepOrder], {
            write_date: DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss"),
        });
        return prepOrder;
    }

    _load_pos_data_fields() {
        return [];
    }
}
