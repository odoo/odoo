import { getOrderLineValues } from "@pos_self_order/app/services/card_utils";

export const getEventOrderLineValues = function (
    selfOrder,
    productTemplate,
    qty,
    customer_note,
    selectedValues = {},
    customValues = {},
    comboValues = {}
) {
    const values = getOrderLineValues(
        selfOrder,
        productTemplate,
        qty,
        customer_note,
        selectedValues,
        customValues,
        comboValues
    );

    const { event_price, event_ticket_id } = customValues;
    if (event_ticket_id && (event_price || event_price === 0)) {
        values.event_ticket_id = event_ticket_id;
        values.price_unit = event_price;
    }
    return values;
};
