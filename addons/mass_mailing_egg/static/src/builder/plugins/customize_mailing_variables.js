/**
 * reconstruction of a customizable_css_variable:
 * --optionName-propertyLikeName (i.e. --button-padding-x, --button-padding-y
 */

function getProperties(propertyDescription) {
    switch (propertyDescription) {
        case "padding-y":
            return ["padding-top", "padding-bottom"];
        case "padding-x":
            return ["padding-left", "padding-right"];
        default:
            return [propertyDescription]
    }
}

function generateSimpleMailingVariables(object, prefix, selectors, properties) {
    for (const propertyDescription of properties) {
        object[`--${prefix}-${propertyDescription}`] = {
            properties: getProperties(propertyDescription),
            selectors: selectors,
        };
    }
    return object;
}

const textProperties = [
    "font-size",
    "font-weight",
    "font-style",
    "font-family",
    "text-decoration-line",
    "color",
];

const buttonProperties = [
    "font-size",
    "color",
    "background-color",
    "padding-x",
    "padding-y",
    "font-family",
    "border-style",
    "border-width",
    "border-color",
]

export const CUSTOMIZE_MAILING_VARIABLES = Object.assign(
    {
        "--wrapper-background-color": {
            properties: ["background-color"],
            selectors: [".o_mail_wrapper_td > [data-snippet]"],
            default: "transparent",
        },
    },
    (() => {
        const object = {};
        for (const depth of [1, 2, 3]) {
            const prefix = `h${depth.toString()}`;
            generateSimpleMailingVariables(object, prefix, [prefix], textProperties);
        }
        return object;
    })(),
    generateSimpleMailingVariables({}, "text", ["p", "p > *", "li", "li > *"], textProperties),
    generateSimpleMailingVariables({}, "link", ["a:not(.btn)", "a.btn.btn-link"], textProperties),
    generateSimpleMailingVariables(
        {},
        "btn-primary",
        ["a.btn.btn-fill-primary", "a.btn.btn-outline-primary", "a.btn.btn-primary"],
        buttonProperties
    ),
    generateSimpleMailingVariables(
        {},
        "btn-secondary",
        ["a.btn.btn-fill-secondary", "a.btn.btn-outline-secondary", "a.btn.btn-secondary"],
        buttonProperties
    )
);
