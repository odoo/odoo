/**
 * reconstruction of a customizable_css_variable:
 * --optionName-propertyLikeName (i.e. --button-padding-x, --button-padding-y
 */

export const CUSTOMIZE_MAILING_VARIABLES = {
    "--wrapper-background-color": {
        properties: ["background-color"],
        selectors: [".o_mail_wrapper_td > [data-snippet]"],
        default: "transparent",
    },
};
