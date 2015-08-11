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


// TODO JEM : remove me in master
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


/**
 * ------------------------------------------------------------
 * MailChat Utils
 * ------------------------------------------------------------
 */

 /**
  * Apply the given shortcode to the 'str' message.
  * @param str : the text to substitute (html).
  * @param shortcodes : dict where key is the shortcode, and the value is the substitution
  */
function shortcode_apply(str, shortcodes){
    var re_escape = function(str){
        return String(str).replace(/([.*+?=^!:${}()|[\]\/\\])/g, '\\$1');
    };
    _.each(_.keys(shortcodes), function(key){
        str = str.replace( new RegExp("(?:^|\\s|<[a-z]*>)(" + re_escape(key) + ")(?:\\s|$|</[a-z]*>)"), ' <span class="o_mail_emoji">'+shortcodes[key]+'</span> ');
    });
    return str;
}

/**
 * Transform the list of emoji (shortcode Object) into a key-array representing
 * the substitution to apply
 * @param {Ojbect[]} emoji_list : list of emoji object
 * @returns {Object} mapping between the code (as key) and the substitution (as value)
 */
function shortcode_substitution(emoji_list){
    var emoji_substitution = {};
    _.each(emoji_list, function(emoji){
        emoji_substitution[emoji.source] = emoji.substitution;
    });
    return emoji_substitution;
}

/**
 * Associate a font awesome class to a attachment file type
 * @param {string} file_type : file type to analyse
 * @returns {string} the fa class associated
 */
function attachment_filetype_to_fa_class(file_type){
    var mapping = {
        'text': 'fa fa-file-text-o',
        'document': 'fa fa-file-word-o',
        'audio': 'fa fa-file-audio-o',
        'archive': 'fa fa-file-archive-o',
        'disk': 'fa fa-file-archive-o',
        'image': 'fa fa-file-photo-o',
        'webimage': 'fa fa-file-photo-o',
        'script': 'fa fa-file-code-o',
        'html': 'fa fa-file-code-o',
        'video': 'fa fa-file-movie-o',
        'spreadsheet': 'fa fa-file-excel-o',
        'print': 'fa fa-file-pdf-o',
        'presentation': 'fa fa-file-powerpoint-o',
    }
    if(_.contains(_.keys(mapping), file_type)){
        return mapping[file_type];
    }
    return 'fa fa-file-o';
}

/**
 * Play the noise 'ting' to notify user
 */
function beep(session){
    if (typeof(Audio) === "undefined") {
        return;
    }
    var audio = new Audio();
    var ext = audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
    audio.src = session.url("/mail/static/src/audio/ting") + ext;
    audio.play();
}

return {
    parse_email: parse_email,
    get_text2html: get_text2html,
    expand_domain: expand_domain,
    breakword: breakword,
    bindTooltipTo: bindTooltipTo,
    shortcode_apply: shortcode_apply,
    shortcode_substitution: shortcode_substitution,
    attachment_filetype_to_fa_class: attachment_filetype_to_fa_class,
    beep: beep,
};

});
