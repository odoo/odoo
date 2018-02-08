odoo.define('web.jquery.extensions', function () {
'use strict';

/**
 * The jquery library extensions and fixes should be done here to avoid patching
 * in place.
 */

// jQuery selectors extensions
$.extend($.expr[':'], {
    containsLike: function (element, index, matches){
        return element.innerHTML.toUpperCase().indexOf(matches[3].toUpperCase()) >= 0;
    },
    containsExact: function (element, index, matches){
        return $.trim(element.innerHTML) === matches[3];
    },
    /**
     * Note all escaped characters need to be double escaped inside of the
     * expression, so "\(" needs to be "\\("
     */
    containsRegex: function (element, index, matches){
        var regreg =  /^\/((?:\\\/|[^\/])+)\/([mig]{0,3})$/,
        reg = regreg.exec(matches[3]);
        return reg ? new RegExp(reg[1], reg[2]).test($.trim(element.innerHTML)) : false;
    },
    propChecked: function (element, index, matches) {
        return $(element).prop("checked") === true;
    },
    propSelected: function (element, index, matches) {
        return $(element).prop("selected") === true;
    },
    propValue: function (element, index, matches) {
        return $(element).prop("value") === matches[3];
    },
    propValueContains: function (element, index, matches) {
        return $(element).prop("value") && $(element).prop("value").indexOf(matches[3]) !== -1;
    },
    hasData: function (element) {
        return !!_.toArray(element.dataset).length;
    },
    data: function (element, index, matches) {
        return $(element).data(matches[3]);
    },
    hasVisibility: function (element, index, matches) {
        var $element = $(element);
        if ($(element).css('visibility') === 'hidden') {
            return false;
        }
        var $parent = $element.parent();
        if (!$parent.length || $element.is('html')) {
            return true;
        }
        return $parent.is(':hasVisibility');
    },
    hasOpacity: function (element, index, matches) {
        var $element = $(element);
        if (parseFloat($(element).css('opacity')) <= 0.01) {
            return false;
        }
        var $parent = $element.parent();
        if (!$parent.length || $element.is('html')) {
            return true;
        }
        return $parent.is(':hasOpacity');
    },
});

// jQuery functions extensions
$.fn.extend({
    /**
     * Returns all the attributes of a DOM element (first one in the jQuery
     * set).
     *
     * @returns {Object} attribute name -> attribute value
     */
    getAttributes: function () {
        var o = {};
        if (this.length) {
            var attrs = this[0].attributes;
            for (var i = 0, l = attrs.length ; i < l ; i++) {
                var attr = attrs.item(i);
                o[attr.name] = attr.value;
            }
        }
        return o;
    },
    /**
     * Makes DOM elements bounce the way Odoo decided it.
     */
    odooBounce: function () {
        return this.each(function () {
            $(this).css('box-sizing', 'content-box')
                   .effect('bounce', {distance: 18, times: 5}, 250);
        });
    },
    /**
     * Allows to bind events to a handler just as the standard `$.on` function
     * but binds the handler so that it is executed before any already-attached
     * handler for the same events.
     *
     * @see jQuery.on
     */
    prependEvent: function (events, selector, data, handler) {
        this.on.apply(this, arguments);

        events = events.split(' ');
        return this.each(function () {
            var el = this;
            _.each(events, function (evNameNamespaced) {
                var evName = evNameNamespaced.split('.')[0];
                var handler = $._data(el, 'events')[evName].pop();
                $._data(el, 'events')[evName].unshift(handler);
            });
        });
    },
});
});
