/** @odoo-module */

import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { registry } from "@web/core/registry";

function makeMockLine(overrides = {}) {
    return {
        order_id: true,
        combo_parent_id: false,
        combo_line_ids: [],
        customer_note: "",
        note: "",
        price: 9.99,
        price_type: "original",
        discount: 0,
        packLotLines: [],
        currency: { id: 1 },
        product_id: {
            uom_id: { name: "Units" },
            taxes_id: [],
            tracking: "none",
            getImageUrl() {
                return "";
            },
        },
        orderDisplayProductName: {
            name: "Margherita Pizza",
            attributeString: "",
        },
        currencyDisplayPriceUnit: "$ 9.99",
        currencyDisplayPrice: "$ 9.99",
        displayPriceNoDiscount: 9.99,
        isSelected() {
            return false;
        },
        getDisplayClasses() {
            return {};
        },
        getQuantityStr() {
            return { unitPart: "1", decimalPart: "", decimalPoint: "." };
        },
        getDiscountStr() {
            return "0";
        },
        ...overrides,
    };
}

class OrderlineDefault extends Component {
    static template = "pos_owlybook.OrderlineDefault";
    static components = { Orderline };
}

OrderlineDefault.storyConfig = {
    title: "Orderline - Default",
    component: Orderline,
    props: {
        line: {
            value: makeMockLine(),
            readonly: true,
            help: "Mock POS order line object",
        },
        mode: { value: "display" },
        onClick: { value: () => {}, readonly: true },
        onLongPress: { value: () => {}, readonly: true },
    },
};

class OrderlineSelected extends Component {
    static template = "pos_owlybook.OrderlineSelected";
    static components = { Orderline };
}

OrderlineSelected.storyConfig = {
    title: "Orderline - Selected",
    component: Orderline,
    props: {
        line: {
            value: makeMockLine({
                isSelected: () => true,
                orderDisplayProductName: {
                    name: "Caesar Salad",
                    attributeString: "Large",
                },
                currencyDisplayPriceUnit: "$ 12.50",
                currencyDisplayPrice: "$ 25.00",
                price: 12.5,
                getQuantityStr: () => ({
                    unitPart: "2",
                    decimalPart: "",
                    decimalPoint: ".",
                }),
            }),
            readonly: true,
        },
        mode: { value: "display" },
        onClick: { value: () => {}, readonly: true },
        onLongPress: { value: () => {}, readonly: true },
    },
};

class OrderlineDiscount extends Component {
    static template = "pos_owlybook.OrderlineDiscount";
    static components = { Orderline };
}

OrderlineDiscount.storyConfig = {
    title: "Orderline - With Discount",
    component: Orderline,
    props: {
        line: {
            value: makeMockLine({
                discount: 15,
                orderDisplayProductName: {
                    name: "Club Sandwich",
                    attributeString: "",
                },
                currencyDisplayPriceUnit: "$ 8.49",
                currencyDisplayPrice: "$ 8.49",
                displayPriceNoDiscount: 9.99,
                price: 8.49,
                getDiscountStr: () => "15",
            }),
            readonly: true,
        },
        mode: { value: "display" },
        onClick: { value: () => {}, readonly: true },
        onLongPress: { value: () => {}, readonly: true },
    },
};

class OrderlineWithNote extends Component {
    static template = "pos_owlybook.OrderlineWithNote";
    static components = { Orderline };
}

OrderlineWithNote.storyConfig = {
    title: "Orderline - With Customer Note",
    component: Orderline,
    props: {
        line: {
            value: makeMockLine({
                customer_note: "No onions please",
                orderDisplayProductName: {
                    name: "Beef Burger",
                    attributeString: "Medium Rare",
                },
                currencyDisplayPriceUnit: "$ 14.99",
                currencyDisplayPrice: "$ 14.99",
                price: 14.99,
            }),
            readonly: true,
        },
        mode: { value: "display" },
        onClick: { value: () => {}, readonly: true },
        onLongPress: { value: () => {}, readonly: true },
    },
};

export const PosOrderlineStories = {
    title: "POS Components",
    module: "point_of_sale",
    stories: [OrderlineDefault, OrderlineSelected, OrderlineDiscount, OrderlineWithNote],
};

registry.category("stories").add("pos_owlybook.pos_orderline", PosOrderlineStories);
