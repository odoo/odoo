export const changesToOrder = (
    order,
    skipped = false,
    orderPreparationCategories,
    cancelled = false
) => {
    const toAdd = [];
    const toRemove = [];

    const orderChanges = getOrderChanges(order, skipped, orderPreparationCategories);
    const linesChanges = !cancelled
        ? Object.values(orderChanges.orderlines)
        : Object.values(order.last_order_preparation_change.lines);

    for (const lineChange of linesChanges) {
        if (lineChange["quantity"] > 0 && !cancelled) {
            toAdd.push(lineChange);
        } else {
            lineChange["quantity"] = Math.abs(lineChange["quantity"]); // we need always positive values.
            toRemove.push(lineChange);
        }
    }

    return {
        new: toAdd,
        cancelled: toRemove,
        noteUpdated: Object.values(orderChanges.noteUpdated),
        generalNote: orderChanges.generalNote,
        modeUpdate: orderChanges.modeUpdate,
    };
};

/**
 * @returns {{ [lineKey: string]: { product_id: number, name: string, note: string, quantity: number } }}
 * This function recalculates the information to be sent to the preparation tools,
 * it uses the variable last_order_preparation_change which contains the last changes sent
 * to perform this calculation.
 */
export const getOrderChanges = (order, skipped = false, orderPreparationCategories) => {
    const prepaCategoryIds = orderPreparationCategories;
    const oldChanges = order.last_order_preparation_change.lines;
    const changes = {};
    const noteupdated = {};
    let changesCount = 0;
    let changeAbsCount = 0;
    let skipCount = 0;

    // Compares the orderlines of the order with the last ones sent.
    // When one of them has changed, we add the change.
    for (const orderline of order.get_orderlines()) {
        const product = orderline.get_product();
        const note = orderline.getNote();
        const lineKey = `${orderline.uuid} - ${note}`;
        const productCategoryIds = product.parentPosCategIds.filter((id) =>
            prepaCategoryIds.has(id)
        );

        if (prepaCategoryIds.size === 0 || productCategoryIds.length > 0) {
            const key = Object.keys(order.last_order_preparation_change.lines).find((k) =>
                k.startsWith(orderline.uuid)
            ); // find old data but note changed
            const quantity = orderline.get_quantity();

            const relatedKey = key !== lineKey ? key : lineKey; // if note update key would be different
            const quantityDiff = oldChanges[relatedKey]
                ? quantity - oldChanges[relatedKey].quantity
                : quantity;

            const lineDetails = {
                uuid: orderline.uuid,
                name: orderline.get_full_product_name(),
                basic_name: orderline.product_id.name,
                isCombo: orderline.combo_item_id?.id,
                product_id: product.id,
                attribute_value_ids: orderline.attribute_value_ids,
                quantity: quantityDiff,
                note: note,
                pos_categ_id: product.pos_categ_ids[0]?.id ?? 0,
                pos_categ_sequence: product.pos_categ_ids[0]?.sequence ?? 0,
            };

            if (quantityDiff && orderline.skip_change === skipped) {
                // if note update with qty add
                changes[lineKey] = lineDetails;
                changesCount += quantityDiff;
                changeAbsCount += Math.abs(quantityDiff);
                if (oldChanges[relatedKey] && oldChanges[relatedKey].note !== note) {
                    lineDetails.quantity = oldChanges[relatedKey].quantity;
                    noteupdated[lineKey] = lineDetails;
                }

                if (!orderline.skip_change) {
                    orderline.setHasChange(true);
                }
            } else {
                if (quantityDiff) {
                    skipCount += quantityDiff;
                    orderline.setHasChange(false);
                } else {
                    // If only note updated
                    if (oldChanges[relatedKey] && oldChanges[relatedKey].note !== note) {
                        lineDetails.quantity = orderline.qty;
                        noteupdated[lineKey] = lineDetails;
                        orderline.setHasChange(true);
                        changesCount += 1;
                    } else {
                        orderline.setHasChange(false);
                    }
                }
            }
        } else {
            orderline.setHasChange(false);
        }
    }
    // Checks whether an orderline has been deleted from the order since it
    // was last sent to the preparation tools. If so we add this to the changes.
    for (const [lineKey, lineResume] of Object.entries(order.last_order_preparation_change.lines)) {
        if (!order.models["pos.order.line"].getBy("uuid", lineResume["uuid"])) {
            if (!changes[lineKey]) {
                changes[lineKey] = {
                    uuid: lineResume["uuid"],
                    product_id: lineResume["product_id"],
                    name: lineResume["name"],
                    basic_name: lineResume["basic_name"],
                    isCombo: lineResume["isCombo"],
                    note: lineResume["note"],
                    attribute_value_ids: lineResume["attribute_value_ids"],
                    quantity: -lineResume["quantity"],
                };
                changeAbsCount += Math.abs(lineResume["quantity"]);
                changesCount += lineResume["quantity"];
            } else {
                changes[lineKey]["quantity"] -= lineResume["quantity"];
            }
        }
    }

    const result = {
        nbrOfSkipped: skipCount,
        nbrOfChanges: changeAbsCount,
        noteUpdated: noteupdated,
        orderlines: changes,
        count: changesCount,
    };

    // if `generalNote` key is present, then there is a change in the generalNote
    const lastGeneralNote = order.last_order_preparation_change.generalNote;
    if (lastGeneralNote !== order.general_note) {
        result.generalNote = order.general_note;
    }
    const sittingMode = order.last_order_preparation_change.sittingMode;
    if (
        (sittingMode !== "dine in" && !order.takeaway) ||
        (sittingMode !== "takeaway" && order.takeaway)
    ) {
        result.modeUpdate = true;
    }
    return result;
};
