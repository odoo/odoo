import { models } from "@web/../tests/web_test_helpers";
import { isIterable } from "@web/core/utils/arrays";

const { DateTime } = luxon;

export class PosPayment extends models.ServerModel {
    _name = "pos.payment";

    create() {
        const posPayment = super.create(...arguments);
        this.write(isIterable(posPayment) ? posPayment : [posPayment], {
            write_date: DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss"),
        });
        return posPayment;
    }

    _load_pos_data_fields() {
        return [];
    }
}
