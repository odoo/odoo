/**
 * reconstruction of a customizable_css_variable:
 * --optionName-propertyLikeName (i.e. --button-padding-x, --button-padding-y
 */

import { BASE_CONTAINER_CLASS } from "@html_editor/utils/base_container";

function getProperties(propertyDescription) {
    switch (propertyDescription) {
        case "padding-y":
            return ["padding-top", "padding-bottom"];
        case "padding-x":
            return ["padding-left", "padding-right"];
        default:
            return [propertyDescription];
    }
}

function generateSimpleMailingVariables(prefix, selectors, properties) {
    const variables = {};
    for (const propertyDescription of properties) {
        variables[`--${prefix}-${propertyDescription}`] = {
            properties: getProperties(propertyDescription),
            selectors: selectors,
        };
    }
    return variables;
}

// Properties and default values:

/* eslint-disable */
const wrapperProperties = [
    "background-color",
];

const textProperties = [
    "font-size",
    "font-weight",
    "font-style",
    "font-family",
    "text-decoration-line",
    "color",
];

const textContainerProperties = [
    "margin-bottom",
];

const buttonProperties = [
    ...textProperties,
    "background-color",
    "padding-x",
    "padding-y",
    "border-style",
    "border-width",
    "border-color",
];

const sizedButtonProperties =  [
    "font-size",
    "padding-x",
    "padding-y",
];

const outlinedButtonProperties = [
    "background-color",
    "color",
    "border-color",
];

const separatorProperties = [
    "border-top-width",
    "border-style",
    "border-color",
    "width",
];
/* eslint-enable */

export const CUSTOMIZE_MAILING_VARIABLES = Object.assign(
    generateSimpleMailingVariables("wrapper", ["> [data-snippet]"], wrapperProperties),
    (() => {
        const variables = {};
        for (const depth of [1, 2, 3]) {
            const prefix = `h${depth}`;
            Object.assign(
                variables,
                generateSimpleMailingVariables(
                    prefix,
                    [prefix],
                    [...textProperties, ...textContainerProperties]
                )
            );
        }
        return variables;
    })(),
    generateSimpleMailingVariables("text", [`.${BASE_CONTAINER_CLASS}`, "p", "li"], textProperties),
    generateSimpleMailingVariables("text-container", ["p", "ul"], textContainerProperties),
    generateSimpleMailingVariables(
        "link",
        ["a:not(.btn):not(:has(.fa, img))", "a.btn.btn-link"],
        textProperties
    ),
    generateSimpleMailingVariables(
        "btn-primary",
        ["a.btn.btn-fill-primary", "a.btn.btn-outline-primary", "a.btn.btn-primary"],
        buttonProperties
    ),
    generateSimpleMailingVariables(
        "btn-secondary",
        ["a.btn.btn-fill-secondary", "a.btn.btn-outline-secondary", "a.btn.btn-secondary"],
        buttonProperties
    ),
    generateSimpleMailingVariables(
        "btn-primary-lg",
        ["a.btn.btn-fill-primary.btn-lg", "a.btn.btn-outline-primary.btn-lg", "a.btn.btn-primary.btn-lg"],
        sizedButtonProperties
    ),
    generateSimpleMailingVariables(
        "btn-primary-sm",
        ["a.btn.btn-fill-primary.btn-sm", "a.btn.btn-outline-primary.btn-sm", "a.btn.btn-primary.btn-sm"],
        sizedButtonProperties
    ),
    generateSimpleMailingVariables(
        "btn-secondary-lg",
        ["a.btn.btn-fill-secondary.btn-lg", "a.btn.btn-outline-secondary.btn-lg", "a.btn.btn-secondary.btn-lg"],
        sizedButtonProperties
    ),
    generateSimpleMailingVariables(
        "btn-secondary-sm",
        ["a.btn.btn-fill-secondary.btn-sm", "a.btn.btn-outline-secondary.btn-sm", "a.btn.btn-secondary.btn-sm"],
        sizedButtonProperties
    ),
    generateSimpleMailingVariables(
        "btn-primary-outline",
        ["a.btn.btn-outline-primary"],
        outlinedButtonProperties
    ),
    generateSimpleMailingVariables(
        "btn-secondary-outline",
        ["a.btn.btn-outline-secondary"],
        outlinedButtonProperties
    ),
    generateSimpleMailingVariables("separator", ["hr"], separatorProperties)
);

export const CUSTOMIZE_MAILING_VARIABLES_DEFAULTS = {
    "--wrapper-background-color": {
        "background-color": "#FFFFFF",
    },
    "--h1-font-size": {
        "font-size": "28px",
    },
    "--h1-font-weight": {
        "font-weight": "500",
    },
    "--h1-font-style": {
        "font-style": "",
    },
    "--h1-font-family": {
        "font-family": "Arial,Helvetica Neue,Helvetica,sans-serif",
    },
    "--h1-text-decoration-line": {
        "text-decoration-line": "",
    },
    "--h1-color": {
        color: "rgb(0, 0, 0)",
    },
    "--h1-margin-bottom": {
        "margin-bottom": "7px",
    },
    "--h2-font-size": {
        "font-size": "23px",
    },
    "--h2-font-weight": {
        "font-weight": "500",
    },
    "--h2-font-style": {
        "font-style": "",
    },
    "--h2-font-family": {
        "font-family": "Arial,Helvetica Neue,Helvetica,sans-serif",
    },
    "--h2-text-decoration-line": {
        "text-decoration-line": "",
    },
    "--h2-color": {
        color: "rgb(0, 0, 0)",
    },
    "--h2-margin-bottom": {
        "margin-bottom": "7px",
    },
    "--h3-font-size": {
        "font-size": "20px",
    },
    "--h3-font-weight": {
        "font-weight": "500",
    },
    "--h3-font-style": {
        "font-style": "",
    },
    "--h3-font-family": {
        "font-family": "Arial,Helvetica Neue,Helvetica,sans-serif",
    },
    "--h3-text-decoration-line": {
        "text-decoration-line": "",
    },
    "--h3-color": {
        color: "rgb(0, 0, 0)",
    },
    "--h3-margin-bottom": {
        "margin-bottom": "7px",
    },
    "--text-font-size": {
        "font-size": "16px",
    },
    "--text-font-weight": {
        "font-weight": "400",
    },
    "--text-font-style": {
        "font-style": "",
    },
    "--text-font-family": {
        "font-family": "Arial,Helvetica Neue,Helvetica,sans-serif",
    },
    "--text-text-decoration-line": {
        "text-decoration-line": "",
    },
    "--text-color": {
        color: "rgb(0, 0, 0)",
    },
    "--text-container-margin-bottom": {
        "margin-bottom": "16px",
    },
    "--link-font-size": {
        "font-size": "16px",
    },
    "--link-font-weight": {
        "font-weight": "400",
    },
    "--link-font-style": {
        "font-style": "",
    },
    "--link-font-family": {
        "font-family": "Arial,Helvetica Neue,Helvetica,sans-serif",
    },
    "--link-text-decoration-line": {
        "text-decoration-line": "",
    },
    "--link-color": {
        color: "rgb(113, 75, 103)",
    },
    "--btn-primary-font-size": {
        "font-size": "12px",
    },
    "--btn-primary-color": {
        color: "rgb(255, 255, 255)",
    },
    "--btn-primary-background-color": {
        "background-color": "rgb(53, 151, 156)",
    },
    "--btn-primary-padding-x": {
        "padding-left": "10px",
        "padding-right": "10px",
    },
    "--btn-primary-padding-y": {
        "padding-top": "5px",
        "padding-bottom": "5px",
    },
    "--btn-primary-font-family": {
        "font-family": "Arial,Helvetica Neue,Helvetica,sans-serif",
    },
    "--btn-primary-border-style": {
        "border-style": "solid",
    },
    "--btn-primary-border-width": {
        "border-width": "1px",
    },
    "--btn-primary-border-color": {
        "border-color": "rgb(53, 151, 156)",
    },
    "--btn-primary-lg-font-size": {
        "font-size": "calc(var(--btn-primary-font-size) * 1.5)",
    },
    "--btn-primary-lg-padding-x": {
        "padding-left": "calc(var(--btn-primary-padding-x) * 2.5)",
        "padding-right": "calc(var(--btn-primary-padding-x) * 2.5)",
    },
    "--btn-primary-lg-padding-y": {
        "padding-top": "calc(var(--btn-primary-padding-y) * 1.5)",
        "padding-bottom": "calc(var(--btn-primary-padding-y) * 1.5)",
    },
    "--btn-primary-sm-font-size": {
        "font-size": "calc(var(--btn-primary-font-size) * 0.875)",
    },
    "--btn-primary-sm-padding-x": {
        "padding-left": "calc(var(--btn-primary-padding-x) * 0.3)",
        "padding-right": "calc(var(--btn-primary-padding-x) * 0.3)",
    },
    "--btn-primary-sm-padding-y": {
        "padding-top": "calc(var(--btn-primary-padding-y) * 0.20)",
        "padding-bottom": "calc(var(--btn-primary-padding-y) * 0.20)",
    },
    "--btn-primary-outline-color": {
        color: "var(--btn-primary-background-color)",
    },
    "--btn-primary-outline-background-color": {
        "background-color": "transparent",
    },
    "--btn-primary-outline-border-color": {
        "border-color": "var(--btn-primary-background-color)",
    },
    "--btn-secondary-font-size": {
        "font-size": "12px",
    },
    "--btn-secondary-color": {
        color: "rgb(255, 255, 255)",
    },
    "--btn-secondary-background-color": {
        "background-color": "rgb(104, 85, 99)",
    },
    "--btn-secondary-padding-x": {
        "padding-left": "10px",
        "padding-right": "10px",
    },
    "--btn-secondary-padding-y": {
        "padding-top": "5px",
        "padding-bottom": "5px",
    },
    "--btn-secondary-font-family": {
        "font-family": "Arial,Helvetica Neue,Helvetica,sans-serif",
    },
    "--btn-secondary-border-style": {
        "border-style": "solid",
    },
    "--btn-secondary-border-width": {
        "border-width": "1px",
    },
    "--btn-secondary-border-color": {
        "border-color": "rgb(104, 85, 99)",
    },
    "--btn-secondary-lg-font-size": {
        "font-size": "calc(var(--btn-secondary-font-size) * 1.5)",
    },
    "--btn-secondary-lg-padding-x": {
        "padding-left": "calc(var(--btn-secondary-padding-x) * 2.5)",
        "padding-right": "calc(var(--btn-secondary-padding-x) * 2.5)",
    },
    "--btn-secondary-lg-padding-y": {
        "padding-top": "calc(var(--btn-secondary-padding-y) * 1.5)",
        "padding-bottom": "calc(var(--btn-secondary-padding-y) * 1.5)",
    },
    "--btn-secondary-sm-font-size": {
        "font-size": "calc(var(--btn-secondary-font-size) * 0.875)",
    },
    "--btn-secondary-sm-padding-x": {
        "padding-left": "calc(var(--btn-secondary-padding-x) * 0.3)",
        "padding-right": "calc(var(--btn-secondary-padding-x) * 0.3)",
    },
    "--btn-secondary-sm-padding-y": {
        "padding-top": "calc(var(--btn-secondary-padding-y) * 0.20)",
        "padding-bottom": "calc(var(--btn-secondary-padding-y) * 0.20)",
    },
    "--btn-secondary-outline-color": {
        color: "var(--btn-secondary-background-color)",
    },
    "--btn-secondary-outline-background-color": {
        "background-color": "transparent",
    },
    "--btn-secondary-outline-border-color": {
        "border-color": "var(--btn-secondary-background-color)",
    },
    "--separator-border-top-width": {
        "border-top-width": "1px",
    },
    "--separator-border-style": {
        "border-style": "solid",
    },
    "--separator-border-color": {
        "border-color": "rgb(33, 37, 41)",
    },
    "--separator-width": {
        width: "100%",
    },
};
