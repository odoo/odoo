/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    pickRadio(name) {
        return [
            {
                content: `picking radio attribute with name ${name}`,
                trigger: `.product-configurator-popup .attribute-name-cell label[name='${name}']`,
            },
        ];
    }

    pickSelect(name) {
        return [
            {
                content: `picking select attribute with name ${name}`,
                trigger: `.product-configurator-popup .configurator_select:has(option:contains('${name}'))`,
                run: `text ${name}`,
            },
        ];
    }

    pickColor(name) {
        return [
            {
                content: `picking color attribute with name ${name}`,
                trigger: `.product-configurator-popup .configurator_color[data-color='${name}']`,
            },
        ];
    }

    fillCustomAttribute(value) {
        return [
            {
                content: `filling custom attribute with value ${value}`,
                trigger: `.product-configurator-popup .custom_value`,
                run: `text ${value}`,
            },
        ];
    }

    confirmAttributes() {
        return [
            {
                content: `confirming product configuration`,
                trigger: `.product-configurator-popup .button.confirm`,
            },
        ];
    }

    cancelAttributes() {
        return [
            {
                content: `canceling product configuration`,
                trigger: `.product-configurator-popup .button.cancel`,
            },
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                content: "product configurator is shown",
                trigger: ".product-configurator-popup:not(:has(.oe_hidden))",
                run: () => {},
            },
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("ProductConfigurator", Do, Check));
