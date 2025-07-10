/**
 * reconstruction of a customizable_css_variable:
 * --optionName-propertyLikeName (i.e. --button-padding-x, --button-padding-y
 */

function generateSimpleMailingVariables(object, prefix, selectors, properties) {
    for (const property of properties) {
        object[`--${prefix}-${property}`] = {
            properties: [property],
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
);
