export const mockSelfRoutes = {
    default: {
        route: "/pos-self/1",
        paramSpecs: [],
        regex: {},
    },
    product_list: {
        route: "/pos-self/1/products",
        paramSpecs: [],
        regex: {},
    },
    product: {
        route: "/pos-self/1/product/{int:id}",
        paramSpecs: [
            {
                type: "int",
                name: "id",
            },
        ],
        regex: {},
    },
    combo_selection: {
        route: "/pos-self/1/combo-selection/{int:id}",
        paramSpecs: [
            {
                type: "int",
                name: "id",
            },
        ],
        regex: {},
    },
    cart: {
        route: "/pos-self/1/cart",
        paramSpecs: [],
        regex: {},
    },
    payment: {
        route: "/pos-self/1/payment",
        paramSpecs: [],
        regex: {},
    },
    confirmation: {
        route: "/pos-self/1/confirmation/{string:orderAccessToken}/{string:screenMode}",
        paramSpecs: [
            {
                type: "string",
                name: "orderAccessToken",
            },
            {
                type: "string",
                name: "screenMode",
            },
        ],
        regex: {},
    },
    location: {
        route: "/pos-self/1/location",
        paramSpecs: [],
        regex: {},
    },
    stand_number: {
        route: "/pos-self/1/stand_number",
        paramSpecs: [],
        regex: {},
    },
    orderHistory: {
        route: "/pos-self/1/orders",
        paramSpecs: [],
        regex: {},
    },
};
