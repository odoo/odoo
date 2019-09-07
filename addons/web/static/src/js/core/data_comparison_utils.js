odoo.define('web.dataComparisonUtils', function (require) {
"use strict";

var fieldUtils = require('web.field_utils');
var Class = require('web.Class');

var DateClasses = Class.extend({
    /**
     * This small class offers a light API to manage equivalence classes of
     * dates. Two dates in different dateSets are declared equivalent when
     * their indexes are equal.
     *
     * @param  {Array[]} dateSets, a list of list of dates
     */
    init: function (dateSets) {
        // At least one dateSet must be non empty.
        // The completion of the first inhabited dateSet will serve as a reference set.
        // The reference set elements will be the default representatives for the classes.
        this.dateSets = dateSets;
        this.referenceIndex = null;
        for (var i = 0; i < dateSets.length; i++) {
            var dateSet = dateSets[i];
            if (dateSet.length && this.referenceIndex === null) {
                this.referenceIndex = i;
            }
        }
    },

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * Returns the index of a date in a given datesetIndex. This can be considered
     * as the date class itself.
     *
     * @param  {number} datesetIndex
     * @param  {string} date
     * @return {number}
     */
    dateClass: function (datesetIndex, date) {
        return this.dateSets[datesetIndex].indexOf(date);
    },
    /**
     * returns the dates occuring in a given class
     *
     * @param  {number} dateClass
     * @return {string[]}
     */
    dateClassMembers: function (dateClass) {
        return _.uniq(_.compact(this.dateSets.map(function (dateSet) {
            return dateSet[dateClass];
        })));
    },
    /**
     * return the representative of a date class from a date set specified by an
     * index.
     *
     * @param  {number} dateClass
     * @param  {number} [index]
     * @return {string}
     */
    representative: function (dateClass, index) {
        index = index === undefined ? this.referenceIndex : index;
        return this.dateSets[index][dateClass];
    },
});
/**
 * @param {Number} value
 * @param {Number} comparisonValue
 * @returns {Number}
 */
function computeVariation(value, comparisonValue) {
    if (isNaN(value) || isNaN(comparisonValue)) {
        return NaN;
    }
    if (comparisonValue === 0) {
        if (value === 0) {
            return 0;
        } else if (value > 0) {
            return 1;
        } else {
            return -1;
        }
    }
    return (value - comparisonValue) / Math.abs(comparisonValue);
}
/**
 * @param {Number} variation
 * @param {Object} field
 * @param {Object} options
 * @returns {Object}
 */
function renderVariation(variation, field, options) {
    var className = 'o_variation';
    var value;
    if (!isNaN(variation)) {
        if (variation > 0) {
            className += ' o_positive';
        } else if (variation < 0) {
            className += ' o_negative';
        } else {
            className += ' o_null';
        }
        value = fieldUtils.format.percentage(variation, field, options);
    } else {
        value = '-';
    }
    return $('<div>', {class: className, html: value});
}
/**
 * @param {JQuery} $node
 * @param {Number} value
 * @param {Number} comparisonValue
 * @param {Number} variation
 * @param {function} formatter
 * @param {Object} field
 * @param {Object} options
 * @returns {Object}
 */
function renderComparison($node, value, comparisonValue, variation, formatter, field, options) {
    var $variation = renderVariation(variation, field, options);
    $node.append($variation);
    if (!isNaN(variation)) {
        $node.append(
            $('<div>', {class: 'o_comparison'})
            .html(formatter(value, field, options) + ' <span>vs</span> ' + formatter(comparisonValue, field, options))
        );
    }
}

return {
    computeVariation: computeVariation,
    DateClasses: DateClasses,
    renderComparison: renderComparison,
    renderVariation: renderVariation,
};

});
