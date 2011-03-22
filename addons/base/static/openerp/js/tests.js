/**
 * @function
 * Defines a module scope (which lasts until the next call to module).
 *
 * This module scopes implies setup and teardown callbacks running for each test.
 *
 * @param {String} name the name of the module
 * @param {Object} [lifecycle] callbacks to run before and after each test of the module
 * @param {Function} lifecycle.setup function running before each test of this module
 * @param {Function} lifecycle.teardown function running after each test of this module
 */
var module;
/**
 * @function
 * Defines a given test to run. Runs all the assertions present in the test
 *
 * @param {String} name the name of the test
 * @param {Number} [expected] number of assertions expected to run in this test (useful for asynchronous tests)
 * @param {Function} test the testing code to run, holding a sequence of assertions (at least one)
 */
var test;
/**
 * @function
 * The most basic boolean assertion (~assertTrue or assert).
 *
 * Passes if its argument is truthy
 *
 * @param {Boolean} state an arbitrary expression, evaluated in a boolean context
 * @param {String} [message] the message to output with the assertion result
 */
var ok;
/**
 * @function
 * Equality assertion (~assertEqual)
 *
 * Passes if both arguments are equal (via <code>==</code>)
 *
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var equal;
/**
 * @function
 * Inequality assertion (~assertEqual)
 *
 * Passes if the arguments are different (via <code>!=</code>)
 *
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var notEqual, deepEqual, notDeepEqual,
    strictEqual, notStrictEqual, raises, start, stop;
$(document).ready(function () {
});
