odoo.define('point_of_sale.tour.ProductScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickDisplayedProduct(name) {
            return [
                {
                    content: `click product '${name}'`,
                    trigger: `.product-list .product-name:contains("${name}")`,
                },
            ];
        }

        clickOrderline(name, quantity) {
            return [
                {
                    content: `selecting orderline with product '${name}' and quantity '${quantity}'`,
                    trigger: `.order .orderline:not(:has(.selected)) .product-name:contains("${name}") ~ .info-list em:contains("${quantity}")`,
                },
                {
                    content: `orderline with product '${name}' and quantity '${quantity}' has been selected`,
                    trigger: `.order .orderline.selected .product-name:contains("${name}") ~ .info-list em:contains("${quantity}")`,
                    run: () => {},
                },
            ];
        }

        clickSubcategory(name) {
            return [
                {
                    content: `selecting '${name}' subcategory`,
                    trigger: `.category-list .category-simple-button:contains("${name}")`,
                },
                {
                    content: `'${name}' subcategory selected`,
                    trigger: `.breadcrumbs .breadcrumb-button:contains("${name}")`,
                    run: () => {},
                },
            ];
        }

        clickHomeCategory() {
            return [
                {
                    content: `click Home subcategory`,
                    trigger: `.breadcrumbs .breadcrumb-home`,
                },
            ];
        }

        /**
         * Press the numpad in sequence based on the given space-separated keys.
         * @param {String} keys space-separated numpad keys
         */
        pressNumpad(keys) {
            const numberChars = '. 0 1 2 3 4 5 6 7 8 9'.split(' ');
            const modeButtons = 'Qty Price Disc'.split(' ');
            function generateStep(key) {
                let trigger;
                if (numberChars.includes(key)) {
                    trigger = `.numpad .number-char:contains("${key}")`;
                } else if (modeButtons.includes(key)) {
                    trigger = `.numpad .mode-button:contains("${key}")`;
                } else if (key === 'Backspace') {
                    trigger = `.numpad .numpad-backspace`;
                } else if (key === '+/-') {
                    trigger = `.numpad .numpad-minus`;
                }
                return {
                    content: `'${key}' pressed in product screen numpad`,
                    trigger,
                };
            }
            return keys.split(' ').map(generateStep);
        }

        clickPayButton() {
            return [
                { content: 'click pay button', trigger: '.actionpad .button.pay' },
                {
                    content: 'now in payment screen',
                    trigger: '.pos-content .payment-screen',
                    run: () => {},
                },
            ];
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'product screen is shown',
                    trigger: '.product-screen:not(:has(.oe_hidden))',
                    run: () => {},
                },
            ];
        }
        selectedOrderlineHas(name, quantity, price) {
            const res = [
                {
                    // check first if the order widget is there and has orderlines
                    content: 'order widget has orderlines',
                    trigger: '.order .orderlines',
                    run: () => {},
                },
                {
                    content: `'${name}' is selected`,
                    trigger: `.order .orderline.selected .product-name:contains("${name}")`,
                    run: function () {}, // it's a check
                },
            ];
            if (quantity) {
                res.push({
                    content: `selected line has ${quantity} quantity`,
                    trigger: `.order .orderline.selected .product-name:contains("${name}") ~ .info-list em:contains("${quantity}")`,
                    run: function () {}, // it's a check
                });
            }
            if (price) {
                res.push({
                    content: `selected line has total price of ${price}`,
                    trigger: `.order .orderline.selected .product-name:contains("${name}") ~ .price:contains("${price}")`,
                    run: function () {}, // it's a check
                });
            }
            return res;
        }
        orderIsEmpty() {
            return [
                {
                    content: `order is empty`,
                    trigger: `.order .order-empty`,
                    run: () => {},
                },
            ];
        }

        productIsDisplayed(name) {
            return [
                {
                    content: `'${name}' should be displayed`,
                    trigger: `.product-list .product-name:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
    }

    class Execute {
        order(productName, quantity, price) {
            const res = this._do.clickDisplayedProduct(productName);
            if (price) {
                res.push(...this._do.pressNumpad('Price'));
                res.push(...this._do.pressNumpad(price.toString().split('').join(' ')));
                res.push(...this._do.pressNumpad('Qty'));
            }
            for (let char of quantity.toString()) {
                if ('.0123456789'.includes(char)) {
                    res.push(...this._do.pressNumpad(char));
                } else if ('-'.includes(char)) {
                    res.push(...this._do.pressNumpad('+/-'));
                }
            }
            return res;
        }
    }

    return {
        Do,
        Check,
        Execute,
        ProductScreen: createTourMethods('ProductScreen', Do, Check, Execute),
    };
});
