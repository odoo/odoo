import PublicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

export const PurchaseDatePicker = PublicWidget.Widget.extend({
    selector: ".o-purchase-datetimepicker",
    disabledInEditableMode: true,

    /**
     * @override
     */
    start() {
        this.disableDateTimePicker = this.call("datetime_picker", "create", {
            target: this.el,
            onChange: (newDate) => {
                const { accessToken, orderId, lineId } = this.el.dataset;
                rpc(`/my/purchase/${orderId}/update?access_token=${accessToken}`, {
                    [lineId]: newDate.toISODate(),
                });
            },
            pickerProps: {
                type: "date",
                value: luxon.DateTime.fromISO(this.el.dataset.value),
            },
        }).enable();
    },
    /**
     * @override
     */
    destroy() {
        this.disableDateTimePicker();
        return this._super(...arguments);
    },
});

PublicWidget.registry.PurchaseDatePicker = PurchaseDatePicker;
