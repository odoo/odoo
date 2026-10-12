import { models } from "@web/../tests/web_test_helpers";
import { isIterable } from "@web/core/utils/arrays";

const { DateTime } = luxon;

export class PosPrepLine extends models.ServerModel {
    _name = "pos.prep.line";

    create() {
        const prepLine = super.create(...arguments);
        this.write(isIterable(prepLine) ? prepLine : [prepLine], {
            write_date: DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss"),
        });
        return prepLine;
    }

    _load_pos_data_fields() {
        return [];
    }
}
