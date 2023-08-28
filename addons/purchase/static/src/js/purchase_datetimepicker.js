/** @odoo-module */
import PublicWidget from "@web/legacy/js/public/public_widget";

export const PurchaseDatePicker = PublicWidget.Widget.extend({
    selector: ".o-purchase-datetimepicker",
    start() {
        this.call("datetime_picker", "create", {
            target: this.el,
            onChange: (newDate) => {
                const { accessToken, orderId, lineId } = this.el.dataset;
                this._rpc({
                    route: `/my/purchase/${orderId}/update?access_token=${accessToken}`,
                    params: {
                        [lineId]: newDate.toISODate(),
                    },
                });
            },
            pickerProps: {
                type: "date",
                value: luxon.DateTime.fromISO(this.el.dataset.value),
            },
        }).enable();
    },
});

PublicWidget.registry.PurchaseDatePicker = PurchaseDatePicker;
