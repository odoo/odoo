/** @odoo-module */

import { Component } from "@odoo/owl";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { registry } from "@web/core/registry";

function makeMockLine(name, qty, price, overrides = {}) {
    return {
        order_id: true,
        combo_parent_id: false,
        combo_line_ids: [],
        customer_note: "",
        note: "",
        price,
        price_type: "original",
        discount: 0,
        packLotLines: [],
        currency: { id: 1 },
        product_id: {
            uom_id: { name: "Units" },
            taxes_id: [],
            tracking: "none",
            getImageUrl: () => "",
        },
        orderDisplayProductName: { name, attributeString: "" },
        currencyDisplayPriceUnit: `$ ${price.toFixed(2)}`,
        currencyDisplayPrice: `$ ${(price * qty).toFixed(2)}`,
        displayPriceNoDiscount: price,
        isSelected: () => false,
        getDisplayClasses: () => ({}),
        getQuantityStr: () => ({
            unitPart: String(qty),
            decimalPart: "",
            decimalPoint: ".",
        }),
        getDiscountStr: () => "0",
        ...overrides,
    };
}

function makeMockOrder(lines, overrides = {}) {
    const subtotal = lines.reduce((sum, l) => sum + l.price * parseInt(l.getQuantityStr().unitPart), 0);
    const tax = subtotal * 0.1;
    return {
        lines,
        currency: { id: 1 },
        general_customer_note: "",
        internal_note: "",
        config_id: { iface_tax_included: "subtotal" },
        prices: {
            taxDetails: { has_tax_groups: true },
        },
        currencyDisplayPriceExcl: `$ ${subtotal.toFixed(2)}`,
        currencyAmountTaxes: `$ ${tax.toFixed(2)}`,
        currencyDisplayPriceIncl: `$ ${(subtotal + tax).toFixed(2)}`,
        ...overrides,
    };
}

const sampleLines = [
    makeMockLine("Margherita Pizza", 1, 9.99),
    makeMockLine("Caesar Salad", 2, 6.50),
    makeMockLine("Sparkling Water", 3, 2.99, {
        isSelected: () => true,
    }),
];

const sampleOrder = makeMockOrder(sampleLines);

const orderWithNotes = makeMockOrder(
    [
        makeMockLine("Beef Burger", 1, 14.99, {
            customer_note: "No onions please",
        }),
        makeMockLine("French Fries", 1, 4.99),
    ],
    {
        general_customer_note: "Allergic to nuts\nPlease serve quickly",
        internal_note: JSON.stringify([
            { id: 1, text: "VIP customer", colorIndex: 1 },
            { id: 2, text: "Rush order", colorIndex: 4 },
        ]),
    }
);

class OrderDisplayDefault extends Component {
    static template = "pos_owlybook.OrderDisplayDefault";
    static components = { OrderDisplay };
}

OrderDisplayDefault.storyConfig = {
    title: "OrderDisplay - Default",
    component: OrderDisplay,
    props: {
        order: {
            value: sampleOrder,
            readonly: true,
            help: "Mock POS order with multiple lines",
        },
        slots: { value: {}, readonly: true },
        mode: { value: "display" },
    },
};

class OrderDisplayWithNotes extends Component {
    static template = "pos_owlybook.OrderDisplayWithNotes";
    static components = { OrderDisplay };
}

OrderDisplayWithNotes.storyConfig = {
    title: "OrderDisplay - With Notes",
    component: OrderDisplay,
    props: {
        order: {
            value: orderWithNotes,
            readonly: true,
            help: "Order with customer and internal notes",
        },
        slots: { value: {}, readonly: true },
        mode: { value: "display" },
    },
};

class OrderDisplayReceipt extends Component {
    static template = "pos_owlybook.OrderDisplayReceipt";
    static components = { OrderDisplay };
}

OrderDisplayReceipt.storyConfig = {
    title: "OrderDisplay - Receipt Mode",
    component: OrderDisplay,
    props: {
        order: {
            value: sampleOrder,
            readonly: true,
            help: "Order displayed in receipt mode (no summary)",
        },
        slots: { value: {}, readonly: true },
        mode: { value: "receipt" },
    },
};

export const PosOrderDisplayStories = {
    title: "POS Components",
    module: "point_of_sale",
    stories: [OrderDisplayDefault, OrderDisplayWithNotes, OrderDisplayReceipt],
};

registry.category("stories").add("pos_owlybook.pos_order_display", PosOrderDisplayStories);
