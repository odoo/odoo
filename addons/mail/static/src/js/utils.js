odoo.define('mail.utils', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var session = require('web.session');
var web_client = require('web.web_client');


function send_notification(title, content) {
    if (Notification && Notification.permission === "granted") {
        if (bus.is_master) {
            _send_native_notification(title, content);
        }
    } else {
        web_client.do_notify(title, content);
        if (bus.is_master) {
            _beep();
        }
    }
}
function _send_native_notification(title, content) {
    var notification = new Notification(title, {body: content, icon: "/mail/static/src/img/odoo_o.png"});
    notification.onclick = function () {
        window.focus();
        if (this.cancel) {
            this.cancel();
        } else if (this.close) {
            this.close();
        }
    };
}
var _beep = (function () {
    if (typeof(Audio) === "undefined") {
        return function () {};
    }
    var audio;
    return function () {
        if (!audio) {
            audio = new Audio();
            var ext = audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
            audio.src = session.url("/mail/static/src/audio/ting" + ext);
        }
        audio.play();
    };
})();

function parse_and_transform(html_string, transform_function) {
    var open_token = "OPEN" + Date.now();
    var string = html_string.replace(/&lt;/g, open_token);
    var children = $('<div>').html(string).contents();
    return _parse_and_transform(children, transform_function)
                .replace(new RegExp(open_token, "g"), "&lt;");
}
function _parse_and_transform(nodes, transform_function) {
    return _.map(nodes, function (node) {
        return transform_function(node, function () {
            return _parse_and_transform(node.childNodes, transform_function);
        });
    }).join("");
}

// Suggested URL Javascript regex of http://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url
// Adapted to make http(s):// not required if (and only if) www. is given. So `should.notmatch` does not match.
var url_regexp = /\b(?:https?:\/\/|(www\.))[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,13}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)/gi;
function add_link (node, transform_children) {
    if (node.nodeType === 3) {  // text node
        return node.data.replace(url_regexp, function (url) {
            var href = (!/^(f|ht)tps?:\/\//i.test(url)) ? "http://" + url : url;
            return '<a target="_blank" href="' + href + '">' + url + '</a>';
        });
    }
    if (node.tagName === "A") return node.outerHTML;
    node.innerHTML = transform_children();
    return node.outerHTML;
}

function strip_html (node, transform_children) {
    if (node.nodeType === 3) return node.data;  // text node
    if (node.tagName === "BR") return "\n";
    return transform_children();
}

function inline (node, transform_children) {
    if (node.nodeType === 3) return node.data;
    if (node.tagName === "BR") return " ";
    if (node.tagName.match(/^(A|P|DIV|PRE|BLOCKQUOTE)$/)) return transform_children();
    node.innerHTML = transform_children();
    return node.outerHTML;
}

// Parses text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False
function parse_email (text) {
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

// Replaces textarea text into html text (add <p>, <a>)
// TDE note : should be done server-side, in Python -> use mail.compose.message ?
function get_text2html (text) {
    return text
        .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
        .replace(/[\n\r]/g,'<br/>');
}

var accented_letters_mapping = {
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
    ' ': '[()\\[\\]]',
};
function unaccent (str) {
    _.each(accented_letters_mapping, function (value, key) {
        str = str.replace(new RegExp(value, 'g'), key);
    });
    return str;
}

return {
    send_notification: send_notification,
    parse_and_transform: parse_and_transform,
    add_link: add_link,
    strip_html: strip_html,
    inline: inline,
    parse_email: parse_email,
    get_text2html: get_text2html,
    unaccent: unaccent,
};

});
