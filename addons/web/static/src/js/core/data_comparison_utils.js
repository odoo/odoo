odoo.define('web.dataComparisonUtils', function (require) {
"use strict";

var fieldUtils = require('web.field_utils');

/**
 * @param {Number} value
 * @param {Number} comparisonValue
 * @returns {Object}
 */
function computeVariation (value, comparisonValue) {
    var magnitude;
    var signClass;

    if (!isNaN(value) && !isNaN(comparisonValue)) {
        if (comparisonValue === 0) {
            if (value === 0) {
                magnitude = 0;
            } else if (value > 0){
                magnitude = 1;
            } else {
                magnitude = -1;
            }
        } else {
            magnitude = (value - comparisonValue) / Math.abs(comparisonValue);
        }
        if (magnitude > 0) {
            signClass = ' o_positive';
        } else if (magnitude < 0) {
            signClass = ' o_negative';
        } else if (magnitude === 0) {
            signClass = ' o_null';
        }
        return {magnitude: magnitude, signClass: signClass};
	} else {
		return {magnitude: NaN};
	}
}

/**
 * @param {Object} variation
 * @param {Object} field
 * @param {Object} options
 * @returns {Object}
 */
function renderVariation (variation, field, options) {
	var $variation;
    if (!isNaN(variation.magnitude)) {
		$variation = $('<div>', {class: 'o_variation' + variation.signClass}).html(
            fieldUtils.format.percentage(variation.magnitude, field, options
        ));
    } else {
        $variation = $('<div>', {class: 'o_variation'}).html('-');
    }
    return $variation;
}

/**
 * @param {JQuery} $node
 * @param {Number} value
 * @param {Number} comparisonValue
 * @param {Object} variation (with key 'magnitude' and 'signClass')
 * @param {function} formatter
 * @param {Object} field
 * @param {Object} options
 * @returns {Object}
 */
function renderComparison ($node, value, comparisonValue, variation, formatter, field, options) {
    var $variation = renderVariation(variation, field, options);
	$node.append($variation);
	if (!isNaN(variation.magnitude)) {
		$node.append(
			$('<div>', {class: 'o_comparison'})
			.html(formatter(value, field, options) + ' <span>vs</span> ' + formatter(comparisonValue, field, options))
		);
	}
}

return {
	computeVariation: computeVariation,
	renderComparison: renderComparison
};

});
