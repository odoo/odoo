import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";

patch(OrderWidget, {
    props: {
        ...OrderWidget.props,
        sales_person: { type: String, optional: true },
    }
});
