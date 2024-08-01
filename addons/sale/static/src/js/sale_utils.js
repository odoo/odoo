/**
 * Checks whether the 2 provided sale order lines are linked.
 *
 * @param linkingSaleOrderLine The line that is linking to the other line.
 * @param linkedSaleOrderLine The line that is linked by the other line.
 * @return {Boolean} Whether the 2 lines are linked.
 */
export function areSaleOrderLinesLinked(linkingSaleOrderLine, linkedSaleOrderLine) {
    const linkingId = linkingSaleOrderLine.isNew
        ? linkingSaleOrderLine.data.linked_virtual_id
        : linkingSaleOrderLine.data.linked_line_id[0];
    const linkedId = linkedSaleOrderLine.isNew
        ? linkedSaleOrderLine.data.virtual_id
        : linkedSaleOrderLine.resId;
    return linkingId && linkingId === linkedId;
}

/**
 * Gets the linked lines of the provided sale order line.
 *
 * @param saleOrderLine The line whose linked lines to get.
 * @return {Object[]} The list of linked lines.
 */
export function getLinkedSaleOrderLines(saleOrderLine) {
    const saleOrder = saleOrderLine.model.root;
    // TODO(loti): this doesn't work if some combo items are on another page.
    return saleOrder.data.order_line.records.filter(
        record => areSaleOrderLinesLinked(record, saleOrderLine)
    );
}
