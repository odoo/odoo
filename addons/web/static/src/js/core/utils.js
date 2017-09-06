odoo.define('web.utils', function (require) {
"use strict";

/**
 * Utils
 *
 * Various generic utility functions
 */

var translation = require('web.translation');

var _t = translation._t;
var id = -1;

var utils = {
    /**
     * Throws an error if the given condition is not true
     *
     * @param {any} bool
     */
    assert: function (bool) {
        if (!bool) {
            throw new Error("AssertionError");
        }
    },
    /**
     * Confines a value inside an interval
     *
     * @param {number} [val] the value to confine
     * @param {number} [min] the minimum of the interval
     * @param {number} [max] the maximum of the interval
     * @return {number} val if val is in [min, max], min if val < min and max
     *   otherwise
     */
    confine: function (val, min, max) {
        return Math.max(min, Math.min(max, val));
    },
    /**
     * computes (Math.floor(a/b), a%b and passes that to the callback.
     *
     * returns the callback's result
     */
    divmod: function (a, b, fn) {
        var mod = a%b;
        // in python, sign(a % b) === sign(b). Not in JS. If wrong side, add a
        // round of b
        if (mod > 0 && b < 0 || mod < 0 && b > 0) {
            mod += b;
        }
        return fn(Math.floor(a/b), mod);
    },
    /**
     * @param {number} value
     * @param {integer} decimals
     * @returns {boolean}
     */
    float_is_zero: function (value, decimals) {
        var epsilon = Math.pow(10, -decimals);
        return Math.abs(utils.round_precision(value, epsilon)) < epsilon;
    },
    /**
     * Generate a unique numerical ID
     *
     * @returns {integer}
     */
    generateID: function () {
        return ++id;
    },
    /**
     * Read the cookie described by c_name
     *
     * @param {string} c_name
     * @returns {string}
     */
    get_cookie: function (c_name) {
        var cookies = document.cookie ? document.cookie.split('; ') : [];
        for (var i = 0, l = cookies.length; i < l; i++) {
            var parts = cookies[i].split('=');
            var name = parts.shift();
            var cookie = parts.join('=');

            if (c_name && c_name === name) {
                return cookie;
            }
        }
        return "";
    },
    /**
     * Returns a human readable number
     *
     * @param {Number} number
     */
    human_number: function (number, decimals) {
        decimals = decimals | 0;
        number = Math.round(number);
        var d2 = Math.pow(10, decimals);
        var val = _t("kMGTPE");
        var i = val.length-1, s;
        while( i ) {
            s = Math.pow(10,i--*3);
            if( s <= number ) {
                number = Math.round(number*d2/s)/d2 + val[i];
            }
        }
        return number;
    },
    /**
     * Returns a human readable size
     *
     * @param {Number} number of bytes
     */
    human_size: function (size) {
        var units = _t("Bytes,Kb,Mb,Gb,Tb,Pb,Eb,Zb,Yb").split(',');
        var i = 0;
        while (size >= 1024) {
            size /= 1024;
            ++i;
        }
        return size.toFixed(2) + ' ' + units[i];
    },
    /**
     * Insert "thousands" separators in the provided number (which is actually
     * a string)
     *
     * @param {String} num
     * @returns {String}
     */
    insert_thousand_seps: function (num) {
        var negative = num[0] === '-';
        num = (negative ? num.slice(1) : num);
        return (negative ? '-' : '') + utils.intersperse(
            num, _t.database.parameters.grouping, _t.database.parameters.thousands_sep);
    },
    /**
     * Intersperses ``separator`` in ``str`` at the positions indicated by
     * ``indices``.
     *
     * ``indices`` is an array of relative offsets (from the previous insertion
     * position, starting from the end of the string) at which to insert
     * ``separator``.
     *
     * There are two special values:
     *
     * ``-1``
     *   indicates the insertion should end now
     * ``0``
     *   indicates that the previous section pattern should be repeated (until all
     *   of ``str`` is consumed)
     *
     * @param {String} str
     * @param {Array<Number>} indices
     * @param {String} separator
     * @returns {String}
     */
    intersperse: function (str, indices, separator) {
        separator = separator || '';
        var result = [], last = str.length;

        for(var i=0; i<indices.length; ++i) {
            var section = indices[i];
            if (section === -1 || last <= 0) {
                // Done with string, or -1 (stops formatting string)
                break;
            } else if(section === 0 && i === 0) {
                // repeats previous section, which there is none => stop
                break;
            } else if (section === 0) {
                // repeat previous section forever
                //noinspection AssignmentToForLoopParameterJS
                section = indices[--i];
            }
            result.push(str.substring(last-section, last));
            last -= section;
        }

        var s = str.substring(0, last);
        if (s) { result.push(s); }
        return result.reverse().join(separator);
    },
    /**
     * @param {any} object
     * @param {any} path
     * @returns
     */
    into: function (object, path) {
        if (!_(path).isArray()) {
            path = path.split('.');
        }
        for (var i = 0; i < path.length; i++) {
            object = object[path[i]];
        }
        return object;
    },
    /**
     * @param {string} v
     * @returns {boolean}
     */
    is_bin_size: function (v) {
        return (/^\d+(\.\d*)? \w+$/).test(v);
    },
    /**
     * @param {any} node
     * @param {any} human_readable
     * @param {any} indent
     * @returns {string}
     */
    json_node_to_xml: function (node, human_readable, indent) {
        // For debugging purpose, this function will convert a json node back to xml
        indent = indent || 0;
        var sindent = (human_readable ? (new Array(indent + 1).join('\t')) : ''),
            r = sindent + '<' + node.tag,
            cr = human_readable ? '\n' : '';

        if (typeof(node) === 'string') {
            return sindent + node.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        } else if (typeof(node.tag) !== 'string' || !node.children instanceof Array || !node.attrs instanceof Object) {
            throw new Error(
                _.str.sprintf(_t("Node [%s] is not a JSONified XML node"),
                            JSON.stringify(node)));
        }
        for (var attr in node.attrs) {
            var vattr = node.attrs[attr];
            if (typeof(vattr) !== 'string') {
                // domains, ...
                vattr = JSON.stringify(vattr);
            }
            vattr = vattr.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
            if (human_readable) {
                vattr = vattr.replace(/&quot;/g, "'");
            }
            r += ' ' + attr + '="' + vattr + '"';
        }
        if (node.children && node.children.length) {
            r += '>' + cr;
            var childs = [];
            for (var i = 0, ii = node.children.length; i < ii; i++) {
                childs.push(utils.json_node_to_xml(node.children[i], human_readable, indent + 1));
            }
            r += childs.join(cr);
            r += cr + sindent + '</' + node.tag + '>';
            return r;
        } else {
            return r + '/>';
        }
    },
    /**
     * Left-pad provided arg 1 with zeroes until reaching size provided by second
     * argument.
     *
     * @see rpad
     *
     * @param {number|string} str value to pad
     * @param {number} size size to reach on the final padded value
     * @returns {string} padded string
     */
    lpad: function (str, size) {
        str = "" + str;
        return new Array(size - str.length + 1).join('0') + str;
    },
    /**
     * Passes the fractional and integer parts of x to the callback, returns
     * the callback's result
     */
    modf: function (x, fn) {
        var mod = x%1;
        if (mod < 0) {
            mod += 1;
        }
        return fn(mod, Math.floor(x));
    },
    /**
     * performs a half up rounding with a fixed amount of decimals, correcting for float loss of precision
     * See the corresponding float_round() in server/tools/float_utils.py for more info
     * @param {Number} the value to be rounded
     * @param {Number} the number of decimals. eg: round_decimals(3.141592,2) -> 3.14
     */
    round_decimals: function (value, decimals) {
        return utils.round_precision(value, Math.pow(10,-decimals));
    },
    /**
     * performs a half up rounding with arbitrary precision, correcting for float loss of precision
     * See the corresponding float_round() in server/tools/float_utils.py for more info
     *
     * @param {number} value the value to be rounded
     * @param {number} precision a precision parameter. eg: 0.01 rounds to two digits.
     */
    round_precision: function (value, precision) {
        if (!value) {
            return 0;
        } else if (!precision || precision < 0) {
            precision = 1;
        }
        var normalized_value = value / precision;
        var epsilon_magnitude = Math.log(Math.abs(normalized_value))/Math.log(2);
        var epsilon = Math.pow(2, epsilon_magnitude - 53);
        normalized_value += normalized_value >= 0 ? epsilon : -epsilon;

        /**
         * Javascript performs strictly the round half up method, which is asymmetric. However, in
         * Python, the method is symmetric. For example:
         * - In JS, Math.round(-0.5) is equal to -0.
         * - In Python, round(-0.5) is equal to -1.
         * We want to keep the Python behavior for consistency.
         */
        var sign = normalized_value < 0 ? -1.0 : 1.0;
        var rounded_value = sign * Math.round(Math.abs(normalized_value));
        return rounded_value * precision;
    },
    /**
     * @see lpad
     *
     * @param {string} str
     * @param {number} size
     * @returns {string}
     */
    rpad: function (str, size) {
        str = "" + str;
        return str + new Array(size - str.length + 1).join('0');
    },
    /**
     * Create a cookie
     * @param {String} name : the name of the cookie
     * @param {String} value : the value stored in the cookie
     * @param {Integer} ttl : time to live of the cookie in millis. -1 to erase the cookie.
     */
    set_cookie: function (name, value, ttl) {
        ttl = ttl || 24*60*60*365;
        document.cookie = [
            name + '=' + value,
            'path=/',
            'max-age=' + ttl,
            'expires=' + new Date(new Date().getTime() + ttl*1000).toGMTString()
        ].join(';');
    },
    /**
     * @param {any} array
     * @param {any} elem1
     * @param {any} elem2
     */
    swap: function (array, elem1, elem2) {
        var i1 = array.indexOf(elem1);
        var i2 = array.indexOf(elem2);
        array[i2] = elem1;
        array[i1] = elem2;
    },
    /**
     * @param {any} str
     * @param {any} elseValues
     * @param {any} trueValues
     * @param {any} falseValues
     * @returns
     */
    toBoolElse: function (str, elseValues, trueValues, falseValues) {
        var ret = _.str.toBool(str, trueValues, falseValues);
        if (_.isUndefined(ret)) {
            return elseValues;
        }
        return ret;
    },
    /**
     * @todo: is this really the correct place?
     *
     * @param {any} data
     * @param {any} f
     */
    traverse_records: function (data, f) {
        if (data.type === 'record') {
            f(data);
        } else if (data.data) {
            for (var i = 0; i < data.data.length; i++) {
                utils.traverse_records(data.data[i], f);
            }
        }
    },
    /**
     * @param {any} node
     * @param {any} strip_whitespace
     * @returns
     */
    xml_to_json: function (node, strip_whitespace) {
        switch (node.nodeType) {
            case 9:
                return utils.xml_to_json(node.documentElement, strip_whitespace);
            case 3:
            case 4:
                return (strip_whitespace && node.data.trim() === '') ? undefined : node.data;
            case 1:
                var attrs = $(node).getAttributes();
                _.each(['domain', 'filter_domain', 'context', 'default_get'], function (key) {
                    if (attrs[key]) {
                        try {
                            attrs[key] = JSON.parse(attrs[key]);
                        } catch(e) { }
                    }
                });
                return {
                    tag: node.tagName.toLowerCase(),
                    attrs: attrs,
                    children: _.compact(_.map(node.childNodes, function (node) {
                        return utils.xml_to_json(node, strip_whitespace);
                    })),
                };
        }
    },
    /**
     * @param {any} node
     * @returns {string}
     */
    xml_to_str: function (node) {
        var str = "";
        if (window.XMLSerializer) {
            str = (new XMLSerializer()).serializeToString(node);
        } else if (window.ActiveXObject) {
            str = node.xml;
        } else {
            throw new Error(_t("Could not serialize XML"));
        }
        // Browsers won't deal with self closing tags except void elements:
        // http://www.w3.org/TR/html-markup/syntax.html
        var void_elements = 'area base br col command embed hr img input keygen link meta param source track wbr'.split(' ');

        // The following regex is a bit naive but it's ok for the xmlserializer output
        str = str.replace(/<([a-z]+)([^<>]*)\s*\/\s*>/g, function (match, tag, attrs) {
            if (void_elements.indexOf(tag) < 0) {
                return "<" + tag + attrs + "></" + tag + ">";
            } else {
                return match;
            }
        });
        return str;
    },
    /**
     * Visit a tree of objects, where each children are in an attribute 'children'.
     * For each children, we call the callback function given in arguments.
     *
     * @param {Object} tree an object describing a tree structure
     * @param {function} f a callback
     */
    traverse: function (tree, f) {
        if (f(tree)) {
            _.each(tree.children, function (c) { utils.traverse(c, f); });
        }
    },
    /**
     * Visit a tree of objects and freeze all
     *
     * @param {Object} obj
     */
    deepFreeze: function (obj) {
      var propNames = Object.getOwnPropertyNames(obj);
      propNames.forEach(function(name) {
        var prop = obj[name];
        if (typeof prop == 'object' && prop !== null)
          utils.deepFreeze(prop);
      });
      return Object.freeze(obj);
    },

};

return utils;

});
