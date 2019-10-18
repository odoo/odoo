odoo.define('mail.emojis', function (require) {
"use strict";

/**
 * This module exports the list of all available emojis on the client side.
 * An emoji object has the following properties:
 *
 *      - {string[]} sources: the character representations of the emoji
 *      - {string} unicode: the unicode representation of the emoji
 *      - {string} description: the description of the emoji
 */

/**
 * This data represent all the available emojis that are supported on the web
 * client:
 *
 * - key: this is the source representation of an emoji, i.e. its "character"
 *        representation. This is a string that can be easily typed by the
 *        user and then translated to its unicode representation (see value)
 * - value: this is the unicode representation of an emoji, i.e. its "true"
 *          representation in the system.
 */
var data = {
    ":)":             "😊",
    ":-)":            "😊", // alternative (alt.)
    "=)":             "😊", // alt.
    ":]":             "😊", // alt.
    ":D":             "😃",
    ":-D":            "😃", // alt.
    "=D":             "😃", // alt.
    "xD":             "😆",
    "XD":             "😆", // alt.
    "x'D":            "😂",
    ";)":             "😉",
    ";-)":            "😉", // alt.
    "B)":             "😎",
    "8)":             "😎", // alt.
    "B-)":            "😎", // alt.
    "8-)":            "😎", // alt.
    ";p":             "😜",
    ";P":             "😜", // alt.
    ":p":             "😋",
    ":P":             "😋", // alt.
    ":-p":            "😋", // alt.
    ":-P":            "😋", // alt.
    "=P":             "😋", // alt.
    "xp":             "😝",
    "xP":             "😝", // alt.
    "o_o":            "😳",
    ":|":             "😐",
    ":-|":            "😐", // alt.
    ":/":             "😕", // alt.
    ":-/":            "😕", // alt.
    ":(":             "😞",
    ":@":             "😱",
    ":O":             "😲",
    ":-O":            "😲", // alt.
    ":o":             "😲", // alt.
    ":-o":            "😲", // alt.
    ":'o":            "😨",
    "3:(":            "😠",
    ">:(":            "😠", // alt.
    "3:":             "😠", // alt.
    "3:)":            "😈",
    ">:)":            "😈", // alt.
    ":*":             "😘",
    ":-*":            "😘", // alt.
    "o:)":            "😇",
    ":'(":            "😢",
    ":'-(":           "😭",
    ":\"(":           "😭", // alt.
    "<3":             "❤️",
    "&lt;3":          "❤️",
    ":heart":         "❤️", // alt.
    "</3":            "💔",
    "&lt;/3":         "💔",
    ":heart_eyes":    "😍",
    ":turban":        "👳",
    ":+1":            "👍",
    ":-1":            "👎",
    ":ok":            "👌",
    ":poop":          "💩",
    ":no_see":        "🙈",
    ":no_hear":       "🙉",
    ":no_speak":      "🙊",
    ":bug":           "🐞",
    ":kitten":        "😺",
    ":bear":          "🐻",
    ":snail":         "🐌",
    ":boar":          "🐗",
    ":clover":        "🍀",
    ":sunflower":     "🌹",
    ":fire":          "🔥",
    ":sun":           "☀️",
    ":partly_sunny:": "⛅️",
    ":rainbow":       "🌈",
    ":cloud":         "☁️",
    ":zap":           "⚡️",
    ":star":          "⭐️",
    ":cookie":        "🍪",
    ":pizza":         "🍕",
    ":hamburger":     "🍔",
    ":fries":         "🍟",
    ":cake":          "🎂",
    ":cake_part":     "🍰",
    ":coffee":        "☕️",
    ":banana":        "🍌",
    ":sushi":         "🍣",
    ":rice_ball":     "🍙",
    ":beer":          "🍺",
    ":wine":          "🍷",
    ":cocktail":      "🍸",
    ":tropical":      "🍹",
    ":beers":         "🍻",
    ":ghost":         "👻",
    ":skull":         "💀",
    ":et":            "👽",
    ":alien":         "👽", // alt.
    ":party":         "🎉",
    ":trophy":        "🏆",
    ":key":           "🔑",
    ":pin":           "📌",
    ":postal_horn":   "📯",
    ":music":         "🎵",
    ":trumpet":       "🎺",
    ":guitar":        "🎸",
    ":run":           "🏃",
    ":bike":          "🚲",
    ":soccer":        "⚽️",
    ":football":      "🏈",
    ":8ball":         "🎱",
    ":clapper":       "🎬",
    ":microphone":    "🎤",
    ":cheese":        "🧀",
};

// list of emojis in a dictionary, indexed by emoji unicode
var emojiDict = {};
_.each(data, function (unicode, source) {
    if (!emojiDict[unicode]) {
        emojiDict[unicode] = {
            sources: [source],
            unicode: unicode,
            description: source,
        };
    } else {
        emojiDict[unicode].sources.push(source);
    }
});

var emojis = _.values(emojiDict);

return emojis;

});
