odoo.define('point_of_sale.tour.ProductConfiguratorTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        pickRadio(name) {
            return [
                {
                    content: `picking radio attribute with name ${name}`,
                    trigger: `.product-configurator-popup .radio_attribute_label:contains('${name}')`,
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
                    content: 'product configurator is shown',
                    trigger: '.product-configurator-popup:not(:has(.oe_hidden))',
                    run: () => {},
                },
            ];
        }
    }

    return createTourMethods('ProductConfigurator', Do, Check);
});
