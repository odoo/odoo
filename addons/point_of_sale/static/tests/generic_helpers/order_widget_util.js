import { negate } from "@point_of_sale/../tests/generic_helpers/utils";
/**
 * @typedef {{
 * withClass?: string, // ex: withClass: ".selected.blue"
 * withoutClass?: string,
 * run?: function | string,
 * productName?: string,
 * quantity?: string,
 * price?: string,
 * customerNote?: string,
 * comboParent?: string,
 * }} LineOptions
 */

/**
 * @param {LineOptions} options
 * @returns {import("@web_tour/js/tour_service").TourStep[]}
 */
export function hasLine({
    withClass = "",
    withoutClass = "",
    run = () => {},
    productName,
    quantity,
    price,
    priceUnit,
    customerNote,
    internalNote,
    comboParent,
    discount,
    oldPrice,
    priceNoDiscount,
    attributeLine,
} = {}) {
    let trigger = `.order-container .orderline${withClass}`;
    if (withoutClass) {
        trigger += `:not(${withoutClass})`;
    }
    if (productName) {
        trigger += `:has(.product-name:contains("${productName}"))`;
    }
    if (quantity) {
        quantity = parseFloat(quantity) % 1 === 0 ? parseInt(quantity).toString() : quantity;
        trigger += `:has(.qty:contains("${quantity}"))`;
    }
    if (price) {
        trigger += `:has(.price:contains("${price}"))`;
    }
    if (priceUnit) {
        trigger += `:has(.price-per-unit:contains("${priceUnit}"))`;
    }
    if (customerNote) {
        trigger += `:has(.info-list .customer-note:contains("${customerNote}"))`;
    }
    if (internalNote) {
        trigger += `:has(.info-list .o_tag_badge_text:contains("${internalNote}"))`;
    }
    if (comboParent) {
        trigger += `:has(.info-list .combo-parent-name:contains("${comboParent}"))`;
    }
    if (discount || discount === "") {
        trigger += `:has(.info-list .discount.em:contains("${discount}"))`;
    }
    if (priceNoDiscount) {
        trigger += `:has(.info-list:contains("${priceNoDiscount}"))`;
    }
    if (attributeLine) {
        trigger += `:has(.attribute-line:contains("${attributeLine}"))`;
    }
    const args = JSON.stringify(arguments[0]);
    return [
        {
            content: `Check orderline with attributes: ${args}`,
            trigger,
            run: typeof run === "string" ? run : () => run(trigger),
        },
    ];
}
/**
 * @param {LineOptions} options
 * @returns {import("@web_tour/tour_service").TourStep}
 */
export function doesNotHaveLine(options = {}) {
    const step = hasLine(options)[0];
    return [{ ...step, trigger: negate(step.trigger) }];
}

// TODO: there are instances where we have no selected orderline. Fix those instances

export function hasTotal(amount) {
    return [
        {
            isActive: ["desktop"],
            content: `order total amount is '${amount}'`,
            trigger: `.product-screen .order-summary .total:contains("${amount}")`,
        },
        {
            isActive: ["mobile"],
            content: `order total amount is '${amount}'`,
            trigger: `.product-screen .order-summary .total:contains("${amount}"):not(:visible)`,
        },
    ];
}
export function hasSubtotal(amount) {
    return [
        {
            isActive: ["desktop"],
            content: `order total amount is '${amount}'`,
            trigger: `.product-screen .order-summary .subtotal:contains("${amount}")`,
        },
        {
            isActive: ["mobile"],
            content: `order total amount is '${amount}'`,
            trigger: `.product-screen .order-summary .subtotal:contains("${amount}"):not(:visible)`,
        },
    ];
}
export function hasTax(amount) {
    return {
        content: `order total tax is '${amount}'`,
        trigger: `.order-summary .tax:contains("${amount}")`,
    };
}
export function hasInternalNote(note) {
    return [
        {
            content: `Order internal note is '${note}'`,
            trigger: `.order-container .internal-note-container span div:contains("${note}")`,
        },
    ];
}
export function hasCustomerNote(note) {
    return [
        {
            content: `Order customer note is '${note}'`,
            trigger: `.order-container .customer-note  div:contains("${note}")`,
        },
    ];
}

export function hasNoTax() {
    return {
        content: "order has not tax",
        trigger: negate(".tax-info"),
    };
}
