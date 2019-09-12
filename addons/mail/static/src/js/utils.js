odoo.define('mail.utils', function (require) {
"use strict";

<<<<<<< HEAD
var core = require('web.core');

var _t = core._t;

function parseAndTransform(htmlString, transformFunction) {
    var openToken = "OPEN" + Date.now();
    var string = htmlString.replace(/&lt;/g, openToken);
=======
function parse_and_transform(html_string, transform_function) {
    var open_token = "OPEN" + Date.now();
    var string = html_string.replace(/&lt;/g, open_token);
>>>>>>> 44a93d745c2... temp
    var children;
    try {
        children = $('<div>').html(string).contents();
    } catch (e) {
        children = $('<div>').html('<pre>' + string + '</pre>').contents();
    }
<<<<<<< HEAD
    return _parseAndTransform(children, transformFunction)
                .replace(new RegExp(openToken, "g"), "&lt;");
=======
    return _parse_and_transform(children, transform_function)
                .replace(new RegExp(open_token, "g"), "&lt;");
>>>>>>> 44a93d745c2... temp
}
function _parseAndTransform(nodes, transformFunction) {
    return _.map(nodes, function (node) {
        return transformFunction(node, function () {
            return _parseAndTransform(node.childNodes, transformFunction);
        });
    }).join("");
}

// Suggested URL Javascript regex of http://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url
// Adapted to make http(s):// not required if (and only if) www. is given. So `should.notmatch` does not match.
var urlRegexp = /\b(?:https?:\/\/\d{1,3}(?:\.\d{1,3}){3}|(?:https?:\/\/|(?:www\.))[-a-z0-9@:%._+~#=]{2,256}\.[a-z]{2,13})\b(?:[-a-z0-9@:%_+.~#?&'$//=;]*)/gi;
function linkify(text, attrs) {
    attrs = attrs || {};
    if (attrs.target === undefined) {
        attrs.target = '_blank';
    }
    attrs = _.map(attrs, function (value, key) {
        return key + '="' + _.escape(value) + '"';
    }).join(' ');
    return text.replace(urlRegexp, function (url) {
        var href = (!/^https?:\/\//i.test(url)) ? "http://" + url : url;
        return '<a ' + attrs + ' href="' + href + '">' + url + '</a>';
    });
}

function addLink(node, transformChildren) {
    if (node.nodeType === 3) {  // text node
        return linkify(node.data);
    }
    if (node.tagName === "A") return node.outerHTML;
    node.innerHTML = transformChildren();
    return node.outerHTML;
}

function stripHTML(node, transformChildren) {
    if (node.nodeType === 3) return node.data;  // text node
    if (node.tagName === "BR") return "\n";
    return transformChildren();
}

function inline(node, transform_children) {
    if (node.nodeType === 3) return node.data;
    if (node.nodeType === 8) return "";
    if (node.tagName === "BR") return " ";
    if (node.tagName.match(/^(A|P|DIV|PRE|BLOCKQUOTE)$/)) return transform_children();
    node.innerHTML = transform_children();
    return node.outerHTML;
}

// Parses text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False
function parseEmail(text) {
    if (text){
        var result = text.match(/(.*)<(.*@.*)>/);
        if (result) {
            return [_.str.trim(result[1]), _.str.trim(result[2])];
        }
        result = text.match(/(.*@.*)/);
        if (result) {
            return [_.str.trim(result[1]), _.str.trim(result[1])];
        }
        return [text, false];
    }
}

// Replaces textarea text into html text (add <p>, <a>)
// TDE note : should be done server-side, in Python -> use mail.compose.message ?
function getTextToHTML(text) {
    return text
        .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
        .replace(/[\n\r]/g,'<br/>');
}

var accentedLettersMapping = {
    'a': '[àáâãäå]',
    'ae': 'æ',
    'c': 'ç',
    'e': '[èéêë]',
    'i': '[ìíîï]',
    'n': 'ñ',
    'o': '[òóôõö]',
    'oe': 'œ',
    'u': '[ùúûűü]',
    'y': '[ýÿ]',
};
function unaccent(str) {
    _.each(accentedLettersMapping, function (value, key) {
        str = str.replace(new RegExp(value, 'g'), key);
    });
    return str;
}

function timeFromNow(date) {
    if (moment().diff(date, 'seconds') < 45) {
        return _t("now");
    }
    return date.fromNow();
}

return {
    addLink: addLink,
    getTextToHTML: getTextToHTML,
    inline: inline,
    linkify: linkify,
    parseAndTransform: parseAndTransform,
    parseEmail: parseEmail,
    stripHTML: stripHTML,
    timeFromNow: timeFromNow,
    unaccent: unaccent,
};

});
