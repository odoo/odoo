import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";

export function doubleClickLine(productName, quantity = "1.0") {
    return [
        ...Order.hasLine({
            run: "dblclick",
            productName,
            quantity,
        }),
    ].flat();
}
