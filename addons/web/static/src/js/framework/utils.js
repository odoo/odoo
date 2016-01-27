odoo.define('web.utils', function (require) {
"use strict";

var Class = require('web.Class');
var translation = require('web.translation');

var _t = translation._t;

/**
 * computes (Math.floor(a/b), a%b and passes that to the callback.
 *
 * returns the callback's result
 */
function divmod (a, b, fn) {
    var mod = a%b;
    // in python, sign(a % b) === sign(b). Not in JS. If wrong side, add a
    // round of b
    if (mod > 0 && b < 0 || mod < 0 && b > 0) {
        mod += b;
    }
    return fn(Math.floor(a/b), mod);
}

/**
 * Passes the fractional and integer parts of x to the callback, returns
 * the callback's result
 */
function modf (x, fn) {
    var mod = x%1;
    if (mod < 0) {
        mod += 1;
    }
    return fn(mod, Math.floor(x));
}

/*
 * Left-pad provided arg 1 with zeroes until reaching size provided by second
 * argument.
 *
 * @param {Number|String} str value to pad
 * @param {Number} size size to reach on the final padded value
 * @returns {String} padded string
 */
function lpad (str, size) {
    str = "" + str;
    return new Array(size - str.length + 1).join('0') + str;
}

function rpad (str, size) {
    str = "" + str;
    return str + new Array(size - str.length + 1).join('0');
}

var id = -1;

function generate_id () {
    return ++id;
}

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
function intersperse (str, indices, separator) {
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
}

function xml_to_json (node, strip_whitespace) {
    switch (node.nodeType) {
        case 9:
            return xml_to_json(node.documentElement, strip_whitespace);
        case 3:
        case 4:
            return (strip_whitespace && node.data.trim() === '') ? undefined : node.data;
        case 1:
            var attrs = $(node).getAttributes();
            _.each(['domain', 'filter_domain', 'context', 'default_get'], function(key) {
                if (attrs[key]) {
                    try {
                        attrs[key] = JSON.parse(attrs[key]);
                    } catch(e) { }
                }
            });
            return {
                tag: node.tagName.toLowerCase(),
                attrs: attrs,
                children: _.compact(_.map(node.childNodes, function(node) {
                    return xml_to_json(node, strip_whitespace);
                })),
            };
    }
}

function json_node_to_xml (node, human_readable, indent) {
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
            childs.push(json_node_to_xml(node.children[i], human_readable, indent + 1));
        }
        r += childs.join(cr);
        r += cr + sindent + '</' + node.tag + '>';
        return r;
    } else {
        return r + '/>';
    }
}

function xml_to_str (node) {
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
    str = str.replace(/<([a-z]+)([^<>]*)\s*\/\s*>/g, function(match, tag, attrs) {
        if (void_elements.indexOf(tag) < 0) {
            return "<" + tag + attrs + "></" + tag + ">";
        } else {
            return match;
        }
    });
    return str;
}

function Mutex () {
    this.def = $.Deferred().resolve();
}

Mutex.prototype.exec = function (action) {
    var current = this.def;
    var next = this.def = $.Deferred();
    return current.then(function() {
        return $.when(action()).always(function() {
            next.resolve();
        });
    });
};

function get_cookie (c_name) {
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
}

/**
 * Create a cookie
 * @param {String} name : the name of the cookie
 * @param {String} value : the value stored in the cookie
 * @param {Integer} ttl : time to live of the cookie in millis. -1 to erase the cookie.
 */
function set_cookie(name, value, ttl) {
    ttl = ttl || 24*60*60*365;
    document.cookie = [
        name + '=' + value,
        'path=/',
        'max-age=' + ttl,
        'expires=' + new Date(new Date().getTime() + ttl*1000).toGMTString()
    ].join(';');
};

/**
 * Insert "thousands" separators in the provided number (which is actually
 * a string)
 *
 * @param {String} num
 * @returns {String}
 */
function insert_thousand_seps (num) {
    var negative = num[0] === '-';
    num = (negative ? num.slice(1) : num);
    return (negative ? '-' : '') + intersperse(
        num, _t.database.parameters.grouping, _t.database.parameters.thousands_sep);
}

function is_bin_size (v) {
    return (/^\d+(\.\d*)? \w+$/).test(v);
}

/**
 * Check with a scary heuristic if the value is a bin_size or not.
 * If not, compute an approximate size out of the base64 encoded string.
 *
 * @param {String} value original format
 */
function binary_to_binsize (value) {
    if (!value) {
        return human_size(0);
    }
    if (value.substr(0, 10).indexOf(' ') == -1) {
        // Computing approximate size out of base64 encoded string
        // http://en.wikipedia.org/wiki/Base64#MIME
        return human_size(value.length / 1.37);
    } else {
        // already bin_size
        return value;
    }
}

/**
 * Returns a human readable size
 *
 * @param {Number} numner of bytes
 */
function human_size (size) {
    var units = _t("Bytes,Kb,Mb,Gb,Tb,Pb,Eb,Zb,Yb").split(',');
    var i = 0;
    while (size >= 1024) {
        size /= 1024;
        ++i;
    }
    return size.toFixed(2) + ' ' + units[i];
}

/**
 * Returns a human readable number
 *
 * @param {Number} number
 */
function human_number (number) {
    var units = _t(",k,M").split(',');
    var i = 0;
    while (number >= 1000) {
        number /= 1000;
        ++i;
    }
    return parseInt(number) + units[i];
}

/**
 * performs a half up rounding with arbitrary precision, correcting for float loss of precision
 * See the corresponding float_round() in server/tools/float_utils.py for more info
 * @param {Number} the value to be rounded
 * @param {Number} a precision parameter. eg: 0.01 rounds to two digits.
 */
function round_precision (value, precision) {
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
}

/**
 * performs a half up rounding with a fixed amount of decimals, correcting for float loss of precision
 * See the corresponding float_round() in server/tools/float_utils.py for more info
 * @param {Number} the value to be rounded
 * @param {Number} the number of decimals. eg: round_decimals(3.141592,2) -> 3.14
 */
function round_decimals (value, decimals) {
    return round_precision(value, Math.pow(10,-decimals));
}

function float_is_zero (value, decimals) {
    var epsilon = Math.pow(10, -decimals);
    return Math.abs(round_precision(value, epsilon)) < epsilon;
};

/**
 * Confines a value inside an interval
 * @param {Number} [val] the value to confine
 * @param {Number} [min] the minimum of the interval
 * @param {Number} [max] the maximum of the interval
 * @return val if val is in [min, max], min if val < min and max otherwise
 */
function confine (val, min, max) {
    return Math.max(min, Math.min(max, val));
}

function assert (bool) {
    if (!bool) {
        throw new Error("AssertionError");
    }
}

/* Logical XOR */
function xor (a, b) {
    return (a && !b) || (!a && b);
}

var DropMisordered = Class.extend({
    /**
     * @constructs instance.web.DropMisordered
     * @extends instance.web.Class
     *
     * @param {Boolean} [failMisordered=false] whether mis-ordered responses should be failed or just ignored
     */
    init: function (failMisordered) {
        // local sequence number, for requests sent
        this.lsn = 0;
        // remote sequence number, seqnum of last received request
        this.rsn = -1;
        this.failMisordered = failMisordered || false;
    },
    /**
     * Adds a deferred (usually an async request) to the sequencer
     *
     * @param {$.Deferred} deferred to ensure add
     * @returns {$.Deferred}
     */
    add: function (deferred) {
        var res = $.Deferred();

        var self = this, seq = this.lsn++;
        deferred.done(function () {
            if (seq > self.rsn) {
                self.rsn = seq;
                res.resolve.apply(res, arguments);
            } else if (self.failMisordered) {
                res.reject();
            }
        }).fail(function () {
            res.reject.apply(res, arguments);
        });

        return res.promise();
    },
});

function swap(array, elem1, elem2) {
    var i1 = array.indexOf(elem1);
    var i2 = array.indexOf(elem2);
    array[i2] = elem1;
    array[i1] = elem2;
}


return {
    divmod: divmod,
    modf: modf,
    lpad: lpad,
    rpad: rpad,
    generate_id: generate_id,
    intersperse: intersperse,
    xml_to_json: xml_to_json,
    json_node_to_xml: json_node_to_xml,
    xml_to_str: xml_to_str,
    Mutex: Mutex,
    get_cookie: get_cookie,
    set_cookie: set_cookie,
    insert_thousand_seps: insert_thousand_seps,
    is_bin_size: is_bin_size,
    binary_to_binsize: binary_to_binsize,
    human_size: human_size,
    human_number: human_number,
    round_precision: round_precision,
    round_decimals: round_decimals,
    float_is_zero: float_is_zero,
    confine: confine,
    assert: assert,
    xor: xor,
    DropMisordered: DropMisordered,
    swap: swap,
};

});

odoo.define('web.dom_utils', function (require) {
"use strict";

var core = require('web.core');

// TO DO: move this into new file dom_utils.js
/**
 * Autoresize a $textarea node, by recomputing its height when necessary
 * @param {number} [options.min_height] by default, 50.
 * @param {Widget} [options.parent] if set, autoresize will listen to some extra
 * events to decide when to resize itself.  This is useful for widgets that are
 * not in the dom when the autoresize is declared.
 */
function autoresize ($textarea, options) {
    options = options || {};

    var $fixed_text_area;
    var min_height = (options && options.min_height) || 50;
    if (!$fixed_text_area) {
        $fixed_text_area = $('<textarea>').css({
            position: 'absolute',
            opacity: 0,
            height: 10,
            top: -10000,
            left: -10000,
        });
        $fixed_text_area.addClass($textarea[0].className);
        $fixed_text_area.insertAfter($textarea);
    }

    var style = window.getComputedStyle($textarea[0], null);
    if (style.resize === 'vertical') {
        $textarea[0].style.resize = 'none';
    } else if (style.resize === 'both') {
        $textarea[0].style.resize = 'horizontal';
    }
    resize();
    if ($textarea.__auto_resized) {
        return;
    }
    $textarea.__auto_resized = true;

    $textarea.on('input focus', resize);
    if (options.parent) {
        core.bus.on('DOM_updated', options.parent, resize);
        core.bus.on('view_shown', options.parent, resize);
    }

    function resize () {
        var heightOffset;
        var style = window.getComputedStyle($textarea[0], null);
        if (style.boxSizing === 'content-box') {
            heightOffset = -(parseFloat(style.paddingTop) + parseFloat(style.paddingBottom));
        } else {
            heightOffset = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
        }
        $fixed_text_area.width($textarea.width());
        $fixed_text_area.val($textarea.val());
        var height = $fixed_text_area[0].scrollHeight;
        $textarea.css({height: Math.max(height + heightOffset, min_height)});
    }
}

return {
    autoresize: autoresize,
};

});
