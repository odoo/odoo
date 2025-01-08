import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";

export class PurchaseDatetimePicker extends Interaction {
    static selector = ".o-purchase-datetimepicker";

    start() {
        this.disableDateTimePicker = this.services.datetime_picker
            .create({
                target: this.el,
                onChange: (newDate) => {
                    const { accessToken, orderId, lineId } = this.el.dataset;
                    this.waitFor(
                        rpc(`/my/purchase/${orderId}/update?access_token=${accessToken}`, {
                            [lineId]: newDate.toISODate(),
                        })
                    );
                },
                pickerProps: {
                    type: "date",
                    value: luxon.DateTime.fromISO(this.el.dataset.value),
                },
            })
            .enable();
    }

    destroy() {
        this.disableDateTimePicker();
    }
}

registry
    .category("public.interactions")
    .add("purchase.purchase_datetime_picker", PurchaseDatetimePicker);
