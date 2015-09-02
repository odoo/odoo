odoo.define('mail.utils', function () {
"use strict";

/**
 * ------------------------------------------------------------
 * ChatterUtils
 * ------------------------------------------------------------
 * 
 * This class holds a few tools method for Chatter.
 * Some regular expressions not used anymore, kept because I want to
 * - (^|\s)@((\w|@|\.)*): @login@log.log
 * - (^|\s)\[(\w+).(\w+),(\d)\|*((\w|[@ .,])*)\]: [ir.attachment,3|My Label],
 *   for internal links
 */


/** parse text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False */
function parse_email(text) {
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

/**
 * Replaces some expressions
 * - :name - shortcut to an image
 */
function do_replace_expressions(string) {
    var icon_list = ['al', 'pinky'];
    /* special shortcut: :name, try to find an icon if in list */
    var regex_login = new RegExp(/(^|\s):((\w)*)/g);
    var regex_res = regex_login.exec(string);
    while (regex_res !== null) {
        var icon_name = regex_res[2];
        if (_.include(icon_list, icon_name))
            string = string.replace(regex_res[0], regex_res[1] + '<img src="/mail/static/src/img/_' + icon_name + '.png" width="22px" height="22px" alt="' + icon_name + '"/>');
        regex_res = regex_login.exec(string);
    }
    return string;
}

/**
 * Replaces textarea text into html text (add <p>, <a>)
 * TDE note : should be done server-side, in Python -> use mail.compose.message ?
 */
function get_text2html(text) {
    return text
        .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
        .replace(/[\n\r]/g,'<br/>');
}

/* Returns the complete domain with "&" 
 * TDE note: please add some comments to explain how/why
 */
function expand_domain(domain) {
    var nb_and = -1;
    var k;
    // TDE note: smarted code maybe ?
    for (k = domain.length-1; k >= 0 ; k-- ) {
        if (typeof domain[k] != 'object' ) {
            nb_and -= 2;
            continue;
        }
        nb_and += 1;
    }

    for (k = 0; k < nb_and ; k++) {
        domain.unshift('&');
    }

    return domain;
}

// inserts zero width space between each letter of a string so that
// the word will correctly wrap in html boxes smaller than the text
function breakword(str){
    var out = '';
    if (!str) {
        return str;
    }
    for(var i = 0, len = str.length; i < len; i++){
        out += _.str.escapeHTML(str[i]) + '&#8203;';
    }
    return out;
}

function bindTooltipTo($el, value, position) {
    $el.tooltip({
        'title': value,
        'placement': position,
        'html': true,
        'trigger': 'manual',
        'animation': false,
    }).on("mouseleave", function () {
        setTimeout(function () {
            if (!$(".tooltip:hover").length) {
                $el.tooltip("hide");
            }
        }, 100);
    });
}

return {
    parse_email: parse_email,
    do_replace_expressions: do_replace_expressions,
    get_text2html: get_text2html,
    expand_domain: expand_domain,
    breakword: breakword,
    bindTooltipTo: bindTooltipTo,
};

});
