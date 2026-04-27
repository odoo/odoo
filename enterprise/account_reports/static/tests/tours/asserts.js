/** @odoo-module **/

//----------------------------------------------------------------------------------------------------------------------
// This class provides some helpers function to do assertions on tours
//----------------------------------------------------------------------------------------------------------------------
export class Asserts {
    //------------------------------------------------------------------------------------------------------------------
    // Helpers
    //------------------------------------------------------------------------------------------------------------------
    // Gets the number of 'selector' element inside 'target' element
    static getCount(target, selector) {
        return document.querySelector(target).querySelectorAll(selector).length;
    }
    // Gets the number of 'selector' element inside DOM
    static getDOMCount(selector) {
        return document.querySelectorAll(selector).length;
    }
    static check(condition, success, error) {
        condition ? Asserts.success(success) : Asserts.error(error);
    }
    static success(message) {
        return console.info(`SUCCESS: ${message}`);
    }
    static error(message) {
        throw new Error(`FAIL: ${message}`);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Asserts
    //------------------------------------------------------------------------------------------------------------------
    static isTrue(actual) {
        Asserts.check(actual, `${actual} is true`, `${actual} is not true`);
    }
    static isFalse(actual) {
        Asserts.check(!actual, `${actual} is false`, `${actual} is not false`);
    }
    // Assert that 'actual' and 'expected' are equal
    static isEqual(actual, expected) {
        Asserts.check(
            (actual == expected),
            `${actual} is equal to expected ${expected}`,
            `${actual} is not equal to expected ${expected}`
        );
    }
    // Asserts that 'actual' and 'expected' are strictly equal
    static isStrictEqual(actual, expected) {
        Asserts.check(
            (actual === expected),
            `${actual} is strictly equal to expected ${expected}`,
            `${actual} is not strictly equal to expected ${expected}`
        );
    }
    // Assert that 'target' element contains at least one 'selector' element
    static contains(target, selector) {
        const count = Asserts.getCount(target, selector);
        Asserts.check(
            (count > 0),
            `There is at least one ${selector} in ${target}`,
            `There should be at least one ${selector} in ${target} but there is ${count}`
        );
    }
    // Asserts there is no 'selector' element in 'target' element
    static containsNone(target, selector) {
        const count = Asserts.getCount(target, selector);
        Asserts.check(
            (count === 0),
            `There is no ${selector} in ${target}`,
            `There should be no ${selector} in ${target} but there is ${count}`
        );
    }
    // Asserts that 'target' element contains 'number' of 'selector' elements
    static containsNumber(target, selector, number) {
        const count = Asserts.getCount(target, selector);
        Asserts.check(
            (count === number),
            `There is the correct number (${number}) of ${selector} in ${target}`,
            `There should be at ${number} ${selector} in ${target} but there is ${count}`
        );
    }
    // Asserts that DOM contains at least one 'selector' element
    static DOMContains(selector) {
        const count = Asserts.getDOMCount(selector);
        Asserts.check(
            (count > 0),
            `There is at least one ${selector} in the DOM`,
            `There should be at least one ${selector} in the DOM but there is ${count}`
        );
    }
    // Asserts there is no 'selector' element in the DOM
    static DOMContainsNone(selector) {
        const count = Asserts.getDOMCount(selector);
        Asserts.check(
            (count === 0),
            `There is no ${selector} in the DOM`,
            `There should be 0 ${selector} in the DOM but there is ${count}`
        );
    }
    // Asserts that DOM contains 'number' of 'selector' element
    static DOMContainsNumber(selector, number) {
        const count = Asserts.getDOMCount(selector);
        Asserts.check(
            (Asserts.getDOMCount(selector) === number),
            `There is the correct number (${number}) of ${selector} in the DOM`,
            `There should be ${number} ${selector} in the DOM but there is ${count}`
        );
    }
    // Asserts that 'selector' element has class 'classname'
    static hasClass(selector, classname) {
        Asserts.check(
            document.querySelector(selector).classList.contains(classname),
            `${selector} has class ${classname}`,
            `${selector} should have class ${classname} but hasn't`
        );
    }
}
