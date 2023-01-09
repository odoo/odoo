/**
 * This code has been more that widely inspired by the multirange library
 * which can be found on https://github.com/LeaVerou/multirange.
 *
 * The license file can be found in the same folder as this file.
 */

odoo.define('website_sale.multirange', function () {
'use strict';

/**
 * The multirange library will display the two values as one range input with
 * two cursors linked by a background. This is to be used with Bootstrap
 * custom-range inputs.
 *
 * There is 2 number inputs on the right and left of the multirange to
 * display and allow quick and precise value modifications. They are
 * initialized with the same value provided to the input (min, max, step).
 *
 * There is 2 events that are added to the input:
 * - oldRangeValue: Triggered when the user clicks on a cursor or on focus
 *                  of the right or left number input.
 * - newRangeValue: Triggered when the user release a cursor or on focus
 *                  out of the right or left number input.
 *
 * The options available for the multirange are :
 * - On range input or as multirange method options:
 *     - min: minimal value of the range. Default: 0.
 *     - max: maximal value of the range. Default: 100.
 *     - step: precision of the range. Default: 1.
 *     - currency: symbol preceding the displayed values. Default: Empty.
 *     - currencyPosition: currency before/after value. Default: "after".
 *     - value: the current value of the range. Default: "0,100".
 *
 * - As multirange method options only:
 *     - displayCounterInput: if we display the value. Default: true.
 *
 * Initialization of a multiple range input can be done in two ways:
 *
 * Having the inputs with the options as properties and the multiple
 * property set will let the library initialize it just after DOM loaded.
 *
 * <input type="range" multiple="multiple" class="custom-range
 * range-with-input" min=2 max=10 step=0.5 data-currency="€"
 * data-currency-position="before" value="4,8"/>
 *
 * Providing a HTMLElement and an Object with the desired options.
 *
 * <input id="multi" type="range" class="custom-range"/>
 *
 * multirange(document.querySelector('#multi'), {
 *     min: 2,
 *     max: 10,
 *     step: 0.5,
 *     currency: "€",
 *     currencyPosition: "before",
 *     value: "4,8"
 *     rangeWithInput: true,
 * });
 */

const HTMLInputElement = window.HTMLInputElement;
const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");

class Multirange {
    constructor(input, options = {}) {
        const self = this;

        /* Set default and optionnal values */
        this.input = input;
        this.rangeWithInput = options.rangeWithInput === true || this.input.classList.contains('range-with-input');
        const value = options.value || this.input.getAttribute("value");
        const values = value === null ? [] : value.split(",");
        this.input.min = this.min = options.min || this.input.min || 0;
        this.input.max = this.max = options.max || this.input.max || 100;
        this.input.step = this.step = options.step || this.input.step || 1;
        this.currency = options.currency || this.input.dataset.currency || '';
        this.currencyPosition = options.currencyPosition || this.input.dataset.currencyPosition || 'after';
        const inputClasses = ["multirange", "d-inline-block", "p-0", "align-top"];

        /* Wrap the input and add its ghost */
        this.rangeDiv = document.createElement("div");
        this.rangeDiv.classList.add("multirange-wrapper", "position-relative", "mb-5");
        this.countersWrapper = document.createElement("small");
        this.countersWrapper.classList.add("d-flex", "justify-content-between", "mt-2");
        this.rangeDiv.appendChild(this.countersWrapper);
        this.input.parentNode.insertBefore(this.rangeDiv, this.input.nextSibling);
        this.rangeDiv.appendChild(this.input);
        this.ghost = this.input.cloneNode();
        this.rangeDiv.appendChild(this.ghost);

        this.input.classList.add("original", "position-absolute", "w-100", "m-0", ...inputClasses);
        this.ghost.classList.add("ghost", "position-relative", ...inputClasses);
        this.input.value = values[0] || this.min;
        this.ghost.value = values[1] || this.max;

        this.leftCounter = document.createElement("span");
        this.leftCounter.classList.add("multirange-min", "position-absolute", "opacity-75", "opacity-100-hover", "mt-1");
        this.rightCounter = document.createElement("span");
        this.rightCounter.classList.add("multirange-max", "position-absolute", "opacity-75", "opacity-100-hover", "mt-1");
        this.rightCounter.style.right = 0;
        this.countersWrapper.append(this.leftCounter, this.rightCounter);

        /* Add the counterInput */
        if (this.rangeWithInput) {
            this.leftInput = document.createElement("input");
            this.leftInput.type = "number";
            this.leftInput.classList.add("invisible", "form-control", "form-control-sm", "mb-2", "mb-lg-1");
            this.leftInput.min = this.min;
            this.leftInput.max = this.max;
            this.leftInput.step = this.step;
            this.rightInput = this.leftInput.cloneNode();

            this.leftInput.classList.add("multirange-min", "invisible");
            this.rightInput.classList.add("multirange-max", "invisible");

            this.leftCounter.parentNode.appendChild(this.leftInput);
            this.rightCounter.parentNode.appendChild(this.rightInput);
        }

        /* Define new properties on range input to link it with ghost, especially for Safari compatibility*/
        Object.defineProperty(this.input, "originalValue", descriptor.get ? descriptor : {
            get: function () {
                return this.value;
            },
            set: function (v) {
                this.value = v;
            }
        });

        Object.defineProperties(this.input, {
            valueLow: {
                get: function () {
                    return Math.min(this.originalValue, self.ghost.value);
                },
                set: function (v) {
                    this.originalValue = v;
                },
                enumerable: true
            },
            valueHigh: {
                get: function () {
                    return Math.max(this.originalValue, self.ghost.value);
                },
                set: function (v) {
                    self.ghost.value = v;
                },
                enumerable: true
            }
        });

        if (descriptor.get) {
            Object.defineProperty(this.input, "value", {
                get: function () {
                    return this.valueLow + "," + this.valueHigh;
                },
                set: function (v) {
                    const values = v.split(",");
                    this.valueLow = values[0];
                    this.valueHigh = values[1];
                    this.update();
                },
                enumerable: true
            });
        }

        if (typeof this.input.oninput === "function") {
            this.ghost.oninput = this.input.oninput.bind(this.input);
        }

        this.input.addEventListener("input", this.update.bind(this));
        this.ghost.addEventListener("input", this.update.bind(this));

        this.input.addEventListener("touchstart", this.saveOldValues.bind(this));
        this.ghost.addEventListener("touchstart", this.saveOldValues.bind(this));
        this.input.addEventListener("mousedown", this.saveOldValues.bind(this));
        this.ghost.addEventListener("mousedown", this.saveOldValues.bind(this));

        this.input.addEventListener("touchend", this.dispatchNewValueEvent.bind(this));
        this.ghost.addEventListener("touchend", this.dispatchNewValueEvent.bind(this));
        this.input.addEventListener("mouseup", this.dispatchNewValueEvent.bind(this));
        this.ghost.addEventListener("mouseup", this.dispatchNewValueEvent.bind(this));

        if (this.rangeWithInput) {
            this.leftCounter.addEventListener("click", this.counterInputSwitch.bind(this));
            this.rightCounter.addEventListener("click", this.counterInputSwitch.bind(this));

            this.leftInput.addEventListener("blur", this.counterInputSwitch.bind(this));
            this.rightInput.addEventListener("blur", this.counterInputSwitch.bind(this));

            this.leftInput.addEventListener("keypress", this.elementBlurOnEnter.bind(this));
            this.rightInput.addEventListener("keypress", this.elementBlurOnEnter.bind(this));

            this.leftInput.addEventListener("focus", this.selectAllFocus.bind(this));
            this.rightInput.addEventListener("focus", this.selectAllFocus.bind(this));
        }
        this.update();
        $(this.rangeDiv).addClass('visible');

    }

    update() {
        const low = 100 * (this.input.valueLow - this.min) / (this.max - this.min);
        const high = 100 * (this.input.valueHigh - this.min) / (this.max - this.min);

        this.rangeDiv.style.setProperty("--low", low + '%');
        this.rangeDiv.style.setProperty("--high", high + '%');
        this.counterInputUpdate();
    }

    counterInputUpdate() {
        if (this.rangeWithInput) {
            this.leftCounter.innerText = this.formatNumber(this.input.valueLow);
            this.rightCounter.innerText = this.formatNumber(this.input.valueHigh);
            this.leftInput.value = this.input.valueLow;
            this.rightInput.value = this.input.valueHigh;
        }
    }

    counterInputSwitch(ev) {
        let counter = this.rightCounter;
        let input = this.rightInput;
        if (ev.currentTarget.classList.contains('multirange-min')) {
            counter = this.leftCounter;
            input = this.leftInput;
        }

        if (counter.classList.contains("invisible")) {
            this.input.valueLow = this.leftInput.value;
            this.input.valueHigh = this.rightInput.value;
            this.dispatchNewValueEvent();
            this.update();
            counter.classList.remove("invisible");
            input.classList.add("invisible");
        } else {
            counter.classList.add("invisible");
            input.classList.remove("invisible");
            this.saveOldValues();
            // Hack because firefox: https://bugzilla.mozilla.org/show_bug.cgi?id=1057858
            window.setTimeout(function () {
                input.focus();
            }, 1);
        }
    }

    elementBlurOnEnter(ev) {
        if (ev.key === "Enter") {
            ev.currentTarget.blur();
        }
    }

    selectAllFocus(ev) {
        ev.currentTarget.select();
    }

    dispatchNewValueEvent() {
        if (this._previousMaxPrice !== this.input.valueHigh || this._previousMinPrice !== this.input.valueLow) {
            this.input.dispatchEvent(new CustomEvent("newRangeValue", {
                bubbles: true,
            }));
        }
    }

    saveOldValues() {
        this._previousMinPrice = this.input.valueLow;
        this._previousMaxPrice = this.input.valueHigh;
    }

    formatNumber(number) {
        number = String(number).split('.');
        if (number[1] && number[1].length === 1) {
            number[1] += '0';
        }
        let formatedNumber = number[0].replace(/(?=(?:\d{3})+$)(?!\b)/g, ',') + (number[1] ? '.' + number[1] : '.00');
        if (this.currency.length) {
            if (this.currencyPosition === 'after') {
                formatedNumber = formatedNumber + ' ' + this.currency;
            } else {
                formatedNumber = this.currency + ' ' + formatedNumber;
            }
        }
        return formatedNumber;
    }
}

function multirange(input, options) {
    if (input.classList.contains('multirange')) {
        return;
    }
    new Multirange(input, options);
}

return {
    Multirange: Multirange,
    init: multirange,
};
});

odoo.define('website_sale.multirange.instance', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const multirange = require('website_sale.multirange');

publicWidget.registry.WebsiteMultirangeInputs = publicWidget.Widget.extend({
    selector: 'input[type=range][multiple]:not(.multirange)',

    /**
     * @override
     */
    start() {
        return this._super.apply(this, arguments).then(() => {
            multirange.init(this.el);
        });
    },
});
});
