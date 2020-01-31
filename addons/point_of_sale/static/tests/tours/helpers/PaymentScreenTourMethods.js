odoo.define('point_of_sale.tour.PaymentScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickPaymentMethod(name) {
            return [
                {
                    content: `click '${name}' payment method`,
                    trigger: `.paymentmethods .button.paymentmethod:contains("${name}")`,
                },
            ];
        }

        /**
         * Delete the paymentline having the given payment method name and amount.
         * @param {String} name payment method
         * @param {String} amount
         */
        clickPaymentlineDelButton(name, amount) {
            return [
                {
                    content: `delete ${name} paymentline with ${amount} amount`,
                    trigger: `.paymentlines .paymentline .payment-name:contains("${name}") ~ .delete-button`,
                },
            ];
        }

        clickEmailButton() {
            return [
                {
                    content: `click email button`,
                    trigger: `.payment-buttons .js_email`,
                },
            ];
        }

        clickValidate() {
            return [
                {
                    content: 'validate payment',
                    trigger: `.payment-screen .button.next.highlight`,
                },
            ];
        }

        /**
         * Press the numpad in sequence based on the given space-separated keys.
         * @param {String} keys space-separated numpad keys
         */
        pressNumpad(keys) {
            const numberChars = '. +/- 0 1 2 3 4 5 6 7 8 9'.split(' ');
            const modeButtons = '+10 +20 +50'.split(' ');
            function generateStep(key) {
                let trigger;
                if (numberChars.includes(key)) {
                    trigger = `.payment-numpad .number-char:contains("${key}")`;
                } else if (modeButtons.includes(key)) {
                    trigger = `.payment-numpad .mode-button:contains("${key}")`;
                } else if (key === 'Backspace') {
                    trigger = `.payment-numpad .number-char img[alt="Backspace"]`;
                }
                return {
                    content: `'${key}' pressed in payment numpad`,
                    trigger,
                };
            }
            return keys.split(' ').map(generateStep);
        }

        clickBack() {
            return [
                {
                    content: 'click back button',
                    trigger: '.payment-screen .button.back',
                },
            ];
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'payment screen is shown',
                    trigger: '.pos .payment-screen',
                    run: () => {},
                },
            ];
        }
        /**
         * Check if change is the provided amount.
         * @param {String} amount
         */
        changeIs(amount) {
            return [
                {
                    content: `change is ${amount}`,
                    trigger: `.payment-status-change .amount:contains("${amount}")`,
                    run: () => {},
                },
            ];
        }

        /**
         * Check if the remaining is the provided amount.
         * @param {String} amount
         */
        remainingIs(amount) {
            return [
                {
                    content: `remaining amount is ${amount}`,
                    trigger: `.payment-status-remaining .amount:contains("${amount}")`,
                    run: () => {},
                },
            ];
        }

        emailButtonIsHighligted(isHighlighted) {
            return [
                {
                    content: `check email button`,
                    trigger: isHighlighted
                        ? `.payment-buttons .js_email.highlight`
                        : `.payment-buttons .js_email:not(:has(.highlight))`,
                    run: () => {},
                },
            ];
        }

        /**
         * Check if validate button is highlighted.
         * @param {Boolean} isHighlighted
         */
        validateButtonIsHighlighted(isHighlighted = true) {
            return [
                {
                    content: `validate button is ${
                        isHighlighted ? 'highlighted' : 'not highligted'
                    }`,
                    trigger: isHighlighted
                        ? `.payment-screen .button.next.highlight`
                        : `.payment-screen .button.next:not(:has(.highlight))`,
                    run: () => {},
                },
            ];
        }

        /**
         * Check if the paymentlines are empty. Also provide the amount to pay.
         * @param {String} amountToPay
         */
        emptyPaymentlines(amountToPay) {
            return [
                {
                    content: `there are no paymentlines`,
                    trigger: `.paymentlines-empty`,
                    run: () => {},
                },
                {
                    content: `amount to pay is '${amountToPay}'`,
                    trigger: `.paymentlines-empty .total:contains("${amountToPay}")`,
                    run: () => {},
                },
            ];
        }

        /**
         * Check if the selected paymentline has the given payment method and amount.
         * @param {String} paymentMethodName
         * @param {String} amount
         */
        selectedPaymentlineHas(paymentMethodName, amount) {
            return [
                {
                    content: `line paid via '${paymentMethodName}' is selected`,
                    trigger: `.paymentlines .paymentline.selected .payment-name:contains("${paymentMethodName}")`,
                    run: () => {},
                },
                {
                    content: `amount tendered in the line is '${amount}'`,
                    trigger: `.paymentlines .paymentline.selected .payment-amount:contains("${amount}")`,
                    run: () => {},
                },
            ];
        }
    }

    return {
        Do,
        Check,
        PaymentScreen: createTourMethods('PaymentScreen', Do, Check),
    };
});
