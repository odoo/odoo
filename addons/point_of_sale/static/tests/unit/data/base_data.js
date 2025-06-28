export const baseData = {
    "pos.config": [
        {
            id: 1,
            name: "Hoot PoS",
        },
    ],
    "pos.session": [
        {
            id: 1,
            name: "Hoot Session",
            config_id: 1,
            state: "opened",
        },
    ],
    "res.country": [
        {
            id: 1,
            name: "Belgium",
            code: "BE",
            currency_id: 1,
        },
    ],
    "res.company": [
        {
            id: 1,
            name: "Hoot Company",
            currency_id: 1,
            country_id: 1,
            account_fiscal_country_id: 1,
        },
    ],
    "res.currency": [
        {
            id: 1,
            name: "Euro",
            symbol: "€",
            rounding: 0.01,
            position: "after",
        },
    ],
    "decimal.precision": [
        {
            id: 1,
            name: "Product Price",
            digits: 2,
        },
    ],
};
