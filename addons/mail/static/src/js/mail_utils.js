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
 * @param {string} mimetype : mimetype to analyse
 * @returns {string} the fa class associated
 */
function attachment_mimetype_icon(mimetype){
    var mapping = {
        'text/plain': 'fa fa-file-text-o',
        'text/css': 'fa fa-file-code-o',
        'text/javascript': 'fa fa-file-code-o',
        'text/html': 'fa fa-file-code-o',
        'image/jpeg': 'fa fa-file-photo-o',
        'image/png': 'fa fa-file-photo-o',
        'image/gif': 'fa fa-file-photo-o',
        'application/octet-stream': 'fa fa-file-code-o',
        'application/pdf': 'fa fa-file-pdf-o',
        'application/zip': 'fa fa-file-archive-o',
        'application/x-compressed': 'fa fa-file-archive-o',
        'application/msword': 'fa fa-file-word-o',
        'application/vnd.ms-excel': 'fa fa-file-excel-o',
        'application/mspowerpoint': 'fa fa-file-powerpoint-o',
        'application/powerpoint': 'fa fa-file-powerpoint-o',
        'application/vnd.ms-powerpoint': 'fa fa-file-powerpoint-o',
        'audio/mpeg3': 'fa fa-file-audio-o',
        'audio/x-mpeg-3': 'fa fa-file-audio-o',
        'audio/mpeg': 'fa fa-file-audio-o',
        'audio/midi': 'fa fa-file-audio-o',
        'video/msvideo': 'fa fa-file-movie-o',
        'video/mpeg': 'fa fa-file-movie-o',
        'video/quicktime': 'fa fa-file-movie-o',
    };
    if(_.contains(_.keys(mapping), mimetype)){
        return mapping[mimetype];
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
    shortcode_apply: shortcode_apply,
    shortcode_substitution: shortcode_substitution,
    attachment_mimetype_icon: attachment_mimetype_icon,
    beep: beep,
};

});
