/** @odoo-module **/

// Emoji data are generated from Unicode CLDR, falling under the following
// licence:

/**
 * UNICODE, INC. LICENSE AGREEMENT - DATA FILES AND SOFTWARE
 *
 * See Terms of Use <https://www.unicode.org/copyright.html>
 * for definitions of Unicode Inc.’s Data Files and Software.
 *
 * NOTICE TO USER: Carefully read the following legal agreement.
 * BY DOWNLOADING, INSTALLING, COPYING OR OTHERWISE USING UNICODE INC.'S
 * DATA FILES ("DATA FILES"), AND/OR SOFTWARE ("SOFTWARE"),
 * YOU UNEQUIVOCALLY ACCEPT, AND AGREE TO BE BOUND BY, ALL OF THE
 * TERMS AND CONDITIONS OF THIS AGREEMENT.
 * IF YOU DO NOT AGREE, DO NOT DOWNLOAD, INSTALL, COPY, DISTRIBUTE OR USE
 * THE DATA FILES OR SOFTWARE.
 *
 * COPYRIGHT AND PERMISSION NOTICE
 *
 * Copyright © 1991-2022 Unicode, Inc. All rights reserved.
 * Distributed under the Terms of Use in https://www.unicode.org/copyright.html.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of the Unicode data files and any associated documentation
 * (the "Data Files") or Unicode software and any associated documentation
 * (the "Software") to deal in the Data Files or Software
 * without restriction, including without limitation the rights to use,
 * copy, modify, merge, publish, distribute, and/or sell copies of
 * the Data Files or Software, and to permit persons to whom the Data Files
 * or Software are furnished to do so, provided that either
 * (a) this copyright and permission notice appear with all copies
 * of the Data Files or Software, or
 * (b) this copyright and permission notice appear in associated
 * Documentation.
 *
 * THE DATA FILES AND SOFTWARE ARE PROVIDED "AS IS", WITHOUT WARRANTY OF
 * ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
 * WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT OF THIRD PARTY RIGHTS.
 * IN NO EVENT SHALL THE COPYRIGHT HOLDER OR HOLDERS INCLUDED IN THIS
 * NOTICE BE LIABLE FOR ANY CLAIM, OR ANY SPECIAL INDIRECT OR CONSEQUENTIAL
 * DAMAGES, OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
 * DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
 * TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
 * PERFORMANCE OF THE DATA FILES OR SOFTWARE.
 *
 * Except as contained in this notice, the name of a copyright holder
 * shall not be used in advertising or otherwise to promote the sale,
 * use or other dealings in these Data Files or Software without prior
 * written authorization of the copyright holder.
 */

// Since JSON grammar is way simpler than JavaScript's grammar, it is actually
// faster to parse the data as a JSON object than as a JavaScript object.
export const emojiCategoriesData = JSON.parse(`[
    {
        "name": "Smileys & Emotion",
        "title": "🤠",
        "sortId": 1
    },
    {
        "name": "People & Body",
        "title": "🤟",
        "sortId": 2
    },
    {
        "name": "Animals & Nature",
        "title": "🐘",
        "sortId": 3
    },
    {
        "name": "Food & Drink",
        "title": "🍔",
        "sortId": 4
    },
    {
        "name": "Travel & Places",
        "title": "🚍",
        "sortId": 5
    },
    {
        "name": "Activities",
        "title": "🎣",
        "sortId": 6
    },
    {
        "name": "Objects",
        "title": "🎩",
        "sortId": 7
    },
    {
        "name": "Symbols",
        "title": "🚰",
        "sortId": 8
    },
    {
        "name": "Flags",
        "title": "🇻🇨",
        "sortId": 9
    }
]`);

export const emojisData = JSON.parse(`[
    {
        "codepoints": "😀",
        "name": "grinning face",
        "shortcodes": [
            ":grinning:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "grin",
            "grinning face"
        ]
    },
    {
        "codepoints": "😃",
        "name": "grinning face with big eyes",
        "shortcodes": [
            ":smiley:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "grinning face with big eyes",
            "mouth",
            "open",
            "smile"
        ]
    },
    {
        "codepoints": "😄",
        "name": "grinning face with smiling eyes",
        "shortcodes": [
            ":smile:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "eye",
            "face",
            "grinning face with smiling eyes",
            "mouth",
            "open",
            "smile"
        ]
    },
    {
        "codepoints": "😁",
        "name": "beaming face with smiling eyes",
        "shortcodes": [
            ":grin:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "beaming face with smiling eyes",
            "eye",
            "face",
            "grin",
            "smile"
        ]
    },
    {
        "codepoints": "😆",
        "name": "grinning squinting face",
        "shortcodes": [
            ":laughing:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "grinning squinting face",
            "laugh",
            "mouth",
            "satisfied",
            "smile"
        ]
    },
    {
        "codepoints": "😅",
        "name": "grinning face with sweat",
        "shortcodes": [
            ":sweat_smile:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cold",
            "face",
            "grinning face with sweat",
            "open",
            "smile",
            "sweat"
        ]
    },
    {
        "codepoints": "🤣",
        "name": "rolling on the floor laughing",
        "shortcodes": [
            ":rofl:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "floor",
            "laugh",
            "rofl",
            "rolling",
            "rolling on the floor laughing",
            "rotfl"
        ]
    },
    {
        "codepoints": "😂",
        "name": "face with tears of joy",
        "shortcodes": [
            ":joy:",
            ":jpp:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face with tears of joy",
            "joy",
            "laugh",
            "tear"
        ]
    },
    {
        "codepoints": "🙂",
        "name": "slightly smiling face",
        "shortcodes": [
            ":slight_smile:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "slightly smiling face",
            "smile"
        ]
    },
    {
        "codepoints": "🙃",
        "name": "upside-down face",
        "shortcodes": [
            ":upside_down:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "upside-down",
            "upside down",
            "upside-down face"
        ]
    },
    {
        "codepoints": "🫠",
        "name": "melting face",
        "shortcodes": [
            ":melt:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "disappear",
            "dissolve",
            "liquid",
            "melt",
            "melting face"
        ]
    },
    {
        "codepoints": "😉",
        "name": "winking face",
        "shortcodes": [
            ":wink:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "wink",
            "winking face"
        ]
    },
    {
        "codepoints": "😊",
        "name": "smiling face with smiling eyes",
        "shortcodes": [
            ":smiling_face_with_smiling_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "blush",
            "eye",
            "face",
            "smile",
            "smiling face with smiling eyes"
        ]
    },
    {
        "codepoints": "😇",
        "name": "smiling face with halo",
        "shortcodes": [
            ":innocent:",
            ":halo:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "angel",
            "face",
            "fantasy",
            "halo",
            "innocent",
            "smiling face with halo"
        ]
    },
    {
        "codepoints": "🥰",
        "name": "smiling face with hearts",
        "shortcodes": [
            ":smiling_face_with_hearts:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "adore",
            "crush",
            "hearts",
            "in love",
            "smiling face with hearts"
        ]
    },
    {
        "codepoints": "😍",
        "name": "smiling face with heart-eyes",
        "shortcodes": [
            ":heart_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "eye",
            "face",
            "love",
            "smile",
            "smiling face with heart-eyes",
            "smiling face with heart eyes"
        ]
    },
    {
        "codepoints": "🤩",
        "name": "star-struck",
        "shortcodes": [
            ":star_struck:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "eyes",
            "face",
            "grinning",
            "star",
            "star-struck"
        ]
    },
    {
        "codepoints": "😘",
        "name": "face blowing a kiss",
        "shortcodes": [
            ":kissing_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face blowing a kiss",
            "kiss"
        ]
    },
    {
        "codepoints": "😗",
        "name": "kissing face",
        "shortcodes": [
            ":kissing:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "kiss",
            "kissing face"
        ]
    },
    {
        "codepoints": "☺️",
        "name": "smiling face",
        "shortcodes": [
            ":smiling_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "outlined",
            "relaxed",
            "smile",
            "smiling face"
        ]
    },
    {
        "codepoints": "😚",
        "name": "kissing face with closed eyes",
        "shortcodes": [
            ":kissing_closed_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "closed",
            "eye",
            "face",
            "kiss",
            "kissing face with closed eyes"
        ]
    },
    {
        "codepoints": "😙",
        "name": "kissing face with smiling eyes",
        "shortcodes": [
            ":kissing_smiling_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "eye",
            "face",
            "kiss",
            "kissing face with smiling eyes",
            "smile"
        ]
    },
    {
        "codepoints": "🥲",
        "name": "smiling face with tear",
        "shortcodes": [
            ":smiling_face_with_tear:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "grateful",
            "proud",
            "relieved",
            "smiling",
            "smiling face with tear",
            "tear",
            "touched"
        ]
    },
    {
        "codepoints": "😋",
        "name": "face savoring food",
        "shortcodes": [
            ":yum:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "delicious",
            "face",
            "face savoring food",
            "savouring",
            "smile",
            "yum",
            "face savouring food",
            "savoring"
        ]
    },
    {
        "codepoints": "😛",
        "name": "face with tongue",
        "shortcodes": [
            ":stuck_out_tongue:"
        ],
        "emoticons": [
            ":P"
        ],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face with tongue",
            "tongue"
        ]
    },
    {
        "codepoints": "😜",
        "name": "winking face with tongue",
        "shortcodes": [
            ":stuck_out_tongue_winking_eye:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "eye",
            "face",
            "joke",
            "tongue",
            "wink",
            "winking face with tongue"
        ]
    },
    {
        "codepoints": "🤪",
        "name": "zany face",
        "shortcodes": [
            ":zany:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "eye",
            "goofy",
            "large",
            "small",
            "zany face"
        ]
    },
    {
        "codepoints": "😝",
        "name": "squinting face with tongue",
        "shortcodes": [
            ":stuck_out_tongue_closed_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "eye",
            "face",
            "horrible",
            "squinting face with tongue",
            "taste",
            "tongue"
        ]
    },
    {
        "codepoints": "🤑",
        "name": "money-mouth face",
        "shortcodes": [
            ":money_mouth:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "money",
            "money-mouth face",
            "mouth"
        ]
    },
    {
        "codepoints": "🤗",
        "name": "smiling face with open hands",
        "shortcodes": [
            ":hugging_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "hug",
            "hugging",
            "open hands",
            "smiling face",
            "smiling face with open hands"
        ]
    },
    {
        "codepoints": "🤭",
        "name": "face with hand over mouth",
        "shortcodes": [
            ":hand_over_mouth:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face with hand over mouth",
            "whoops",
            "oops",
            "embarrassed"
        ]
    },
    {
        "codepoints": "🫢",
        "name": "face with open eyes and hand over mouth",
        "shortcodes": [
            ":gasp:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "amazement",
            "awe",
            "disbelief",
            "embarrass",
            "face with open eyes and hand over mouth",
            "scared",
            "surprise"
        ]
    },
    {
        "codepoints": "🫣",
        "name": "face with peeking eye",
        "shortcodes": [
            ":peek:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "captivated",
            "face with peeking eye",
            "peep",
            "stare"
        ]
    },
    {
        "codepoints": "🤫",
        "name": "shushing face",
        "shortcodes": [
            ":shush:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "quiet",
            "shooshing face",
            "shush",
            "shushing face"
        ]
    },
    {
        "codepoints": "🤔",
        "name": "thinking face",
        "shortcodes": [
            ":thinking:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "thinking"
        ]
    },
    {
        "codepoints": "🫡",
        "name": "saluting face",
        "shortcodes": [
            ":salute:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "OK",
            "salute",
            "saluting face",
            "sunny",
            "troops",
            "yes"
        ]
    },
    {
        "codepoints": "🤐",
        "name": "zipper-mouth face",
        "shortcodes": [
            ":zipper_mouth:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "mouth",
            "zipper",
            "zipper-mouth face"
        ]
    },
    {
        "codepoints": "🤨",
        "name": "face with raised eyebrow",
        "shortcodes": [
            ":raised_eyebrow:",
            ":skeptic:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "distrust",
            "face with raised eyebrow",
            "skeptic"
        ]
    },
    {
        "codepoints": "😐",
        "name": "neutral face",
        "shortcodes": [
            ":neutral:"
        ],
        "emoticons": [
            ":|",
            ":-|"
        ],
        "category": "Smileys & Emotion",
        "keywords": [
            "deadpan",
            "face",
            "meh",
            "neutral"
        ]
    },
    {
        "codepoints": "😑",
        "name": "expressionless face",
        "shortcodes": [
            ":expressionless:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "expressionless",
            "face",
            "inexpressive",
            "meh",
            "unexpressive"
        ]
    },
    {
        "codepoints": "😶",
        "name": "face without mouth",
        "shortcodes": [
            ":no_mouth:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face without mouth",
            "mouth",
            "quiet",
            "silent"
        ]
    },
    {
        "codepoints": "🫥",
        "name": "dotted line face",
        "shortcodes": [
            ":dotted_line_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "depressed",
            "disappear",
            "dotted line face",
            "hide",
            "introvert",
            "invisible"
        ]
    },
    {
        "codepoints": "😶‍🌫️",
        "name": "face in clouds",
        "shortcodes": [
            ":face_in_clouds:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "absentminded",
            "face in clouds",
            "face in the fog",
            "head in clouds",
            "absent-minded"
        ]
    },
    {
        "codepoints": "😏",
        "name": "smirking face",
        "shortcodes": [
            ":smirk:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "smirk",
            "smirking face"
        ]
    },
    {
        "codepoints": "😒",
        "name": "unamused face",
        "shortcodes": [
            ":unamused_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "unamused",
            "unhappy"
        ]
    },
    {
        "codepoints": "🙄",
        "name": "face with rolling eyes",
        "shortcodes": [
            ":face_with_rolling_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "eyeroll",
            "eyes",
            "face",
            "face with rolling eyes",
            "rolling"
        ]
    },
    {
        "codepoints": "😬",
        "name": "grimacing face",
        "shortcodes": [
            ":grimacing_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "grimace",
            "grimacing face"
        ]
    },
    {
        "codepoints": "😮‍💨",
        "name": "face exhaling",
        "shortcodes": [
            ":face_exhaling:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "exhale",
            "face exhaling",
            "gasp",
            "groan",
            "relief",
            "whisper",
            "whistle"
        ]
    },
    {
        "codepoints": "🤥",
        "name": "lying face",
        "shortcodes": [
            ":lying_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "lie",
            "lying face",
            "pinocchio"
        ]
    },
    {
        "codepoints": "😌",
        "name": "relieved face",
        "shortcodes": [
            ":relieved_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "relieved"
        ]
    },
    {
        "codepoints": "😔",
        "name": "pensive face",
        "shortcodes": [
            ":pensive_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "dejected",
            "face",
            "pensive"
        ]
    },
    {
        "codepoints": "😪",
        "name": "sleepy face",
        "shortcodes": [
            ":sleepy_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "good night",
            "sleep",
            "sleepy face"
        ]
    },
    {
        "codepoints": "🤤",
        "name": "drooling face",
        "shortcodes": [
            ":drooling_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "drooling",
            "face"
        ]
    },
    {
        "codepoints": "😴",
        "name": "sleeping face",
        "shortcodes": [
            ":sleeping_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "good night",
            "sleep",
            "sleeping face",
            "ZZZ"
        ]
    },
    {
        "codepoints": "😷",
        "name": "face with medical mask",
        "shortcodes": [
            ":face_with_medical_mask:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cold",
            "doctor",
            "face",
            "face with medical mask",
            "mask",
            "sick",
            "ill",
            "medicine",
            "poorly"
        ]
    },
    {
        "codepoints": "🤒",
        "name": "face with thermometer",
        "shortcodes": [
            ":face_with_thermometer:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face with thermometer",
            "ill",
            "sick",
            "thermometer"
        ]
    },
    {
        "codepoints": "🤕",
        "name": "face with head-bandage",
        "shortcodes": [
            ":face_with_head-bandage:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "bandage",
            "face",
            "face with head-bandage",
            "hurt",
            "injury",
            "face with head bandage"
        ]
    },
    {
        "codepoints": "🤢",
        "name": "nauseated face",
        "shortcodes": [
            ":nauseated_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "nauseated",
            "vomit"
        ]
    },
    {
        "codepoints": "🤮",
        "name": "face vomiting",
        "shortcodes": [
            ":face_vomiting:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face vomiting",
            "puke",
            "sick",
            "vomit"
        ]
    },
    {
        "codepoints": "🤧",
        "name": "sneezing face",
        "shortcodes": [
            ":sneezing_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "gesundheit",
            "sneeze",
            "sneezing face",
            "bless you"
        ]
    },
    {
        "codepoints": "🥵",
        "name": "hot face",
        "shortcodes": [
            ":hot_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "feverish",
            "flushed",
            "heat stroke",
            "hot",
            "hot face",
            "red-faced",
            "sweating"
        ]
    },
    {
        "codepoints": "🥶",
        "name": "cold face",
        "shortcodes": [
            ":cold_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "blue-faced",
            "cold",
            "cold face",
            "freezing",
            "frostbite",
            "icicles"
        ]
    },
    {
        "codepoints": "🥴",
        "name": "woozy face",
        "shortcodes": [
            ":woozy_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "dizzy",
            "intoxicated",
            "tipsy",
            "uneven eyes",
            "wavy mouth",
            "woozy face"
        ]
    },
    {
        "codepoints": "😵",
        "name": "face with crossed-out eyes",
        "shortcodes": [
            ":face_with_crossed-out_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "crossed-out eyes",
            "dead",
            "face",
            "face with crossed-out eyes",
            "knocked out"
        ]
    },
    {
        "codepoints": "😵‍💫",
        "name": "face with spiral eyes",
        "shortcodes": [
            ":face_with_spiral_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "dizzy",
            "face with spiral eyes",
            "hypnotized",
            "spiral",
            "trouble",
            "whoa",
            "hypnotised"
        ]
    },
    {
        "codepoints": "🤯",
        "name": "exploding head",
        "shortcodes": [
            ":exploding_head:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "exploding head",
            "mind blown",
            "shocked"
        ]
    },
    {
        "codepoints": "🤠",
        "name": "cowboy hat face",
        "shortcodes": [
            ":cowboy_hat_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cowboy",
            "cowgirl",
            "face",
            "hat"
        ]
    },
    {
        "codepoints": "🥳",
        "name": "partying face",
        "shortcodes": [
            ":partying_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "celebration",
            "hat",
            "horn",
            "party",
            "partying face"
        ]
    },
    {
        "codepoints": "🥸",
        "name": "disguised face",
        "shortcodes": [
            ":disguised_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "disguise",
            "disguised face",
            "face",
            "glasses",
            "incognito",
            "nose"
        ]
    },
    {
        "codepoints": "😎",
        "name": "smiling face with sunglasses",
        "shortcodes": [
            ":smiling_face_with_sunglasses:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "bright",
            "cool",
            "face",
            "smiling face with sunglasses",
            "sun",
            "sunglasses"
        ]
    },
    {
        "codepoints": "🤓",
        "name": "nerd face",
        "shortcodes": [
            ":nerd_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "geek",
            "nerd"
        ]
    },
    {
        "codepoints": "🧐",
        "name": "face with monocle",
        "shortcodes": [
            ":face_with_monocle:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face with monocle",
            "monocle",
            "stuffy"
        ]
    },
    {
        "codepoints": "😕",
        "name": "confused face",
        "shortcodes": [
            ":confused_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "confused",
            "face",
            "meh"
        ]
    },
    {
        "codepoints": "🫤",
        "name": "face with diagonal mouth",
        "shortcodes": [
            ":face_with_diagonal_mouth:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "disappointed",
            "face with diagonal mouth",
            "meh",
            "skeptical",
            "unsure",
            "sceptical"
        ]
    },
    {
        "codepoints": "😟",
        "name": "worried face",
        "shortcodes": [
            ":worried_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "worried"
        ]
    },
    {
        "codepoints": "🙁",
        "name": "slightly frowning face",
        "shortcodes": [
            ":slightly_frowning_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "frown",
            "slightly frowning face"
        ]
    },
    {
        "codepoints": "☹️",
        "name": "frowning face",
        "shortcodes": [
            ":frowning_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "frown",
            "frowning face"
        ]
    },
    {
        "codepoints": "😮",
        "name": "face with open mouth",
        "shortcodes": [
            ":face_with_open_mouth:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face with open mouth",
            "mouth",
            "open",
            "sympathy"
        ]
    },
    {
        "codepoints": "😯",
        "name": "hushed face",
        "shortcodes": [
            ":hushed_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "hushed",
            "stunned",
            "surprised"
        ]
    },
    {
        "codepoints": "😲",
        "name": "astonished face",
        "shortcodes": [
            ":astonished_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "astonished",
            "face",
            "shocked",
            "totally"
        ]
    },
    {
        "codepoints": "😳",
        "name": "flushed face",
        "shortcodes": [
            ":flushed_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "dazed",
            "face",
            "flushed"
        ]
    },
    {
        "codepoints": "🥺",
        "name": "pleading face",
        "shortcodes": [
            ":pleading_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "begging",
            "mercy",
            "pleading face",
            "puppy eyes"
        ]
    },
    {
        "codepoints": "🥹",
        "name": "face holding back tears",
        "shortcodes": [
            ":face_holding_back_tears:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "angry",
            "cry",
            "face holding back tears",
            "proud",
            "resist",
            "sad"
        ]
    },
    {
        "codepoints": "😦",
        "name": "frowning face with open mouth",
        "shortcodes": [
            ":frowning_face_with_open_mouth:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "frown",
            "frowning face with open mouth",
            "mouth",
            "open"
        ]
    },
    {
        "codepoints": "😧",
        "name": "anguished face",
        "shortcodes": [
            ":anguished_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "anguished",
            "face"
        ]
    },
    {
        "codepoints": "😨",
        "name": "fearful face",
        "shortcodes": [
            ":fearful_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "fear",
            "fearful",
            "scared"
        ]
    },
    {
        "codepoints": "😰",
        "name": "anxious face with sweat",
        "shortcodes": [
            ":anxious_face_with_sweat:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "anxious face with sweat",
            "blue",
            "cold",
            "face",
            "rushed",
            "sweat"
        ]
    },
    {
        "codepoints": "😥",
        "name": "sad but relieved face",
        "shortcodes": [
            ":sad_but_relieved_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "disappointed",
            "face",
            "relieved",
            "sad but relieved face",
            "whew"
        ]
    },
    {
        "codepoints": "😢",
        "name": "crying face",
        "shortcodes": [
            ":crying_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cry",
            "crying face",
            "face",
            "sad",
            "tear"
        ]
    },
    {
        "codepoints": "😭",
        "name": "loudly crying face",
        "shortcodes": [
            ":loudly_crying_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cry",
            "face",
            "loudly crying face",
            "sad",
            "sob",
            "tear"
        ]
    },
    {
        "codepoints": "😱",
        "name": "face screaming in fear",
        "shortcodes": [
            ":face_screaming_in_fear:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face screaming in fear",
            "fear",
            "Munch",
            "scared",
            "scream",
            "munch"
        ]
    },
    {
        "codepoints": "😖",
        "name": "confounded face",
        "shortcodes": [
            ":confounded_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "confounded",
            "face"
        ]
    },
    {
        "codepoints": "😣",
        "name": "persevering face",
        "shortcodes": [
            ":persevering_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "persevere",
            "persevering face"
        ]
    },
    {
        "codepoints": "😞",
        "name": "disappointed face",
        "shortcodes": [
            ":disappointed_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "disappointed",
            "face"
        ]
    },
    {
        "codepoints": "😓",
        "name": "downcast face with sweat",
        "shortcodes": [
            ":downcast_face_with_sweat:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cold",
            "downcast face with sweat",
            "face",
            "sweat"
        ]
    },
    {
        "codepoints": "😩",
        "name": "weary face",
        "shortcodes": [
            ":weary_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "tired",
            "weary"
        ]
    },
    {
        "codepoints": "😫",
        "name": "tired face",
        "shortcodes": [
            ":tired_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "tired"
        ]
    },
    {
        "codepoints": "🥱",
        "name": "yawning face",
        "shortcodes": [
            ":yawning_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "bored",
            "tired",
            "yawn",
            "yawning face"
        ]
    },
    {
        "codepoints": "😤",
        "name": "face with steam from nose",
        "shortcodes": [
            ":face_with_steam_from_nose:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "face with steam from nose",
            "triumph",
            "won",
            "angry",
            "frustration"
        ]
    },
    {
        "codepoints": "😡",
        "name": "enraged face",
        "shortcodes": [
            ":enraged_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "angry",
            "enraged",
            "face",
            "mad",
            "pouting",
            "rage",
            "red"
        ]
    },
    {
        "codepoints": "😠",
        "name": "angry face",
        "shortcodes": [
            ":angry_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "anger",
            "angry",
            "face",
            "mad"
        ]
    },
    {
        "codepoints": "🤬",
        "name": "face with symbols on mouth",
        "shortcodes": [
            ":face_with_symbols_on_mouth:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face with symbols on mouth",
            "swearing"
        ]
    },
    {
        "codepoints": "😈",
        "name": "smiling face with horns",
        "shortcodes": [
            ":smiling_face_with_horns:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "devil",
            "face",
            "fantasy",
            "horns",
            "smile",
            "smiling face with horns",
            "fairy tale"
        ]
    },
    {
        "codepoints": "👿",
        "name": "angry face with horns",
        "shortcodes": [
            ":angry_face_with_horns:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "angry face with horns",
            "demon",
            "devil",
            "face",
            "fantasy",
            "imp"
        ]
    },
    {
        "codepoints": "💀",
        "name": "skull",
        "shortcodes": [
            ":skull:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "death",
            "face",
            "fairy tale",
            "monster",
            "skull"
        ]
    },
    {
        "codepoints": "☠️",
        "name": "skull and crossbones",
        "shortcodes": [
            ":skull_and_crossbones:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "crossbones",
            "death",
            "face",
            "monster",
            "skull",
            "skull and crossbones"
        ]
    },
    {
        "codepoints": "💩",
        "name": "pile of poo",
        "shortcodes": [
            ":pile_of_poo:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "dung",
            "face",
            "monster",
            "pile of poo",
            "poo",
            "poop"
        ]
    },
    {
        "codepoints": "🤡",
        "name": "clown face",
        "shortcodes": [
            ":clown_face:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "clown",
            "face"
        ]
    },
    {
        "codepoints": "👹",
        "name": "ogre",
        "shortcodes": [
            ":ogre:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "creature",
            "face",
            "fairy tale",
            "fantasy",
            "monster",
            "ogre"
        ]
    },
    {
        "codepoints": "👺",
        "name": "goblin",
        "shortcodes": [
            ":goblin:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "creature",
            "face",
            "fairy tale",
            "fantasy",
            "goblin",
            "monster"
        ]
    },
    {
        "codepoints": "👻",
        "name": "ghost",
        "shortcodes": [
            ":ghost:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "creature",
            "face",
            "fairy tale",
            "fantasy",
            "ghost",
            "monster"
        ]
    },
    {
        "codepoints": "👽",
        "name": "alien",
        "shortcodes": [
            ":alien:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "alien",
            "creature",
            "extraterrestrial",
            "face",
            "fantasy",
            "ufo"
        ]
    },
    {
        "codepoints": "👾",
        "name": "alien monster",
        "shortcodes": [
            ":alien_monster:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "alien",
            "creature",
            "extraterrestrial",
            "face",
            "monster",
            "ufo"
        ]
    },
    {
        "codepoints": "🤖",
        "name": "robot",
        "shortcodes": [
            ":robot:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "face",
            "monster",
            "robot"
        ]
    },
    {
        "codepoints": "😺",
        "name": "grinning cat",
        "shortcodes": [
            ":grinning_cat:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "face",
            "grinning",
            "mouth",
            "open",
            "smile"
        ]
    },
    {
        "codepoints": "😸",
        "name": "grinning cat with smiling eyes",
        "shortcodes": [
            ":grinning_cat_with_smiling_eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "eye",
            "face",
            "grin",
            "grinning cat with smiling eyes",
            "smile"
        ]
    },
    {
        "codepoints": "😹",
        "name": "cat with tears of joy",
        "shortcodes": [
            ":cat_with_tears_of_joy:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "cat with tears of joy",
            "face",
            "joy",
            "tear"
        ]
    },
    {
        "codepoints": "😻",
        "name": "smiling cat with heart-eyes",
        "shortcodes": [
            ":smiling_cat_with_heart-eyes:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "eye",
            "face",
            "heart",
            "love",
            "smile",
            "smiling cat with heart-eyes",
            "smiling cat face with heart eyes",
            "smiling cat face with heart-eyes"
        ]
    },
    {
        "codepoints": "😼",
        "name": "cat with wry smile",
        "shortcodes": [
            ":cat_with_wry_smile:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "cat with wry smile",
            "face",
            "ironic",
            "smile",
            "wry"
        ]
    },
    {
        "codepoints": "😽",
        "name": "kissing cat",
        "shortcodes": [
            ":kissing_cat:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "eye",
            "face",
            "kiss",
            "kissing cat"
        ]
    },
    {
        "codepoints": "🙀",
        "name": "weary cat",
        "shortcodes": [
            ":weary_cat:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "face",
            "oh",
            "surprised",
            "weary"
        ]
    },
    {
        "codepoints": "😿",
        "name": "crying cat",
        "shortcodes": [
            ":crying_cat:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "cry",
            "crying cat",
            "face",
            "sad",
            "tear"
        ]
    },
    {
        "codepoints": "😾",
        "name": "pouting cat",
        "shortcodes": [
            ":pouting_cat:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "cat",
            "face",
            "pouting"
        ]
    },
    {
        "codepoints": "🙈",
        "name": "see-no-evil monkey",
        "shortcodes": [
            ":see-no-evil_monkey:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "evil",
            "face",
            "forbidden",
            "monkey",
            "see",
            "see-no-evil monkey"
        ]
    },
    {
        "codepoints": "🙉",
        "name": "hear-no-evil monkey",
        "shortcodes": [
            ":hear-no-evil_monkey:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "evil",
            "face",
            "forbidden",
            "hear",
            "hear-no-evil monkey",
            "monkey"
        ]
    },
    {
        "codepoints": "🙊",
        "name": "speak-no-evil monkey",
        "shortcodes": [
            ":speak-no-evil_monkey:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "evil",
            "face",
            "forbidden",
            "monkey",
            "speak",
            "speak-no-evil monkey"
        ]
    },
    {
        "codepoints": "💋",
        "name": "kiss mark",
        "shortcodes": [
            ":kiss_mark:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "kiss",
            "kiss mark",
            "lips"
        ]
    },
    {
        "codepoints": "💌",
        "name": "love letter",
        "shortcodes": [
            ":love_letter:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "heart",
            "letter",
            "love",
            "mail"
        ]
    },
    {
        "codepoints": "💘",
        "name": "heart with arrow",
        "shortcodes": [
            ":heart_with_arrow:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "arrow",
            "cupid",
            "heart with arrow"
        ]
    },
    {
        "codepoints": "💝",
        "name": "heart with ribbon",
        "shortcodes": [
            ":heart_with_ribbon:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "heart with ribbon",
            "ribbon",
            "valentine"
        ]
    },
    {
        "codepoints": "💖",
        "name": "sparkling heart",
        "shortcodes": [
            ":sparkling_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "excited",
            "sparkle",
            "sparkling heart"
        ]
    },
    {
        "codepoints": "💗",
        "name": "growing heart",
        "shortcodes": [
            ":growing_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "excited",
            "growing",
            "growing heart",
            "nervous",
            "pulse"
        ]
    },
    {
        "codepoints": "💓",
        "name": "beating heart",
        "shortcodes": [
            ":beating_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "beating",
            "beating heart",
            "heartbeat",
            "pulsating"
        ]
    },
    {
        "codepoints": "💞",
        "name": "revolving hearts",
        "shortcodes": [
            ":revolving_hearts:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "revolving",
            "revolving hearts"
        ]
    },
    {
        "codepoints": "💕",
        "name": "two hearts",
        "shortcodes": [
            ":two_hearts:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "love",
            "two hearts"
        ]
    },
    {
        "codepoints": "💟",
        "name": "heart decoration",
        "shortcodes": [
            ":heart_decoration:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "heart",
            "heart decoration"
        ]
    },
    {
        "codepoints": "❣️",
        "name": "heart exclamation",
        "shortcodes": [
            ":heart_exclamation:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "exclamation",
            "heart exclamation",
            "mark",
            "punctuation"
        ]
    },
    {
        "codepoints": "💔",
        "name": "broken heart",
        "shortcodes": [
            ":broken_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "break",
            "broken",
            "broken heart"
        ]
    },
    {
        "codepoints": "❤️‍🔥",
        "name": "heart on fire",
        "shortcodes": [
            ":heart_on_fire:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "burn",
            "heart",
            "heart on fire",
            "love",
            "lust",
            "sacred heart"
        ]
    },
    {
        "codepoints": "❤️‍🩹",
        "name": "mending heart",
        "shortcodes": [
            ":mending_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "healthier",
            "improving",
            "mending",
            "mending heart",
            "recovering",
            "recuperating",
            "well"
        ]
    },
    {
        "codepoints": "❤️",
        "name": "red heart",
        "shortcodes": [
            ":red_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "heart",
            "red heart"
        ]
    },
    {
        "codepoints": "🧡",
        "name": "orange heart",
        "shortcodes": [
            ":orange_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "orange",
            "orange heart"
        ]
    },
    {
        "codepoints": "💛",
        "name": "yellow heart",
        "shortcodes": [
            ":yellow_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "yellow",
            "yellow heart"
        ]
    },
    {
        "codepoints": "💚",
        "name": "green heart",
        "shortcodes": [
            ":green_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "green",
            "green heart"
        ]
    },
    {
        "codepoints": "💙",
        "name": "blue heart",
        "shortcodes": [
            ":blue_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "blue",
            "blue heart"
        ]
    },
    {
        "codepoints": "💜",
        "name": "purple heart",
        "shortcodes": [
            ":purple_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "purple",
            "purple heart"
        ]
    },
    {
        "codepoints": "🤎",
        "name": "brown heart",
        "shortcodes": [
            ":brown_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "brown",
            "heart"
        ]
    },
    {
        "codepoints": "🖤",
        "name": "black heart",
        "shortcodes": [
            ":black_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "black",
            "black heart",
            "evil",
            "wicked"
        ]
    },
    {
        "codepoints": "🤍",
        "name": "white heart",
        "shortcodes": [
            ":white_heart:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "heart",
            "white"
        ]
    },
    {
        "codepoints": "💯",
        "name": "hundred points",
        "shortcodes": [
            ":hundred_points:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "100",
            "full",
            "hundred",
            "hundred points",
            "score"
        ]
    },
    {
        "codepoints": "💢",
        "name": "anger symbol",
        "shortcodes": [
            ":anger_symbol:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "anger symbol",
            "angry",
            "comic",
            "mad"
        ]
    },
    {
        "codepoints": "💥",
        "name": "collision",
        "shortcodes": [
            ":collision:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "boom",
            "collision",
            "comic"
        ]
    },
    {
        "codepoints": "💫",
        "name": "dizzy",
        "shortcodes": [
            ":dizzy:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "comic",
            "dizzy",
            "star"
        ]
    },
    {
        "codepoints": "💦",
        "name": "sweat droplets",
        "shortcodes": [
            ":sweat_droplets:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "comic",
            "splashing",
            "sweat",
            "sweat droplets"
        ]
    },
    {
        "codepoints": "💨",
        "name": "dashing away",
        "shortcodes": [
            ":dashing_away:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "comic",
            "dash",
            "dashing away",
            "running"
        ]
    },
    {
        "codepoints": "🕳️",
        "name": "hole",
        "shortcodes": [
            ":hole:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "hole"
        ]
    },
    {
        "codepoints": "💣",
        "name": "bomb",
        "shortcodes": [
            ":bomb:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "bomb",
            "comic"
        ]
    },
    {
        "codepoints": "💬",
        "name": "speech balloon",
        "shortcodes": [
            ":speech_balloon:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "balloon",
            "bubble",
            "comic",
            "dialog",
            "speech"
        ]
    },
    {
        "codepoints": "👁️‍🗨️",
        "name": "eye in speech bubble",
        "shortcodes": [
            ":eye_in_speech_bubble:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": []
    },
    {
        "codepoints": "🗨️",
        "name": "left speech bubble",
        "shortcodes": [
            ":left_speech_bubble:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "balloon",
            "bubble",
            "dialog",
            "left speech bubble",
            "speech",
            "dialogue"
        ]
    },
    {
        "codepoints": "🗯️",
        "name": "right anger bubble",
        "shortcodes": [
            ":right_anger_bubble:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "angry",
            "balloon",
            "bubble",
            "mad",
            "right anger bubble"
        ]
    },
    {
        "codepoints": "💭",
        "name": "thought balloon",
        "shortcodes": [
            ":thought_balloon:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "balloon",
            "bubble",
            "comic",
            "thought"
        ]
    },
    {
        "codepoints": "💤",
        "name": "ZZZ",
        "shortcodes": [
            ":ZZZ:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [
            "comic",
            "good night",
            "sleep",
            "ZZZ"
        ]
    },
    {
        "codepoints": "👋",
        "name": "waving hand",
        "shortcodes": [
            ":waving_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "wave",
            "waving"
        ]
    },
    {
        "codepoints": "🤚",
        "name": "raised back of hand",
        "shortcodes": [
            ":raised_back_of_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "backhand",
            "raised",
            "raised back of hand"
        ]
    },
    {
        "codepoints": "🖐️",
        "name": "hand with fingers splayed",
        "shortcodes": [
            ":hand_with_fingers_splayed:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "finger",
            "hand",
            "hand with fingers splayed",
            "splayed"
        ]
    },
    {
        "codepoints": "✋",
        "name": "raised hand",
        "shortcodes": [
            ":raised_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "high 5",
            "high five",
            "raised hand"
        ]
    },
    {
        "codepoints": "🖖",
        "name": "vulcan salute",
        "shortcodes": [
            ":vulcan_salute:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "finger",
            "hand",
            "spock",
            "vulcan",
            "Vulcan salute",
            "vulcan salute"
        ]
    },
    {
        "codepoints": "🫱",
        "name": "rightwards hand",
        "shortcodes": [
            ":rightwards_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "right",
            "rightward",
            "rightwards hand",
            "rightwards"
        ]
    },
    {
        "codepoints": "🫲",
        "name": "leftwards hand",
        "shortcodes": [
            ":leftwards_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "left",
            "leftward",
            "leftwards hand",
            "leftwards"
        ]
    },
    {
        "codepoints": "🫳",
        "name": "palm down hand",
        "shortcodes": [
            ":palm_down_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "dismiss",
            "drop",
            "palm down hand",
            "shoo"
        ]
    },
    {
        "codepoints": "🫴",
        "name": "palm up hand",
        "shortcodes": [
            ":palm_up_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "beckon",
            "catch",
            "come",
            "offer",
            "palm up hand"
        ]
    },
    {
        "codepoints": "👌",
        "name": "OK hand",
        "shortcodes": [
            ":OK_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "OK",
            "perfect"
        ]
    },
    {
        "codepoints": "🤌",
        "name": "pinched fingers",
        "shortcodes": [
            ":pinched_fingers:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fingers",
            "hand gesture",
            "interrogation",
            "pinched",
            "sarcastic"
        ]
    },
    {
        "codepoints": "🤏",
        "name": "pinching hand",
        "shortcodes": [
            ":pinching_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "pinching hand",
            "small amount"
        ]
    },
    {
        "codepoints": "✌️",
        "name": "victory hand",
        "shortcodes": [
            ":victory_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "v",
            "victory"
        ]
    },
    {
        "codepoints": "🤞",
        "name": "crossed fingers",
        "shortcodes": [
            ":crossed_fingers:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "cross",
            "crossed fingers",
            "finger",
            "hand",
            "luck",
            "good luck"
        ]
    },
    {
        "codepoints": "🫰",
        "name": "hand with index finger and thumb crossed",
        "shortcodes": [
            ":hand_with_index_finger_and_thumb_crossed:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "expensive",
            "hand with index finger and thumb crossed",
            "heart",
            "love",
            "money",
            "snap"
        ]
    },
    {
        "codepoints": "🤟",
        "name": "love-you gesture",
        "shortcodes": [
            ":love-you_gesture:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "ILY",
            "love-you gesture",
            "love you gesture"
        ]
    },
    {
        "codepoints": "🤘",
        "name": "sign of the horns",
        "shortcodes": [
            ":sign_of_the_horns:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "finger",
            "hand",
            "horns",
            "rock-on",
            "sign of the horns",
            "rock on"
        ]
    },
    {
        "codepoints": "🤙",
        "name": "call me hand",
        "shortcodes": [
            ":call_me_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "call",
            "call me hand",
            "call-me hand",
            "hand",
            "shaka",
            "hang loose",
            "Shaka"
        ]
    },
    {
        "codepoints": "👈",
        "name": "backhand index pointing left",
        "shortcodes": [
            ":backhand_index_pointing_left:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "backhand",
            "backhand index pointing left",
            "finger",
            "hand",
            "index",
            "point"
        ]
    },
    {
        "codepoints": "👉",
        "name": "backhand index pointing right",
        "shortcodes": [
            ":backhand_index_pointing_right:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "backhand",
            "backhand index pointing right",
            "finger",
            "hand",
            "index",
            "point"
        ]
    },
    {
        "codepoints": "👆",
        "name": "backhand index pointing up",
        "shortcodes": [
            ":backhand_index_pointing_up:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "backhand",
            "backhand index pointing up",
            "finger",
            "hand",
            "point",
            "up"
        ]
    },
    {
        "codepoints": "🖕",
        "name": "middle finger",
        "shortcodes": [
            ":middle_finger:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "finger",
            "hand",
            "middle finger"
        ]
    },
    {
        "codepoints": "👇",
        "name": "backhand index pointing down",
        "shortcodes": [
            ":backhand_index_pointing_down:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "backhand",
            "backhand index pointing down",
            "down",
            "finger",
            "hand",
            "point"
        ]
    },
    {
        "codepoints": "☝️",
        "name": "index pointing up",
        "shortcodes": [
            ":index_pointing_up:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "finger",
            "hand",
            "index",
            "index pointing up",
            "point",
            "up"
        ]
    },
    {
        "codepoints": "🫵",
        "name": "index pointing at the viewer",
        "shortcodes": [
            ":index_pointing_at_the_viewer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "index pointing at the viewer",
            "point",
            "you"
        ]
    },
    {
        "codepoints": "👍",
        "name": "thumbs up",
        "shortcodes": [
            ":thumbs_up:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "+1",
            "hand",
            "thumb",
            "thumbs up",
            "up"
        ]
    },
    {
        "codepoints": "👎",
        "name": "thumbs down",
        "shortcodes": [
            ":thumbs_down:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "-1",
            "down",
            "hand",
            "thumb",
            "thumbs down"
        ]
    },
    {
        "codepoints": "✊",
        "name": "raised fist",
        "shortcodes": [
            ":raised_fist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "clenched",
            "fist",
            "hand",
            "punch",
            "raised fist"
        ]
    },
    {
        "codepoints": "👊",
        "name": "oncoming fist",
        "shortcodes": [
            ":oncoming_fist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "clenched",
            "fist",
            "hand",
            "oncoming fist",
            "punch"
        ]
    },
    {
        "codepoints": "🤛",
        "name": "left-facing fist",
        "shortcodes": [
            ":left-facing_fist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fist",
            "left-facing fist",
            "leftwards",
            "leftward"
        ]
    },
    {
        "codepoints": "🤜",
        "name": "right-facing fist",
        "shortcodes": [
            ":right-facing_fist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fist",
            "right-facing fist",
            "rightwards",
            "rightward"
        ]
    },
    {
        "codepoints": "👏",
        "name": "clapping hands",
        "shortcodes": [
            ":clapping_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "clap",
            "clapping hands",
            "hand"
        ]
    },
    {
        "codepoints": "🙌",
        "name": "raising hands",
        "shortcodes": [
            ":raising_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "celebration",
            "gesture",
            "hand",
            "hooray",
            "raised",
            "raising hands",
            "woo hoo",
            "yay"
        ]
    },
    {
        "codepoints": "🫶",
        "name": "heart hands",
        "shortcodes": [
            ":heart_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "heart hands",
            "love"
        ]
    },
    {
        "codepoints": "👐",
        "name": "open hands",
        "shortcodes": [
            ":open_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "open",
            "open hands"
        ]
    },
    {
        "codepoints": "🤲",
        "name": "palms up together",
        "shortcodes": [
            ":palms_up_together:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "palms up together",
            "prayer"
        ]
    },
    {
        "codepoints": "🤝",
        "name": "handshake",
        "shortcodes": [
            ":handshake:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "agreement",
            "hand",
            "handshake",
            "meeting",
            "shake"
        ]
    },
    {
        "codepoints": "🙏",
        "name": "folded hands",
        "shortcodes": [
            ":folded_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "ask",
            "folded hands",
            "hand",
            "high 5",
            "high five",
            "please",
            "pray",
            "thanks"
        ]
    },
    {
        "codepoints": "✍️",
        "name": "writing hand",
        "shortcodes": [
            ":writing_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "write",
            "writing hand"
        ]
    },
    {
        "codepoints": "💅",
        "name": "nail polish",
        "shortcodes": [
            ":nail_polish:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "care",
            "cosmetics",
            "manicure",
            "nail",
            "polish"
        ]
    },
    {
        "codepoints": "🤳",
        "name": "selfie",
        "shortcodes": [
            ":selfie:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "camera",
            "phone",
            "selfie"
        ]
    },
    {
        "codepoints": "💪",
        "name": "flexed biceps",
        "shortcodes": [
            ":flexed_biceps:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "biceps",
            "comic",
            "flex",
            "flexed biceps",
            "muscle"
        ]
    },
    {
        "codepoints": "🦾",
        "name": "mechanical arm",
        "shortcodes": [
            ":mechanical_arm:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "mechanical arm",
            "prosthetic"
        ]
    },
    {
        "codepoints": "🦿",
        "name": "mechanical leg",
        "shortcodes": [
            ":mechanical_leg:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "mechanical leg",
            "prosthetic"
        ]
    },
    {
        "codepoints": "🦵",
        "name": "leg",
        "shortcodes": [
            ":leg:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "kick",
            "leg",
            "limb"
        ]
    },
    {
        "codepoints": "🦶",
        "name": "foot",
        "shortcodes": [
            ":foot:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "foot",
            "kick",
            "stomp"
        ]
    },
    {
        "codepoints": "👂",
        "name": "ear",
        "shortcodes": [
            ":ear:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "body",
            "ear"
        ]
    },
    {
        "codepoints": "🦻",
        "name": "ear with hearing aid",
        "shortcodes": [
            ":ear_with_hearing_aid:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "ear with hearing aid",
            "hard of hearing",
            "hearing impaired"
        ]
    },
    {
        "codepoints": "👃",
        "name": "nose",
        "shortcodes": [
            ":nose:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "body",
            "nose"
        ]
    },
    {
        "codepoints": "🧠",
        "name": "brain",
        "shortcodes": [
            ":brain:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "brain",
            "intelligent"
        ]
    },
    {
        "codepoints": "🫀",
        "name": "anatomical heart",
        "shortcodes": [
            ":anatomical_heart:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "anatomical",
            "cardiology",
            "heart",
            "organ",
            "pulse",
            "anatomical heart"
        ]
    },
    {
        "codepoints": "🫁",
        "name": "lungs",
        "shortcodes": [
            ":lungs:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "breath",
            "exhalation",
            "inhalation",
            "lungs",
            "organ",
            "respiration"
        ]
    },
    {
        "codepoints": "🦷",
        "name": "tooth",
        "shortcodes": [
            ":tooth:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "dentist",
            "tooth"
        ]
    },
    {
        "codepoints": "🦴",
        "name": "bone",
        "shortcodes": [
            ":bone:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bone",
            "skeleton"
        ]
    },
    {
        "codepoints": "👀",
        "name": "eyes",
        "shortcodes": [
            ":eyes:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "eye",
            "eyes",
            "face"
        ]
    },
    {
        "codepoints": "👁️",
        "name": "eye",
        "shortcodes": [
            ":eye:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "body",
            "eye"
        ]
    },
    {
        "codepoints": "👅",
        "name": "tongue",
        "shortcodes": [
            ":tongue:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "body",
            "tongue"
        ]
    },
    {
        "codepoints": "👄",
        "name": "mouth",
        "shortcodes": [
            ":mouth:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "lips",
            "mouth"
        ]
    },
    {
        "codepoints": "🫦",
        "name": "biting lip",
        "shortcodes": [
            ":biting_lip:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "anxious",
            "biting lip",
            "fear",
            "flirting",
            "nervous",
            "uncomfortable",
            "worried"
        ]
    },
    {
        "codepoints": "👶",
        "name": "baby",
        "shortcodes": [
            ":baby:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "baby",
            "young"
        ]
    },
    {
        "codepoints": "🧒",
        "name": "child",
        "shortcodes": [
            ":child:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "child",
            "gender-neutral",
            "unspecified gender",
            "young"
        ]
    },
    {
        "codepoints": "👦",
        "name": "boy",
        "shortcodes": [
            ":boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "young",
            "young person"
        ]
    },
    {
        "codepoints": "👧",
        "name": "girl",
        "shortcodes": [
            ":girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "girl",
            "Virgo",
            "young person",
            "zodiac",
            "young"
        ]
    },
    {
        "codepoints": "🧑",
        "name": "person",
        "shortcodes": [
            ":person:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "gender-neutral",
            "person",
            "unspecified gender"
        ]
    },
    {
        "codepoints": "👱",
        "name": "person: blond hair",
        "shortcodes": [
            ":person:_blond_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "blond",
            "blond-haired person",
            "hair",
            "person: blond hair"
        ]
    },
    {
        "codepoints": "👨",
        "name": "man",
        "shortcodes": [
            ":man:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "man"
        ]
    },
    {
        "codepoints": "🧔",
        "name": "person: beard",
        "shortcodes": [
            ":person:_beard:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "beard",
            "person",
            "person: beard"
        ]
    },
    {
        "codepoints": "🧔‍♂️",
        "name": "man: beard",
        "shortcodes": [
            ":man:_beard:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "beard",
            "man",
            "man: beard"
        ]
    },
    {
        "codepoints": "🧔‍♀️",
        "name": "woman: beard",
        "shortcodes": [
            ":woman:_beard:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "beard",
            "woman",
            "woman: beard"
        ]
    },
    {
        "codepoints": "👨‍🦰",
        "name": "man: red hair",
        "shortcodes": [
            ":man:_red_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "man",
            "red hair"
        ]
    },
    {
        "codepoints": "👨‍🦱",
        "name": "man: curly hair",
        "shortcodes": [
            ":man:_curly_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "curly hair",
            "man"
        ]
    },
    {
        "codepoints": "👨‍🦳",
        "name": "man: white hair",
        "shortcodes": [
            ":man:_white_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "man",
            "white hair"
        ]
    },
    {
        "codepoints": "👨‍🦲",
        "name": "man: bald",
        "shortcodes": [
            ":man:_bald:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "bald",
            "man"
        ]
    },
    {
        "codepoints": "👩",
        "name": "woman",
        "shortcodes": [
            ":woman:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍🦰",
        "name": "woman: red hair",
        "shortcodes": [
            ":woman:_red_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "red hair",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🦰",
        "name": "person: red hair",
        "shortcodes": [
            ":person:_red_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "gender-neutral",
            "person",
            "red hair",
            "unspecified gender"
        ]
    },
    {
        "codepoints": "👩‍🦱",
        "name": "woman: curly hair",
        "shortcodes": [
            ":woman:_curly_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "curly hair",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🦱",
        "name": "person: curly hair",
        "shortcodes": [
            ":person:_curly_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "curly hair",
            "gender-neutral",
            "person",
            "unspecified gender"
        ]
    },
    {
        "codepoints": "👩‍🦳",
        "name": "woman: white hair",
        "shortcodes": [
            ":woman:_white_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "white hair",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🦳",
        "name": "person: white hair",
        "shortcodes": [
            ":person:_white_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "gender-neutral",
            "person",
            "unspecified gender",
            "white hair"
        ]
    },
    {
        "codepoints": "👩‍🦲",
        "name": "woman: bald",
        "shortcodes": [
            ":woman:_bald:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "bald",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🦲",
        "name": "person: bald",
        "shortcodes": [
            ":person:_bald:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "bald",
            "gender-neutral",
            "person",
            "unspecified gender"
        ]
    },
    {
        "codepoints": "👱‍♀️",
        "name": "woman: blond hair",
        "shortcodes": [
            ":woman:_blond_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "blond-haired woman",
            "blonde",
            "hair",
            "woman",
            "woman: blond hair"
        ]
    },
    {
        "codepoints": "👱‍♂️",
        "name": "man: blond hair",
        "shortcodes": [
            ":man:_blond_hair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "blond",
            "blond-haired man",
            "hair",
            "man",
            "man: blond hair"
        ]
    },
    {
        "codepoints": "🧓",
        "name": "older person",
        "shortcodes": [
            ":older_person:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "gender-neutral",
            "old",
            "older person",
            "unspecified gender"
        ]
    },
    {
        "codepoints": "👴",
        "name": "old man",
        "shortcodes": [
            ":old_man:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "man",
            "old"
        ]
    },
    {
        "codepoints": "👵",
        "name": "old woman",
        "shortcodes": [
            ":old_woman:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "adult",
            "old",
            "woman"
        ]
    },
    {
        "codepoints": "🙍",
        "name": "person frowning",
        "shortcodes": [
            ":person_frowning:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "frown",
            "gesture",
            "person frowning"
        ]
    },
    {
        "codepoints": "🙍‍♂️",
        "name": "man frowning",
        "shortcodes": [
            ":man_frowning:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "frowning",
            "gesture",
            "man"
        ]
    },
    {
        "codepoints": "🙍‍♀️",
        "name": "woman frowning",
        "shortcodes": [
            ":woman_frowning:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "frowning",
            "gesture",
            "woman"
        ]
    },
    {
        "codepoints": "🙎",
        "name": "person pouting",
        "shortcodes": [
            ":person_pouting:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "person pouting",
            "pouting"
        ]
    },
    {
        "codepoints": "🙎‍♂️",
        "name": "man pouting",
        "shortcodes": [
            ":man_pouting:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "man",
            "pouting"
        ]
    },
    {
        "codepoints": "🙎‍♀️",
        "name": "woman pouting",
        "shortcodes": [
            ":woman_pouting:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "pouting",
            "woman"
        ]
    },
    {
        "codepoints": "🙅",
        "name": "person gesturing NO",
        "shortcodes": [
            ":person_gesturing_NO:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "forbidden",
            "gesture",
            "hand",
            "person gesturing NO",
            "prohibited"
        ]
    },
    {
        "codepoints": "🙅‍♂️",
        "name": "man gesturing NO",
        "shortcodes": [
            ":man_gesturing_NO:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "forbidden",
            "gesture",
            "hand",
            "man",
            "man gesturing NO",
            "prohibited"
        ]
    },
    {
        "codepoints": "🙅‍♀️",
        "name": "woman gesturing NO",
        "shortcodes": [
            ":woman_gesturing_NO:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "forbidden",
            "gesture",
            "hand",
            "prohibited",
            "woman",
            "woman gesturing NO"
        ]
    },
    {
        "codepoints": "🙆",
        "name": "person gesturing OK",
        "shortcodes": [
            ":person_gesturing_OK:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "hand",
            "OK",
            "person gesturing OK"
        ]
    },
    {
        "codepoints": "🙆‍♂️",
        "name": "man gesturing OK",
        "shortcodes": [
            ":man_gesturing_OK:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "hand",
            "man",
            "man gesturing OK",
            "OK"
        ]
    },
    {
        "codepoints": "🙆‍♀️",
        "name": "woman gesturing OK",
        "shortcodes": [
            ":woman_gesturing_OK:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "hand",
            "OK",
            "woman",
            "woman gesturing OK"
        ]
    },
    {
        "codepoints": "💁",
        "name": "person tipping hand",
        "shortcodes": [
            ":person_tipping_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hand",
            "help",
            "information",
            "person tipping hand",
            "sassy",
            "tipping"
        ]
    },
    {
        "codepoints": "💁‍♂️",
        "name": "man tipping hand",
        "shortcodes": [
            ":man_tipping_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "man tipping hand",
            "sassy",
            "tipping hand"
        ]
    },
    {
        "codepoints": "💁‍♀️",
        "name": "woman tipping hand",
        "shortcodes": [
            ":woman_tipping_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "sassy",
            "tipping hand",
            "woman",
            "woman tipping hand"
        ]
    },
    {
        "codepoints": "🙋",
        "name": "person raising hand",
        "shortcodes": [
            ":person_raising_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "hand",
            "happy",
            "person raising hand",
            "raised"
        ]
    },
    {
        "codepoints": "🙋‍♂️",
        "name": "man raising hand",
        "shortcodes": [
            ":man_raising_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "man",
            "man raising hand",
            "raising hand"
        ]
    },
    {
        "codepoints": "🙋‍♀️",
        "name": "woman raising hand",
        "shortcodes": [
            ":woman_raising_hand:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "gesture",
            "raising hand",
            "woman",
            "woman raising hand"
        ]
    },
    {
        "codepoints": "🧏",
        "name": "deaf person",
        "shortcodes": [
            ":deaf_person:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "deaf",
            "deaf person",
            "ear",
            "hear",
            "hearing impaired"
        ]
    },
    {
        "codepoints": "🧏‍♂️",
        "name": "deaf man",
        "shortcodes": [
            ":deaf_man:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "deaf",
            "man"
        ]
    },
    {
        "codepoints": "🧏‍♀️",
        "name": "deaf woman",
        "shortcodes": [
            ":deaf_woman:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "deaf",
            "woman"
        ]
    },
    {
        "codepoints": "🙇",
        "name": "person bowing",
        "shortcodes": [
            ":person_bowing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "apology",
            "bow",
            "gesture",
            "person bowing",
            "sorry"
        ]
    },
    {
        "codepoints": "🙇‍♂️",
        "name": "man bowing",
        "shortcodes": [
            ":man_bowing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "apology",
            "bowing",
            "favor",
            "gesture",
            "man",
            "sorry"
        ]
    },
    {
        "codepoints": "🙇‍♀️",
        "name": "woman bowing",
        "shortcodes": [
            ":woman_bowing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "apology",
            "bowing",
            "favor",
            "gesture",
            "sorry",
            "woman"
        ]
    },
    {
        "codepoints": "🤦",
        "name": "person facepalming",
        "shortcodes": [
            ":person_facepalming:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "disbelief",
            "exasperation",
            "face",
            "palm",
            "person facepalming"
        ]
    },
    {
        "codepoints": "🤦‍♂️",
        "name": "man facepalming",
        "shortcodes": [
            ":man_facepalming:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "disbelief",
            "exasperation",
            "facepalm",
            "man",
            "man facepalming"
        ]
    },
    {
        "codepoints": "🤦‍♀️",
        "name": "woman facepalming",
        "shortcodes": [
            ":woman_facepalming:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "disbelief",
            "exasperation",
            "facepalm",
            "woman",
            "woman facepalming"
        ]
    },
    {
        "codepoints": "🤷",
        "name": "person shrugging",
        "shortcodes": [
            ":person_shrugging:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "doubt",
            "ignorance",
            "indifference",
            "person shrugging",
            "shrug"
        ]
    },
    {
        "codepoints": "🤷‍♂️",
        "name": "man shrugging",
        "shortcodes": [
            ":man_shrugging:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "doubt",
            "ignorance",
            "indifference",
            "man",
            "man shrugging",
            "shrug"
        ]
    },
    {
        "codepoints": "🤷‍♀️",
        "name": "woman shrugging",
        "shortcodes": [
            ":woman_shrugging:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "doubt",
            "ignorance",
            "indifference",
            "shrug",
            "woman",
            "woman shrugging"
        ]
    },
    {
        "codepoints": "🧑‍⚕️",
        "name": "health worker",
        "shortcodes": [
            ":health_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "doctor",
            "health worker",
            "healthcare",
            "nurse",
            "therapist",
            "care",
            "health"
        ]
    },
    {
        "codepoints": "👨‍⚕️",
        "name": "man health worker",
        "shortcodes": [
            ":man_health_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "doctor",
            "healthcare",
            "man",
            "man health worker",
            "nurse",
            "therapist",
            "health care"
        ]
    },
    {
        "codepoints": "👩‍⚕️",
        "name": "woman health worker",
        "shortcodes": [
            ":woman_health_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "doctor",
            "healthcare",
            "nurse",
            "therapist",
            "woman",
            "woman health worker",
            "health care"
        ]
    },
    {
        "codepoints": "🧑‍🎓",
        "name": "student",
        "shortcodes": [
            ":student:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "graduate",
            "student"
        ]
    },
    {
        "codepoints": "👨‍🎓",
        "name": "man student",
        "shortcodes": [
            ":man_student:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "graduate",
            "man",
            "student"
        ]
    },
    {
        "codepoints": "👩‍🎓",
        "name": "woman student",
        "shortcodes": [
            ":woman_student:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "graduate",
            "student",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🏫",
        "name": "teacher",
        "shortcodes": [
            ":teacher:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "instructor",
            "professor",
            "teacher",
            "lecturer"
        ]
    },
    {
        "codepoints": "👨‍🏫",
        "name": "man teacher",
        "shortcodes": [
            ":man_teacher:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "instructor",
            "man",
            "professor",
            "teacher"
        ]
    },
    {
        "codepoints": "👩‍🏫",
        "name": "woman teacher",
        "shortcodes": [
            ":woman_teacher:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "instructor",
            "professor",
            "teacher",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍⚖️",
        "name": "judge",
        "shortcodes": [
            ":judge:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "judge",
            "justice",
            "scales",
            "law"
        ]
    },
    {
        "codepoints": "👨‍⚖️",
        "name": "man judge",
        "shortcodes": [
            ":man_judge:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "judge",
            "justice",
            "man",
            "scales"
        ]
    },
    {
        "codepoints": "👩‍⚖️",
        "name": "woman judge",
        "shortcodes": [
            ":woman_judge:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "judge",
            "justice",
            "scales",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🌾",
        "name": "farmer",
        "shortcodes": [
            ":farmer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "farmer",
            "gardener",
            "rancher"
        ]
    },
    {
        "codepoints": "👨‍🌾",
        "name": "man farmer",
        "shortcodes": [
            ":man_farmer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "farmer",
            "gardener",
            "man",
            "rancher"
        ]
    },
    {
        "codepoints": "👩‍🌾",
        "name": "woman farmer",
        "shortcodes": [
            ":woman_farmer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "farmer",
            "gardener",
            "rancher",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🍳",
        "name": "cook",
        "shortcodes": [
            ":cook:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "chef",
            "cook"
        ]
    },
    {
        "codepoints": "👨‍🍳",
        "name": "man cook",
        "shortcodes": [
            ":man_cook:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "chef",
            "cook",
            "man"
        ]
    },
    {
        "codepoints": "👩‍🍳",
        "name": "woman cook",
        "shortcodes": [
            ":woman_cook:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "chef",
            "cook",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🔧",
        "name": "mechanic",
        "shortcodes": [
            ":mechanic:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "electrician",
            "mechanic",
            "plumber",
            "tradesperson",
            "tradie"
        ]
    },
    {
        "codepoints": "👨‍🔧",
        "name": "man mechanic",
        "shortcodes": [
            ":man_mechanic:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "electrician",
            "man",
            "mechanic",
            "plumber",
            "tradesperson"
        ]
    },
    {
        "codepoints": "👩‍🔧",
        "name": "woman mechanic",
        "shortcodes": [
            ":woman_mechanic:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "electrician",
            "mechanic",
            "plumber",
            "tradesperson",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🏭",
        "name": "factory worker",
        "shortcodes": [
            ":factory_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "assembly",
            "factory",
            "industrial",
            "worker"
        ]
    },
    {
        "codepoints": "👨‍🏭",
        "name": "man factory worker",
        "shortcodes": [
            ":man_factory_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "assembly",
            "factory",
            "industrial",
            "man",
            "worker"
        ]
    },
    {
        "codepoints": "👩‍🏭",
        "name": "woman factory worker",
        "shortcodes": [
            ":woman_factory_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "assembly",
            "factory",
            "industrial",
            "woman",
            "worker"
        ]
    },
    {
        "codepoints": "🧑‍💼",
        "name": "office worker",
        "shortcodes": [
            ":office_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "architect",
            "business",
            "manager",
            "office worker",
            "white-collar"
        ]
    },
    {
        "codepoints": "👨‍💼",
        "name": "man office worker",
        "shortcodes": [
            ":man_office_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "business man",
            "man office worker",
            "manager",
            "office worker",
            "white collar",
            "architect",
            "business",
            "man",
            "white-collar"
        ]
    },
    {
        "codepoints": "👩‍💼",
        "name": "woman office worker",
        "shortcodes": [
            ":woman_office_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "business woman",
            "manager",
            "office worker",
            "white collar",
            "woman office worker",
            "architect",
            "business",
            "white-collar",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🔬",
        "name": "scientist",
        "shortcodes": [
            ":scientist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "biologist",
            "chemist",
            "engineer",
            "physicist",
            "scientist"
        ]
    },
    {
        "codepoints": "👨‍🔬",
        "name": "man scientist",
        "shortcodes": [
            ":man_scientist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "biologist",
            "chemist",
            "engineer",
            "man",
            "physicist",
            "scientist"
        ]
    },
    {
        "codepoints": "👩‍🔬",
        "name": "woman scientist",
        "shortcodes": [
            ":woman_scientist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "biologist",
            "chemist",
            "engineer",
            "physicist",
            "scientist",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍💻",
        "name": "technologist",
        "shortcodes": [
            ":technologist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "coder",
            "developer",
            "inventor",
            "software",
            "technologist"
        ]
    },
    {
        "codepoints": "👨‍💻",
        "name": "man technologist",
        "shortcodes": [
            ":man_technologist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "coder",
            "developer",
            "inventor",
            "man",
            "software",
            "technologist"
        ]
    },
    {
        "codepoints": "👩‍💻",
        "name": "woman technologist",
        "shortcodes": [
            ":woman_technologist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "coder",
            "developer",
            "inventor",
            "software",
            "technologist",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🎤",
        "name": "singer",
        "shortcodes": [
            ":singer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "actor",
            "entertainer",
            "rock",
            "singer",
            "star"
        ]
    },
    {
        "codepoints": "👨‍🎤",
        "name": "man singer",
        "shortcodes": [
            ":man_singer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "entertainer",
            "man",
            "man singer",
            "performer",
            "rock singer",
            "star",
            "actor",
            "rock",
            "singer"
        ]
    },
    {
        "codepoints": "👩‍🎤",
        "name": "woman singer",
        "shortcodes": [
            ":woman_singer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "entertainer",
            "performer",
            "rock singer",
            "star",
            "woman",
            "woman singer",
            "actor",
            "rock",
            "singer"
        ]
    },
    {
        "codepoints": "🧑‍🎨",
        "name": "artist",
        "shortcodes": [
            ":artist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "artist",
            "palette"
        ]
    },
    {
        "codepoints": "👨‍🎨",
        "name": "man artist",
        "shortcodes": [
            ":man_artist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "artist",
            "man",
            "painter",
            "palette"
        ]
    },
    {
        "codepoints": "👩‍🎨",
        "name": "woman artist",
        "shortcodes": [
            ":woman_artist:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "artist",
            "painter",
            "palette",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍✈️",
        "name": "pilot",
        "shortcodes": [
            ":pilot:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "pilot",
            "plane"
        ]
    },
    {
        "codepoints": "👨‍✈️",
        "name": "man pilot",
        "shortcodes": [
            ":man_pilot:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "pilot",
            "plane"
        ]
    },
    {
        "codepoints": "👩‍✈️",
        "name": "woman pilot",
        "shortcodes": [
            ":woman_pilot:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "pilot",
            "plane",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🚀",
        "name": "astronaut",
        "shortcodes": [
            ":astronaut:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "astronaut",
            "rocket"
        ]
    },
    {
        "codepoints": "👨‍🚀",
        "name": "man astronaut",
        "shortcodes": [
            ":man_astronaut:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "astronaut",
            "man",
            "rocket"
        ]
    },
    {
        "codepoints": "👩‍🚀",
        "name": "woman astronaut",
        "shortcodes": [
            ":woman_astronaut:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "astronaut",
            "rocket",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🚒",
        "name": "firefighter",
        "shortcodes": [
            ":firefighter:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "firefighter",
            "firetruck",
            "engine",
            "fire",
            "truck",
            "fire engine",
            "fire truck"
        ]
    },
    {
        "codepoints": "👨‍🚒",
        "name": "man firefighter",
        "shortcodes": [
            ":man_firefighter:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fire truck",
            "firefighter",
            "man",
            "firetruck",
            "fireman"
        ]
    },
    {
        "codepoints": "👩‍🚒",
        "name": "woman firefighter",
        "shortcodes": [
            ":woman_firefighter:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fire truck",
            "firefighter",
            "woman",
            "firetruck",
            "engine",
            "fire",
            "firewoman",
            "truck"
        ]
    },
    {
        "codepoints": "👮",
        "name": "police officer",
        "shortcodes": [
            ":police_officer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "cop",
            "officer",
            "police"
        ]
    },
    {
        "codepoints": "👮‍♂️",
        "name": "man police officer",
        "shortcodes": [
            ":man_police_officer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "cop",
            "man",
            "officer",
            "police"
        ]
    },
    {
        "codepoints": "👮‍♀️",
        "name": "woman police officer",
        "shortcodes": [
            ":woman_police_officer:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "cop",
            "officer",
            "police",
            "woman"
        ]
    },
    {
        "codepoints": "🕵️",
        "name": "detective",
        "shortcodes": [
            ":detective:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "detective",
            "investigator",
            "sleuth",
            "spy"
        ]
    },
    {
        "codepoints": "🕵️‍♂️",
        "name": "man detective",
        "shortcodes": [
            ":man_detective:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": []
    },
    {
        "codepoints": "🕵️‍♀️",
        "name": "woman detective",
        "shortcodes": [
            ":woman_detective:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": []
    },
    {
        "codepoints": "💂",
        "name": "guard",
        "shortcodes": [
            ":guard:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "guard"
        ]
    },
    {
        "codepoints": "💂‍♂️",
        "name": "man guard",
        "shortcodes": [
            ":man_guard:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "guard",
            "man"
        ]
    },
    {
        "codepoints": "💂‍♀️",
        "name": "woman guard",
        "shortcodes": [
            ":woman_guard:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "guard",
            "woman"
        ]
    },
    {
        "codepoints": "🥷",
        "name": "ninja",
        "shortcodes": [
            ":ninja:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fighter",
            "hidden",
            "ninja",
            "stealth"
        ]
    },
    {
        "codepoints": "👷",
        "name": "construction worker",
        "shortcodes": [
            ":construction_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "construction",
            "hat",
            "worker"
        ]
    },
    {
        "codepoints": "👷‍♂️",
        "name": "man construction worker",
        "shortcodes": [
            ":man_construction_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "construction",
            "man",
            "worker"
        ]
    },
    {
        "codepoints": "👷‍♀️",
        "name": "woman construction worker",
        "shortcodes": [
            ":woman_construction_worker:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "construction",
            "woman",
            "worker"
        ]
    },
    {
        "codepoints": "🫅",
        "name": "person with crown",
        "shortcodes": [
            ":person_with_crown:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "monarch",
            "noble",
            "person with crown",
            "regal",
            "royalty"
        ]
    },
    {
        "codepoints": "🤴",
        "name": "prince",
        "shortcodes": [
            ":prince:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "prince"
        ]
    },
    {
        "codepoints": "👸",
        "name": "princess",
        "shortcodes": [
            ":princess:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fairy tale",
            "fantasy",
            "princess"
        ]
    },
    {
        "codepoints": "👳",
        "name": "person wearing turban",
        "shortcodes": [
            ":person_wearing_turban:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "person wearing turban",
            "turban"
        ]
    },
    {
        "codepoints": "👳‍♂️",
        "name": "man wearing turban",
        "shortcodes": [
            ":man_wearing_turban:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "man wearing turban",
            "turban"
        ]
    },
    {
        "codepoints": "👳‍♀️",
        "name": "woman wearing turban",
        "shortcodes": [
            ":woman_wearing_turban:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "turban",
            "woman",
            "woman wearing turban"
        ]
    },
    {
        "codepoints": "👲",
        "name": "person with skullcap",
        "shortcodes": [
            ":person_with_skullcap:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "cap",
            "gua pi mao",
            "hat",
            "person",
            "person with skullcap",
            "skullcap"
        ]
    },
    {
        "codepoints": "🧕",
        "name": "woman with headscarf",
        "shortcodes": [
            ":woman_with_headscarf:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "headscarf",
            "hijab",
            "mantilla",
            "tichel",
            "woman with headscarf"
        ]
    },
    {
        "codepoints": "🤵",
        "name": "person in tuxedo",
        "shortcodes": [
            ":person_in_tuxedo:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "groom",
            "person",
            "person in tux",
            "person in tuxedo",
            "tuxedo"
        ]
    },
    {
        "codepoints": "🤵‍♂️",
        "name": "man in tuxedo",
        "shortcodes": [
            ":man_in_tuxedo:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "man in tux",
            "man in tuxedo",
            "tux",
            "tuxedo"
        ]
    },
    {
        "codepoints": "🤵‍♀️",
        "name": "woman in tuxedo",
        "shortcodes": [
            ":woman_in_tuxedo:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "tuxedo",
            "woman",
            "woman in tux",
            "woman in tuxedo"
        ]
    },
    {
        "codepoints": "👰",
        "name": "person with veil",
        "shortcodes": [
            ":person_with_veil:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bride",
            "person",
            "person with veil",
            "veil",
            "wedding"
        ]
    },
    {
        "codepoints": "👰‍♂️",
        "name": "man with veil",
        "shortcodes": [
            ":man_with_veil:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "man with veil",
            "veil"
        ]
    },
    {
        "codepoints": "👰‍♀️",
        "name": "woman with veil",
        "shortcodes": [
            ":woman_with_veil:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bride",
            "veil",
            "woman",
            "woman with veil"
        ]
    },
    {
        "codepoints": "🤰",
        "name": "pregnant woman",
        "shortcodes": [
            ":pregnant_woman:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "pregnant",
            "woman"
        ]
    },
    {
        "codepoints": "🫃",
        "name": "pregnant man",
        "shortcodes": [
            ":pregnant_man:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "belly",
            "bloated",
            "full",
            "pregnant",
            "pregnant man"
        ]
    },
    {
        "codepoints": "🫄",
        "name": "pregnant person",
        "shortcodes": [
            ":pregnant_person:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "belly",
            "bloated",
            "full",
            "pregnant",
            "pregnant person"
        ]
    },
    {
        "codepoints": "🤱",
        "name": "breast-feeding",
        "shortcodes": [
            ":breast-feeding:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "baby",
            "breast",
            "breast-feeding",
            "nursing"
        ]
    },
    {
        "codepoints": "👩‍🍼",
        "name": "woman feeding baby",
        "shortcodes": [
            ":woman_feeding_baby:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "baby",
            "feeding",
            "nursing",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍🍼",
        "name": "man feeding baby",
        "shortcodes": [
            ":man_feeding_baby:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "baby",
            "feeding",
            "man",
            "nursing"
        ]
    },
    {
        "codepoints": "🧑‍🍼",
        "name": "person feeding baby",
        "shortcodes": [
            ":person_feeding_baby:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "baby",
            "feeding",
            "nursing",
            "person"
        ]
    },
    {
        "codepoints": "👼",
        "name": "baby angel",
        "shortcodes": [
            ":baby_angel:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "angel",
            "baby",
            "face",
            "fairy tale",
            "fantasy"
        ]
    },
    {
        "codepoints": "🎅",
        "name": "Santa Claus",
        "shortcodes": [
            ":Santa_Claus:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "celebration",
            "Christmas",
            "Father Christmas",
            "Santa",
            "Santa Claus",
            "claus",
            "father",
            "santa",
            "Claus",
            "Father"
        ]
    },
    {
        "codepoints": "🤶",
        "name": "Mrs. Claus",
        "shortcodes": [
            ":Mrs._Claus:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "celebration",
            "Christmas",
            "Mrs Claus",
            "Mrs Santa Claus",
            "Mrs. Claus",
            "claus",
            "mother",
            "Mrs.",
            "Claus",
            "Mother"
        ]
    },
    {
        "codepoints": "🧑‍🎄",
        "name": "mx claus",
        "shortcodes": [
            ":mx_claus:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "Claus, christmas",
            "mx claus",
            "Claus, Christmas",
            "Mx. Claus"
        ]
    },
    {
        "codepoints": "🦸",
        "name": "superhero",
        "shortcodes": [
            ":superhero:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "good",
            "hero",
            "heroine",
            "superhero",
            "superpower"
        ]
    },
    {
        "codepoints": "🦸‍♂️",
        "name": "man superhero",
        "shortcodes": [
            ":man_superhero:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "good",
            "hero",
            "man",
            "man superhero",
            "superpower"
        ]
    },
    {
        "codepoints": "🦸‍♀️",
        "name": "woman superhero",
        "shortcodes": [
            ":woman_superhero:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "good",
            "hero",
            "heroine",
            "superpower",
            "woman",
            "woman superhero"
        ]
    },
    {
        "codepoints": "🦹",
        "name": "supervillain",
        "shortcodes": [
            ":supervillain:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "criminal",
            "evil",
            "superpower",
            "supervillain",
            "villain"
        ]
    },
    {
        "codepoints": "🦹‍♂️",
        "name": "man supervillain",
        "shortcodes": [
            ":man_supervillain:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "criminal",
            "evil",
            "man",
            "man supervillain",
            "superpower",
            "villain"
        ]
    },
    {
        "codepoints": "🦹‍♀️",
        "name": "woman supervillain",
        "shortcodes": [
            ":woman_supervillain:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "criminal",
            "evil",
            "superpower",
            "villain",
            "woman",
            "woman supervillain"
        ]
    },
    {
        "codepoints": "🧙",
        "name": "mage",
        "shortcodes": [
            ":mage:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "mage",
            "sorcerer",
            "sorceress",
            "witch",
            "wizard"
        ]
    },
    {
        "codepoints": "🧙‍♂️",
        "name": "man mage",
        "shortcodes": [
            ":man_mage:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man mage",
            "sorcerer",
            "wizard"
        ]
    },
    {
        "codepoints": "🧙‍♀️",
        "name": "woman mage",
        "shortcodes": [
            ":woman_mage:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "sorceress",
            "witch",
            "woman mage"
        ]
    },
    {
        "codepoints": "🧚",
        "name": "fairy",
        "shortcodes": [
            ":fairy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fairy",
            "Oberon",
            "Puck",
            "Titania"
        ]
    },
    {
        "codepoints": "🧚‍♂️",
        "name": "man fairy",
        "shortcodes": [
            ":man_fairy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man fairy",
            "Oberon",
            "Puck"
        ]
    },
    {
        "codepoints": "🧚‍♀️",
        "name": "woman fairy",
        "shortcodes": [
            ":woman_fairy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "Titania",
            "woman fairy"
        ]
    },
    {
        "codepoints": "🧛",
        "name": "vampire",
        "shortcodes": [
            ":vampire:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "Dracula",
            "undead",
            "vampire"
        ]
    },
    {
        "codepoints": "🧛‍♂️",
        "name": "man vampire",
        "shortcodes": [
            ":man_vampire:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "Dracula",
            "man vampire",
            "undead"
        ]
    },
    {
        "codepoints": "🧛‍♀️",
        "name": "woman vampire",
        "shortcodes": [
            ":woman_vampire:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "undead",
            "woman vampire"
        ]
    },
    {
        "codepoints": "🧜",
        "name": "merperson",
        "shortcodes": [
            ":merperson:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "mermaid",
            "merman",
            "merperson",
            "merwoman"
        ]
    },
    {
        "codepoints": "🧜‍♂️",
        "name": "merman",
        "shortcodes": [
            ":merman:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "merman",
            "Triton"
        ]
    },
    {
        "codepoints": "🧜‍♀️",
        "name": "mermaid",
        "shortcodes": [
            ":mermaid:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "mermaid",
            "merwoman"
        ]
    },
    {
        "codepoints": "🧝",
        "name": "elf",
        "shortcodes": [
            ":elf:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "elf",
            "magical"
        ]
    },
    {
        "codepoints": "🧝‍♂️",
        "name": "man elf",
        "shortcodes": [
            ":man_elf:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "magical",
            "man elf"
        ]
    },
    {
        "codepoints": "🧝‍♀️",
        "name": "woman elf",
        "shortcodes": [
            ":woman_elf:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "magical",
            "woman elf"
        ]
    },
    {
        "codepoints": "🧞",
        "name": "genie",
        "shortcodes": [
            ":genie:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "djinn",
            "genie"
        ]
    },
    {
        "codepoints": "🧞‍♂️",
        "name": "man genie",
        "shortcodes": [
            ":man_genie:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "djinn",
            "man genie"
        ]
    },
    {
        "codepoints": "🧞‍♀️",
        "name": "woman genie",
        "shortcodes": [
            ":woman_genie:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "djinn",
            "woman genie"
        ]
    },
    {
        "codepoints": "🧟",
        "name": "zombie",
        "shortcodes": [
            ":zombie:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "undead",
            "walking dead",
            "zombie"
        ]
    },
    {
        "codepoints": "🧟‍♂️",
        "name": "man zombie",
        "shortcodes": [
            ":man_zombie:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man zombie",
            "undead",
            "walking dead"
        ]
    },
    {
        "codepoints": "🧟‍♀️",
        "name": "woman zombie",
        "shortcodes": [
            ":woman_zombie:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "undead",
            "walking dead",
            "woman zombie"
        ]
    },
    {
        "codepoints": "🧌",
        "name": "troll",
        "shortcodes": [
            ":troll:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fairy tale",
            "fantasy",
            "monster",
            "troll"
        ]
    },
    {
        "codepoints": "💆",
        "name": "person getting massage",
        "shortcodes": [
            ":person_getting_massage:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "face",
            "massage",
            "person getting massage",
            "salon"
        ]
    },
    {
        "codepoints": "💆‍♂️",
        "name": "man getting massage",
        "shortcodes": [
            ":man_getting_massage:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "face",
            "man",
            "man getting massage",
            "massage"
        ]
    },
    {
        "codepoints": "💆‍♀️",
        "name": "woman getting massage",
        "shortcodes": [
            ":woman_getting_massage:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "face",
            "massage",
            "woman",
            "woman getting massage"
        ]
    },
    {
        "codepoints": "💇",
        "name": "person getting haircut",
        "shortcodes": [
            ":person_getting_haircut:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "barber",
            "beauty",
            "haircut",
            "parlor",
            "person getting haircut",
            "parlour"
        ]
    },
    {
        "codepoints": "💇‍♂️",
        "name": "man getting haircut",
        "shortcodes": [
            ":man_getting_haircut:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "haircut",
            "hairdresser",
            "man",
            "man getting haircut"
        ]
    },
    {
        "codepoints": "💇‍♀️",
        "name": "woman getting haircut",
        "shortcodes": [
            ":woman_getting_haircut:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "haircut",
            "hairdresser",
            "woman",
            "woman getting haircut"
        ]
    },
    {
        "codepoints": "🚶",
        "name": "person walking",
        "shortcodes": [
            ":person_walking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hike",
            "person walking",
            "walk",
            "walking"
        ]
    },
    {
        "codepoints": "🚶‍♂️",
        "name": "man walking",
        "shortcodes": [
            ":man_walking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hike",
            "man",
            "man walking",
            "walk"
        ]
    },
    {
        "codepoints": "🚶‍♀️",
        "name": "woman walking",
        "shortcodes": [
            ":woman_walking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hike",
            "walk",
            "woman",
            "woman walking"
        ]
    },
    {
        "codepoints": "🧍",
        "name": "person standing",
        "shortcodes": [
            ":person_standing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "person standing",
            "stand",
            "standing"
        ]
    },
    {
        "codepoints": "🧍‍♂️",
        "name": "man standing",
        "shortcodes": [
            ":man_standing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "standing"
        ]
    },
    {
        "codepoints": "🧍‍♀️",
        "name": "woman standing",
        "shortcodes": [
            ":woman_standing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "standing",
            "woman"
        ]
    },
    {
        "codepoints": "🧎",
        "name": "person kneeling",
        "shortcodes": [
            ":person_kneeling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "kneel",
            "kneeling",
            "person kneeling"
        ]
    },
    {
        "codepoints": "🧎‍♂️",
        "name": "man kneeling",
        "shortcodes": [
            ":man_kneeling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "kneeling",
            "man"
        ]
    },
    {
        "codepoints": "🧎‍♀️",
        "name": "woman kneeling",
        "shortcodes": [
            ":woman_kneeling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "kneeling",
            "woman"
        ]
    },
    {
        "codepoints": "🧑‍🦯",
        "name": "person with white cane",
        "shortcodes": [
            ":person_with_white_cane:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "blind",
            "person with guide cane",
            "person with long mobility cane",
            "person with white cane"
        ]
    },
    {
        "codepoints": "👨‍🦯",
        "name": "man with white cane",
        "shortcodes": [
            ":man_with_white_cane:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "blind",
            "man",
            "man with white cane",
            "man with guide cane"
        ]
    },
    {
        "codepoints": "👩‍🦯",
        "name": "woman with white cane",
        "shortcodes": [
            ":woman_with_white_cane:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "blind",
            "woman",
            "woman with white cane",
            "woman with guide cane"
        ]
    },
    {
        "codepoints": "🧑‍🦼",
        "name": "person in motorized wheelchair",
        "shortcodes": [
            ":person_in_motorized_wheelchair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "person in motorised wheelchair",
            "accessibility",
            "person in motorized wheelchair",
            "wheelchair",
            "person in powered wheelchair"
        ]
    },
    {
        "codepoints": "👨‍🦼",
        "name": "man in motorized wheelchair",
        "shortcodes": [
            ":man_in_motorized_wheelchair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man in motorised wheelchair",
            "accessibility",
            "man",
            "man in motorized wheelchair",
            "wheelchair",
            "man in powered wheelchair"
        ]
    },
    {
        "codepoints": "👩‍🦼",
        "name": "woman in motorized wheelchair",
        "shortcodes": [
            ":woman_in_motorized_wheelchair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "woman in motorised wheelchair",
            "accessibility",
            "wheelchair",
            "woman",
            "woman in motorized wheelchair",
            "woman in powered wheelchair"
        ]
    },
    {
        "codepoints": "🧑‍🦽",
        "name": "person in manual wheelchair",
        "shortcodes": [
            ":person_in_manual_wheelchair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "person in manual wheelchair",
            "wheelchair"
        ]
    },
    {
        "codepoints": "👨‍🦽",
        "name": "man in manual wheelchair",
        "shortcodes": [
            ":man_in_manual_wheelchair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "man",
            "man in manual wheelchair",
            "wheelchair"
        ]
    },
    {
        "codepoints": "👩‍🦽",
        "name": "woman in manual wheelchair",
        "shortcodes": [
            ":woman_in_manual_wheelchair:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "accessibility",
            "wheelchair",
            "woman",
            "woman in manual wheelchair"
        ]
    },
    {
        "codepoints": "🏃",
        "name": "person running",
        "shortcodes": [
            ":person_running:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "marathon",
            "person running",
            "running"
        ]
    },
    {
        "codepoints": "🏃‍♂️",
        "name": "man running",
        "shortcodes": [
            ":man_running:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "marathon",
            "racing",
            "running"
        ]
    },
    {
        "codepoints": "🏃‍♀️",
        "name": "woman running",
        "shortcodes": [
            ":woman_running:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "marathon",
            "racing",
            "running",
            "woman"
        ]
    },
    {
        "codepoints": "💃",
        "name": "woman dancing",
        "shortcodes": [
            ":woman_dancing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "dance",
            "dancing",
            "woman"
        ]
    },
    {
        "codepoints": "🕺",
        "name": "man dancing",
        "shortcodes": [
            ":man_dancing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "dance",
            "dancing",
            "man"
        ]
    },
    {
        "codepoints": "🕴️",
        "name": "person in suit levitating",
        "shortcodes": [
            ":person_in_suit_levitating:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "business",
            "person",
            "person in suit levitating",
            "suit"
        ]
    },
    {
        "codepoints": "👯",
        "name": "people with bunny ears",
        "shortcodes": [
            ":people_with_bunny_ears:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bunny ear",
            "dancer",
            "partying",
            "people with bunny ears"
        ]
    },
    {
        "codepoints": "👯‍♂️",
        "name": "men with bunny ears",
        "shortcodes": [
            ":men_with_bunny_ears:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bunny ear",
            "dancer",
            "men",
            "men with bunny ears",
            "partying"
        ]
    },
    {
        "codepoints": "👯‍♀️",
        "name": "women with bunny ears",
        "shortcodes": [
            ":women_with_bunny_ears:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bunny ear",
            "dancer",
            "partying",
            "women",
            "women with bunny ears"
        ]
    },
    {
        "codepoints": "🧖",
        "name": "person in steamy room",
        "shortcodes": [
            ":person_in_steamy_room:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "person in steamy room",
            "sauna",
            "steam room"
        ]
    },
    {
        "codepoints": "🧖‍♂️",
        "name": "man in steamy room",
        "shortcodes": [
            ":man_in_steamy_room:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man in steam room",
            "man in steamy room",
            "sauna",
            "steam room"
        ]
    },
    {
        "codepoints": "🧖‍♀️",
        "name": "woman in steamy room",
        "shortcodes": [
            ":woman_in_steamy_room:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "sauna",
            "steam room",
            "woman in steam room",
            "woman in steamy room"
        ]
    },
    {
        "codepoints": "🧗",
        "name": "person climbing",
        "shortcodes": [
            ":person_climbing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "climber",
            "person climbing"
        ]
    },
    {
        "codepoints": "🧗‍♂️",
        "name": "man climbing",
        "shortcodes": [
            ":man_climbing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "climber",
            "man climbing"
        ]
    },
    {
        "codepoints": "🧗‍♀️",
        "name": "woman climbing",
        "shortcodes": [
            ":woman_climbing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "climber",
            "woman climbing"
        ]
    },
    {
        "codepoints": "🤺",
        "name": "person fencing",
        "shortcodes": [
            ":person_fencing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "fencer",
            "fencing",
            "person fencing",
            "sword"
        ]
    },
    {
        "codepoints": "🏇",
        "name": "horse racing",
        "shortcodes": [
            ":horse_racing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "horse",
            "jockey",
            "racehorse",
            "racing"
        ]
    },
    {
        "codepoints": "⛷️",
        "name": "skier",
        "shortcodes": [
            ":skier:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "ski",
            "skier",
            "snow"
        ]
    },
    {
        "codepoints": "🏂",
        "name": "snowboarder",
        "shortcodes": [
            ":snowboarder:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "ski",
            "snow",
            "snowboard",
            "snowboarder"
        ]
    },
    {
        "codepoints": "🏌️",
        "name": "person golfing",
        "shortcodes": [
            ":person_golfing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "ball",
            "golf",
            "golfer",
            "person golfing"
        ]
    },
    {
        "codepoints": "🏌️‍♂️",
        "name": "man golfing",
        "shortcodes": [
            ":man_golfing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": []
    },
    {
        "codepoints": "🏌️‍♀️",
        "name": "woman golfing",
        "shortcodes": [
            ":woman_golfing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": []
    },
    {
        "codepoints": "🏄",
        "name": "person surfing",
        "shortcodes": [
            ":person_surfing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "person surfing",
            "surfer",
            "surfing"
        ]
    },
    {
        "codepoints": "🏄‍♂️",
        "name": "man surfing",
        "shortcodes": [
            ":man_surfing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "surfer",
            "surfing"
        ]
    },
    {
        "codepoints": "🏄‍♀️",
        "name": "woman surfing",
        "shortcodes": [
            ":woman_surfing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "surfer",
            "surfing",
            "woman"
        ]
    },
    {
        "codepoints": "🚣",
        "name": "person rowing boat",
        "shortcodes": [
            ":person_rowing_boat:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boat",
            "person",
            "person rowing boat",
            "rowboat"
        ]
    },
    {
        "codepoints": "🚣‍♂️",
        "name": "man rowing boat",
        "shortcodes": [
            ":man_rowing_boat:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boat",
            "man",
            "man rowing boat",
            "rowboat"
        ]
    },
    {
        "codepoints": "🚣‍♀️",
        "name": "woman rowing boat",
        "shortcodes": [
            ":woman_rowing_boat:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boat",
            "rowboat",
            "woman",
            "woman rowing boat"
        ]
    },
    {
        "codepoints": "🏊",
        "name": "person swimming",
        "shortcodes": [
            ":person_swimming:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "person swimming",
            "swim",
            "swimmer"
        ]
    },
    {
        "codepoints": "🏊‍♂️",
        "name": "man swimming",
        "shortcodes": [
            ":man_swimming:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "man swimming",
            "swim",
            "swimmer"
        ]
    },
    {
        "codepoints": "🏊‍♀️",
        "name": "woman swimming",
        "shortcodes": [
            ":woman_swimming:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "swim",
            "swimmer",
            "woman",
            "woman swimming"
        ]
    },
    {
        "codepoints": "⛹️",
        "name": "person bouncing ball",
        "shortcodes": [
            ":person_bouncing_ball:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "ball",
            "person bouncing ball"
        ]
    },
    {
        "codepoints": "⛹️‍♂️",
        "name": "man bouncing ball",
        "shortcodes": [
            ":man_bouncing_ball:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": []
    },
    {
        "codepoints": "⛹️‍♀️",
        "name": "woman bouncing ball",
        "shortcodes": [
            ":woman_bouncing_ball:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": []
    },
    {
        "codepoints": "🏋️",
        "name": "person lifting weights",
        "shortcodes": [
            ":person_lifting_weights:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "lifter",
            "person lifting weights",
            "weight",
            "weightlifter"
        ]
    },
    {
        "codepoints": "🏋️‍♂️",
        "name": "man lifting weights",
        "shortcodes": [
            ":man_lifting_weights:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": []
    },
    {
        "codepoints": "🏋️‍♀️",
        "name": "woman lifting weights",
        "shortcodes": [
            ":woman_lifting_weights:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": []
    },
    {
        "codepoints": "🚴",
        "name": "person biking",
        "shortcodes": [
            ":person_biking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bicycle",
            "biking",
            "cyclist",
            "person biking",
            "person riding a bike"
        ]
    },
    {
        "codepoints": "🚴‍♂️",
        "name": "man biking",
        "shortcodes": [
            ":man_biking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bicycle",
            "biking",
            "cyclist",
            "man",
            "man riding a bike"
        ]
    },
    {
        "codepoints": "🚴‍♀️",
        "name": "woman biking",
        "shortcodes": [
            ":woman_biking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bicycle",
            "biking",
            "cyclist",
            "woman",
            "woman riding a bike"
        ]
    },
    {
        "codepoints": "🚵",
        "name": "person mountain biking",
        "shortcodes": [
            ":person_mountain_biking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bicycle",
            "bicyclist",
            "bike",
            "cyclist",
            "mountain",
            "person mountain biking"
        ]
    },
    {
        "codepoints": "🚵‍♂️",
        "name": "man mountain biking",
        "shortcodes": [
            ":man_mountain_biking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bicycle",
            "bike",
            "cyclist",
            "man",
            "man mountain biking",
            "mountain"
        ]
    },
    {
        "codepoints": "🚵‍♀️",
        "name": "woman mountain biking",
        "shortcodes": [
            ":woman_mountain_biking:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bicycle",
            "bike",
            "biking",
            "cyclist",
            "mountain",
            "woman"
        ]
    },
    {
        "codepoints": "🤸",
        "name": "person cartwheeling",
        "shortcodes": [
            ":person_cartwheeling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "cartwheel",
            "gymnastics",
            "person cartwheeling"
        ]
    },
    {
        "codepoints": "🤸‍♂️",
        "name": "man cartwheeling",
        "shortcodes": [
            ":man_cartwheeling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "cartwheel",
            "gymnastics",
            "man",
            "man cartwheeling"
        ]
    },
    {
        "codepoints": "🤸‍♀️",
        "name": "woman cartwheeling",
        "shortcodes": [
            ":woman_cartwheeling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "cartwheel",
            "gymnastics",
            "woman",
            "woman cartwheeling"
        ]
    },
    {
        "codepoints": "🤼",
        "name": "people wrestling",
        "shortcodes": [
            ":people_wrestling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "people wrestling",
            "wrestle",
            "wrestler"
        ]
    },
    {
        "codepoints": "🤼‍♂️",
        "name": "men wrestling",
        "shortcodes": [
            ":men_wrestling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "men",
            "men wrestling",
            "wrestle"
        ]
    },
    {
        "codepoints": "🤼‍♀️",
        "name": "women wrestling",
        "shortcodes": [
            ":women_wrestling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "women",
            "women wrestling",
            "wrestle"
        ]
    },
    {
        "codepoints": "🤽",
        "name": "person playing water polo",
        "shortcodes": [
            ":person_playing_water_polo:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "person playing water polo",
            "polo",
            "water"
        ]
    },
    {
        "codepoints": "🤽‍♂️",
        "name": "man playing water polo",
        "shortcodes": [
            ":man_playing_water_polo:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man",
            "man playing water polo",
            "water polo"
        ]
    },
    {
        "codepoints": "🤽‍♀️",
        "name": "woman playing water polo",
        "shortcodes": [
            ":woman_playing_water_polo:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "water polo",
            "woman",
            "woman playing water polo"
        ]
    },
    {
        "codepoints": "🤾",
        "name": "person playing handball",
        "shortcodes": [
            ":person_playing_handball:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "ball",
            "handball",
            "person playing handball"
        ]
    },
    {
        "codepoints": "🤾‍♂️",
        "name": "man playing handball",
        "shortcodes": [
            ":man_playing_handball:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "handball",
            "man",
            "man playing handball"
        ]
    },
    {
        "codepoints": "🤾‍♀️",
        "name": "woman playing handball",
        "shortcodes": [
            ":woman_playing_handball:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "handball",
            "woman",
            "woman playing handball"
        ]
    },
    {
        "codepoints": "🤹",
        "name": "person juggling",
        "shortcodes": [
            ":person_juggling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "balance",
            "juggle",
            "multi-task",
            "person juggling",
            "skill",
            "multitask"
        ]
    },
    {
        "codepoints": "🤹‍♂️",
        "name": "man juggling",
        "shortcodes": [
            ":man_juggling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "juggling",
            "man",
            "multi-task",
            "multitask"
        ]
    },
    {
        "codepoints": "🤹‍♀️",
        "name": "woman juggling",
        "shortcodes": [
            ":woman_juggling:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "juggling",
            "multi-task",
            "woman",
            "multitask"
        ]
    },
    {
        "codepoints": "🧘",
        "name": "person in lotus position",
        "shortcodes": [
            ":person_in_lotus_position:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "meditation",
            "person in lotus position",
            "yoga"
        ]
    },
    {
        "codepoints": "🧘‍♂️",
        "name": "man in lotus position",
        "shortcodes": [
            ":man_in_lotus_position:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "man in lotus position",
            "meditation",
            "yoga"
        ]
    },
    {
        "codepoints": "🧘‍♀️",
        "name": "woman in lotus position",
        "shortcodes": [
            ":woman_in_lotus_position:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "meditation",
            "woman in lotus position",
            "yoga"
        ]
    },
    {
        "codepoints": "🛀",
        "name": "person taking bath",
        "shortcodes": [
            ":person_taking_bath:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bath",
            "bathtub",
            "person taking bath",
            "tub"
        ]
    },
    {
        "codepoints": "🛌",
        "name": "person in bed",
        "shortcodes": [
            ":person_in_bed:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "hotel",
            "person in bed",
            "sleep",
            "sleeping",
            "good night"
        ]
    },
    {
        "codepoints": "🧑‍🤝‍🧑",
        "name": "people holding hands",
        "shortcodes": [
            ":people_holding_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "hand",
            "hold",
            "holding hands",
            "people holding hands",
            "person"
        ]
    },
    {
        "codepoints": "👭",
        "name": "women holding hands",
        "shortcodes": [
            ":women_holding_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "hand",
            "holding hands",
            "women",
            "women holding hands",
            "two women holding hands"
        ]
    },
    {
        "codepoints": "👫",
        "name": "woman and man holding hands",
        "shortcodes": [
            ":woman_and_man_holding_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "hand",
            "hold",
            "holding hands",
            "man",
            "woman",
            "woman and man holding hands",
            "man and woman holding hands"
        ]
    },
    {
        "codepoints": "👬",
        "name": "men holding hands",
        "shortcodes": [
            ":men_holding_hands:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "Gemini",
            "holding hands",
            "man",
            "men",
            "men holding hands",
            "twins",
            "zodiac",
            "two men holding hands"
        ]
    },
    {
        "codepoints": "💏",
        "name": "kiss",
        "shortcodes": [
            ":kiss:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "kiss"
        ]
    },
    {
        "codepoints": "👩‍❤️‍💋‍👨",
        "name": "kiss: woman, man",
        "shortcodes": [
            ":kiss:_woman,_man:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "kiss",
            "man",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍❤️‍💋‍👨",
        "name": "kiss: man, man",
        "shortcodes": [
            ":kiss:_man,_man:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "kiss",
            "man"
        ]
    },
    {
        "codepoints": "👩‍❤️‍💋‍👩",
        "name": "kiss: woman, woman",
        "shortcodes": [
            ":kiss:_woman,_woman:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "kiss",
            "woman"
        ]
    },
    {
        "codepoints": "💑",
        "name": "couple with heart",
        "shortcodes": [
            ":couple_with_heart:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "couple with heart",
            "love"
        ]
    },
    {
        "codepoints": "👩‍❤️‍👨",
        "name": "couple with heart: woman, man",
        "shortcodes": [
            ":couple_with_heart:_woman,_man:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "couple with heart",
            "love",
            "man",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍❤️‍👨",
        "name": "couple with heart: man, man",
        "shortcodes": [
            ":couple_with_heart:_man,_man:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "couple with heart",
            "love",
            "man"
        ]
    },
    {
        "codepoints": "👩‍❤️‍👩",
        "name": "couple with heart: woman, woman",
        "shortcodes": [
            ":couple_with_heart:_woman,_woman:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "couple",
            "couple with heart",
            "love",
            "woman"
        ]
    },
    {
        "codepoints": "👪",
        "name": "family",
        "shortcodes": [
            ":family:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family"
        ]
    },
    {
        "codepoints": "👨‍👩‍👦",
        "name": "family: man, woman, boy",
        "shortcodes": [
            ":family:_man,_woman,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "man",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍👩‍👧",
        "name": "family: man, woman, girl",
        "shortcodes": [
            ":family:_man,_woman,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "man",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍👩‍👧‍👦",
        "name": "family: man, woman, girl, boy",
        "shortcodes": [
            ":family:_man,_woman,_girl,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "girl",
            "man",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍👩‍👦‍👦",
        "name": "family: man, woman, boy, boy",
        "shortcodes": [
            ":family:_man,_woman,_boy,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "man",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍👩‍👧‍👧",
        "name": "family: man, woman, girl, girl",
        "shortcodes": [
            ":family:_man,_woman,_girl,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "man",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍👨‍👦",
        "name": "family: man, man, boy",
        "shortcodes": [
            ":family:_man,_man,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "man"
        ]
    },
    {
        "codepoints": "👨‍👨‍👧",
        "name": "family: man, man, girl",
        "shortcodes": [
            ":family:_man,_man,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "man"
        ]
    },
    {
        "codepoints": "👨‍👨‍👧‍👦",
        "name": "family: man, man, girl, boy",
        "shortcodes": [
            ":family:_man,_man,_girl,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "girl",
            "man"
        ]
    },
    {
        "codepoints": "👨‍👨‍👦‍👦",
        "name": "family: man, man, boy, boy",
        "shortcodes": [
            ":family:_man,_man,_boy,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "man"
        ]
    },
    {
        "codepoints": "👨‍👨‍👧‍👧",
        "name": "family: man, man, girl, girl",
        "shortcodes": [
            ":family:_man,_man,_girl,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "man"
        ]
    },
    {
        "codepoints": "👩‍👩‍👦",
        "name": "family: woman, woman, boy",
        "shortcodes": [
            ":family:_woman,_woman,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍👩‍👧",
        "name": "family: woman, woman, girl",
        "shortcodes": [
            ":family:_woman,_woman,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍👩‍👧‍👦",
        "name": "family: woman, woman, girl, boy",
        "shortcodes": [
            ":family:_woman,_woman,_girl,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "girl",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍👩‍👦‍👦",
        "name": "family: woman, woman, boy, boy",
        "shortcodes": [
            ":family:_woman,_woman,_boy,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍👩‍👧‍👧",
        "name": "family: woman, woman, girl, girl",
        "shortcodes": [
            ":family:_woman,_woman,_girl,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "woman"
        ]
    },
    {
        "codepoints": "👨‍👦",
        "name": "family: man, boy",
        "shortcodes": [
            ":family:_man,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "man"
        ]
    },
    {
        "codepoints": "👨‍👦‍👦",
        "name": "family: man, boy, boy",
        "shortcodes": [
            ":family:_man,_boy,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "man"
        ]
    },
    {
        "codepoints": "👨‍👧",
        "name": "family: man, girl",
        "shortcodes": [
            ":family:_man,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "man"
        ]
    },
    {
        "codepoints": "👨‍👧‍👦",
        "name": "family: man, girl, boy",
        "shortcodes": [
            ":family:_man,_girl,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "girl",
            "man"
        ]
    },
    {
        "codepoints": "👨‍👧‍👧",
        "name": "family: man, girl, girl",
        "shortcodes": [
            ":family:_man,_girl,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "man"
        ]
    },
    {
        "codepoints": "👩‍👦",
        "name": "family: woman, boy",
        "shortcodes": [
            ":family:_woman,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍👦‍👦",
        "name": "family: woman, boy, boy",
        "shortcodes": [
            ":family:_woman,_boy,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍👧",
        "name": "family: woman, girl",
        "shortcodes": [
            ":family:_woman,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍👧‍👦",
        "name": "family: woman, girl, boy",
        "shortcodes": [
            ":family:_woman,_girl,_boy:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "boy",
            "family",
            "girl",
            "woman"
        ]
    },
    {
        "codepoints": "👩‍👧‍👧",
        "name": "family: woman, girl, girl",
        "shortcodes": [
            ":family:_woman,_girl,_girl:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "family",
            "girl",
            "woman"
        ]
    },
    {
        "codepoints": "🗣️",
        "name": "speaking head",
        "shortcodes": [
            ":speaking_head:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "face",
            "head",
            "silhouette",
            "speak",
            "speaking"
        ]
    },
    {
        "codepoints": "👤",
        "name": "bust in silhouette",
        "shortcodes": [
            ":bust_in_silhouette:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bust",
            "bust in silhouette",
            "silhouette"
        ]
    },
    {
        "codepoints": "👥",
        "name": "busts in silhouette",
        "shortcodes": [
            ":busts_in_silhouette:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "bust",
            "busts in silhouette",
            "silhouette"
        ]
    },
    {
        "codepoints": "🫂",
        "name": "people hugging",
        "shortcodes": [
            ":people_hugging:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "goodbye",
            "hello",
            "hug",
            "people hugging",
            "thanks"
        ]
    },
    {
        "codepoints": "👣",
        "name": "footprints",
        "shortcodes": [
            ":footprints:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [
            "clothing",
            "footprint",
            "footprints",
            "print"
        ]
    },
    {
        "codepoints": "🐵",
        "name": "monkey face",
        "shortcodes": [
            ":monkey_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "monkey"
        ]
    },
    {
        "codepoints": "🐒",
        "name": "monkey",
        "shortcodes": [
            ":monkey:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "monkey"
        ]
    },
    {
        "codepoints": "🦍",
        "name": "gorilla",
        "shortcodes": [
            ":gorilla:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "gorilla"
        ]
    },
    {
        "codepoints": "🦧",
        "name": "orangutan",
        "shortcodes": [
            ":orangutan:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "ape",
            "orangutan"
        ]
    },
    {
        "codepoints": "🐶",
        "name": "dog face",
        "shortcodes": [
            ":dog_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "dog",
            "face",
            "pet"
        ]
    },
    {
        "codepoints": "🐕",
        "name": "dog",
        "shortcodes": [
            ":dog:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "dog",
            "pet"
        ]
    },
    {
        "codepoints": "🦮",
        "name": "guide dog",
        "shortcodes": [
            ":guide_dog:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "accessibility",
            "blind",
            "guide",
            "guide dog"
        ]
    },
    {
        "codepoints": "🐕‍🦺",
        "name": "service dog",
        "shortcodes": [
            ":service_dog:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "accessibility",
            "assistance",
            "dog",
            "service"
        ]
    },
    {
        "codepoints": "🐩",
        "name": "poodle",
        "shortcodes": [
            ":poodle:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "dog",
            "poodle"
        ]
    },
    {
        "codepoints": "🐺",
        "name": "wolf",
        "shortcodes": [
            ":wolf:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "wolf"
        ]
    },
    {
        "codepoints": "🦊",
        "name": "fox",
        "shortcodes": [
            ":fox:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "fox"
        ]
    },
    {
        "codepoints": "🦝",
        "name": "raccoon",
        "shortcodes": [
            ":raccoon:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "curious",
            "raccoon",
            "sly"
        ]
    },
    {
        "codepoints": "🐱",
        "name": "cat face",
        "shortcodes": [
            ":cat_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "cat",
            "face",
            "pet"
        ]
    },
    {
        "codepoints": "🐈",
        "name": "cat",
        "shortcodes": [
            ":cat:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "cat",
            "pet"
        ]
    },
    {
        "codepoints": "🐈‍⬛",
        "name": "black cat",
        "shortcodes": [
            ":black_cat:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "black",
            "cat",
            "unlucky"
        ]
    },
    {
        "codepoints": "🦁",
        "name": "lion",
        "shortcodes": [
            ":lion:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "Leo",
            "lion",
            "zodiac"
        ]
    },
    {
        "codepoints": "🐯",
        "name": "tiger face",
        "shortcodes": [
            ":tiger_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "tiger"
        ]
    },
    {
        "codepoints": "🐅",
        "name": "tiger",
        "shortcodes": [
            ":tiger:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "tiger"
        ]
    },
    {
        "codepoints": "🐆",
        "name": "leopard",
        "shortcodes": [
            ":leopard:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "leopard"
        ]
    },
    {
        "codepoints": "🐴",
        "name": "horse face",
        "shortcodes": [
            ":horse_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "horse"
        ]
    },
    {
        "codepoints": "🐎",
        "name": "horse",
        "shortcodes": [
            ":horse:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "equestrian",
            "horse",
            "racehorse",
            "racing"
        ]
    },
    {
        "codepoints": "🦄",
        "name": "unicorn",
        "shortcodes": [
            ":unicorn:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "unicorn"
        ]
    },
    {
        "codepoints": "🦓",
        "name": "zebra",
        "shortcodes": [
            ":zebra:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "stripe",
            "zebra"
        ]
    },
    {
        "codepoints": "🦌",
        "name": "deer",
        "shortcodes": [
            ":deer:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "deer",
            "stag"
        ]
    },
    {
        "codepoints": "🦬",
        "name": "bison",
        "shortcodes": [
            ":bison:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bison",
            "buffalo",
            "herd",
            "wisent"
        ]
    },
    {
        "codepoints": "🐮",
        "name": "cow face",
        "shortcodes": [
            ":cow_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "cow",
            "face"
        ]
    },
    {
        "codepoints": "🐂",
        "name": "ox",
        "shortcodes": [
            ":ox:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bull",
            "ox",
            "Taurus",
            "zodiac"
        ]
    },
    {
        "codepoints": "🐃",
        "name": "water buffalo",
        "shortcodes": [
            ":water_buffalo:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "buffalo",
            "water"
        ]
    },
    {
        "codepoints": "🐄",
        "name": "cow",
        "shortcodes": [
            ":cow:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "cow"
        ]
    },
    {
        "codepoints": "🐷",
        "name": "pig face",
        "shortcodes": [
            ":pig_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "pig"
        ]
    },
    {
        "codepoints": "🐖",
        "name": "pig",
        "shortcodes": [
            ":pig:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "pig",
            "sow"
        ]
    },
    {
        "codepoints": "🐗",
        "name": "boar",
        "shortcodes": [
            ":boar:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "boar",
            "pig"
        ]
    },
    {
        "codepoints": "🐽",
        "name": "pig nose",
        "shortcodes": [
            ":pig_nose:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "nose",
            "pig"
        ]
    },
    {
        "codepoints": "🐏",
        "name": "ram",
        "shortcodes": [
            ":ram:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "Aries",
            "male",
            "ram",
            "sheep",
            "zodiac"
        ]
    },
    {
        "codepoints": "🐑",
        "name": "ewe",
        "shortcodes": [
            ":ewe:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "ewe",
            "female",
            "sheep"
        ]
    },
    {
        "codepoints": "🐐",
        "name": "goat",
        "shortcodes": [
            ":goat:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "Capricorn",
            "goat",
            "zodiac"
        ]
    },
    {
        "codepoints": "🐪",
        "name": "camel",
        "shortcodes": [
            ":camel:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "camel",
            "dromedary",
            "hump"
        ]
    },
    {
        "codepoints": "🐫",
        "name": "two-hump camel",
        "shortcodes": [
            ":two-hump_camel:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bactrian",
            "camel",
            "hump",
            "two-hump camel",
            "Bactrian"
        ]
    },
    {
        "codepoints": "🦙",
        "name": "llama",
        "shortcodes": [
            ":llama:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "alpaca",
            "guanaco",
            "llama",
            "vicuña",
            "wool"
        ]
    },
    {
        "codepoints": "🦒",
        "name": "giraffe",
        "shortcodes": [
            ":giraffe:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "giraffe",
            "spots"
        ]
    },
    {
        "codepoints": "🐘",
        "name": "elephant",
        "shortcodes": [
            ":elephant:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "elephant"
        ]
    },
    {
        "codepoints": "🦣",
        "name": "mammoth",
        "shortcodes": [
            ":mammoth:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "extinction",
            "large",
            "mammoth",
            "tusk",
            "woolly"
        ]
    },
    {
        "codepoints": "🦏",
        "name": "rhinoceros",
        "shortcodes": [
            ":rhinoceros:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "rhino",
            "rhinoceros"
        ]
    },
    {
        "codepoints": "🦛",
        "name": "hippopotamus",
        "shortcodes": [
            ":hippopotamus:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "hippo",
            "hippopotamus"
        ]
    },
    {
        "codepoints": "🐭",
        "name": "mouse face",
        "shortcodes": [
            ":mouse_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "mouse",
            "pet"
        ]
    },
    {
        "codepoints": "🐁",
        "name": "mouse",
        "shortcodes": [
            ":mouse:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "mouse",
            "pet",
            "rodent"
        ]
    },
    {
        "codepoints": "🐀",
        "name": "rat",
        "shortcodes": [
            ":rat:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "pet",
            "rat",
            "rodent"
        ]
    },
    {
        "codepoints": "🐹",
        "name": "hamster",
        "shortcodes": [
            ":hamster:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "hamster",
            "pet"
        ]
    },
    {
        "codepoints": "🐰",
        "name": "rabbit face",
        "shortcodes": [
            ":rabbit_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bunny",
            "face",
            "pet",
            "rabbit"
        ]
    },
    {
        "codepoints": "🐇",
        "name": "rabbit",
        "shortcodes": [
            ":rabbit:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bunny",
            "pet",
            "rabbit"
        ]
    },
    {
        "codepoints": "🐿️",
        "name": "chipmunk",
        "shortcodes": [
            ":chipmunk:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "chipmunk",
            "squirrel"
        ]
    },
    {
        "codepoints": "🦫",
        "name": "beaver",
        "shortcodes": [
            ":beaver:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "beaver",
            "dam"
        ]
    },
    {
        "codepoints": "🦔",
        "name": "hedgehog",
        "shortcodes": [
            ":hedgehog:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "hedgehog",
            "spiny"
        ]
    },
    {
        "codepoints": "🦇",
        "name": "bat",
        "shortcodes": [
            ":bat:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bat",
            "vampire"
        ]
    },
    {
        "codepoints": "🐻",
        "name": "bear",
        "shortcodes": [
            ":bear:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bear",
            "face"
        ]
    },
    {
        "codepoints": "🐻‍❄️",
        "name": "polar bear",
        "shortcodes": [
            ":polar_bear:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "arctic",
            "bear",
            "polar bear",
            "white"
        ]
    },
    {
        "codepoints": "🐨",
        "name": "koala",
        "shortcodes": [
            ":koala:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "koala",
            "marsupial",
            "face"
        ]
    },
    {
        "codepoints": "🐼",
        "name": "panda",
        "shortcodes": [
            ":panda:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "panda"
        ]
    },
    {
        "codepoints": "🦥",
        "name": "sloth",
        "shortcodes": [
            ":sloth:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "lazy",
            "sloth",
            "slow"
        ]
    },
    {
        "codepoints": "🦦",
        "name": "otter",
        "shortcodes": [
            ":otter:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "fishing",
            "otter",
            "playful"
        ]
    },
    {
        "codepoints": "🦨",
        "name": "skunk",
        "shortcodes": [
            ":skunk:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "skunk",
            "stink"
        ]
    },
    {
        "codepoints": "🦘",
        "name": "kangaroo",
        "shortcodes": [
            ":kangaroo:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "Australia",
            "joey",
            "jump",
            "kangaroo",
            "marsupial"
        ]
    },
    {
        "codepoints": "🦡",
        "name": "badger",
        "shortcodes": [
            ":badger:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "badger",
            "honey badger",
            "pester"
        ]
    },
    {
        "codepoints": "🐾",
        "name": "paw prints",
        "shortcodes": [
            ":paw_prints:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "feet",
            "paw",
            "paw prints",
            "print"
        ]
    },
    {
        "codepoints": "🦃",
        "name": "turkey",
        "shortcodes": [
            ":turkey:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "poultry",
            "turkey"
        ]
    },
    {
        "codepoints": "🐔",
        "name": "chicken",
        "shortcodes": [
            ":chicken:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "chicken",
            "poultry"
        ]
    },
    {
        "codepoints": "🐓",
        "name": "rooster",
        "shortcodes": [
            ":rooster:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "rooster"
        ]
    },
    {
        "codepoints": "🐣",
        "name": "hatching chick",
        "shortcodes": [
            ":hatching_chick:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "baby",
            "bird",
            "chick",
            "hatching"
        ]
    },
    {
        "codepoints": "🐤",
        "name": "baby chick",
        "shortcodes": [
            ":baby_chick:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "baby",
            "bird",
            "chick"
        ]
    },
    {
        "codepoints": "🐥",
        "name": "front-facing baby chick",
        "shortcodes": [
            ":front-facing_baby_chick:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "baby",
            "bird",
            "chick",
            "front-facing baby chick"
        ]
    },
    {
        "codepoints": "🐦",
        "name": "bird",
        "shortcodes": [
            ":bird:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird"
        ]
    },
    {
        "codepoints": "🐧",
        "name": "penguin",
        "shortcodes": [
            ":penguin:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "penguin"
        ]
    },
    {
        "codepoints": "🕊️",
        "name": "dove",
        "shortcodes": [
            ":dove:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "dove",
            "fly",
            "peace"
        ]
    },
    {
        "codepoints": "🦅",
        "name": "eagle",
        "shortcodes": [
            ":eagle:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird of prey",
            "eagle",
            "bird"
        ]
    },
    {
        "codepoints": "🦆",
        "name": "duck",
        "shortcodes": [
            ":duck:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "duck"
        ]
    },
    {
        "codepoints": "🦢",
        "name": "swan",
        "shortcodes": [
            ":swan:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "cygnet",
            "swan",
            "ugly duckling"
        ]
    },
    {
        "codepoints": "🦉",
        "name": "owl",
        "shortcodes": [
            ":owl:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird of prey",
            "owl",
            "wise",
            "bird"
        ]
    },
    {
        "codepoints": "🦤",
        "name": "dodo",
        "shortcodes": [
            ":dodo:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "dodo",
            "extinction",
            "large",
            "Mauritius"
        ]
    },
    {
        "codepoints": "🪶",
        "name": "feather",
        "shortcodes": [
            ":feather:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "feather",
            "flight",
            "light",
            "plumage"
        ]
    },
    {
        "codepoints": "🦩",
        "name": "flamingo",
        "shortcodes": [
            ":flamingo:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "flamboyant",
            "flamingo",
            "tropical"
        ]
    },
    {
        "codepoints": "🦚",
        "name": "peacock",
        "shortcodes": [
            ":peacock:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "ostentatious",
            "peacock",
            "peahen",
            "proud"
        ]
    },
    {
        "codepoints": "🦜",
        "name": "parrot",
        "shortcodes": [
            ":parrot:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bird",
            "parrot",
            "pirate",
            "talk"
        ]
    },
    {
        "codepoints": "🐸",
        "name": "frog",
        "shortcodes": [
            ":frog:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "frog"
        ]
    },
    {
        "codepoints": "🐊",
        "name": "crocodile",
        "shortcodes": [
            ":crocodile:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "crocodile"
        ]
    },
    {
        "codepoints": "🐢",
        "name": "turtle",
        "shortcodes": [
            ":turtle:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "terrapin",
            "tortoise",
            "turtle"
        ]
    },
    {
        "codepoints": "🦎",
        "name": "lizard",
        "shortcodes": [
            ":lizard:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "lizard",
            "reptile"
        ]
    },
    {
        "codepoints": "🐍",
        "name": "snake",
        "shortcodes": [
            ":snake:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bearer",
            "Ophiuchus",
            "serpent",
            "snake",
            "zodiac"
        ]
    },
    {
        "codepoints": "🐲",
        "name": "dragon face",
        "shortcodes": [
            ":dragon_face:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "dragon",
            "face",
            "fairy tale"
        ]
    },
    {
        "codepoints": "🐉",
        "name": "dragon",
        "shortcodes": [
            ":dragon:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "dragon",
            "fairy tale"
        ]
    },
    {
        "codepoints": "🦕",
        "name": "sauropod",
        "shortcodes": [
            ":sauropod:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "brachiosaurus",
            "brontosaurus",
            "diplodocus",
            "sauropod"
        ]
    },
    {
        "codepoints": "🦖",
        "name": "T-Rex",
        "shortcodes": [
            ":T-Rex:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "T-Rex",
            "Tyrannosaurus Rex"
        ]
    },
    {
        "codepoints": "🐳",
        "name": "spouting whale",
        "shortcodes": [
            ":spouting_whale:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "face",
            "spouting",
            "whale"
        ]
    },
    {
        "codepoints": "🐋",
        "name": "whale",
        "shortcodes": [
            ":whale:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "whale"
        ]
    },
    {
        "codepoints": "🐬",
        "name": "dolphin",
        "shortcodes": [
            ":dolphin:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "dolphin",
            "porpoise",
            "flipper"
        ]
    },
    {
        "codepoints": "🦭",
        "name": "seal",
        "shortcodes": [
            ":seal:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "sea lion",
            "seal"
        ]
    },
    {
        "codepoints": "🐟",
        "name": "fish",
        "shortcodes": [
            ":fish:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "fish",
            "Pisces",
            "zodiac"
        ]
    },
    {
        "codepoints": "🐠",
        "name": "tropical fish",
        "shortcodes": [
            ":tropical_fish:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "fish",
            "reef fish",
            "tropical"
        ]
    },
    {
        "codepoints": "🐡",
        "name": "blowfish",
        "shortcodes": [
            ":blowfish:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "blowfish",
            "fish"
        ]
    },
    {
        "codepoints": "🦈",
        "name": "shark",
        "shortcodes": [
            ":shark:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "fish",
            "shark"
        ]
    },
    {
        "codepoints": "🐙",
        "name": "octopus",
        "shortcodes": [
            ":octopus:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "octopus"
        ]
    },
    {
        "codepoints": "🐚",
        "name": "spiral shell",
        "shortcodes": [
            ":spiral_shell:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "shell",
            "spiral"
        ]
    },
    {
        "codepoints": "🪸",
        "name": "coral",
        "shortcodes": [
            ":coral:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "coral",
            "ocean",
            "reef"
        ]
    },
    {
        "codepoints": "🐌",
        "name": "snail",
        "shortcodes": [
            ":snail:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "mollusc",
            "snail"
        ]
    },
    {
        "codepoints": "🦋",
        "name": "butterfly",
        "shortcodes": [
            ":butterfly:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "butterfly",
            "insect",
            "moth",
            "pretty"
        ]
    },
    {
        "codepoints": "🐛",
        "name": "bug",
        "shortcodes": [
            ":bug:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bug",
            "caterpillar",
            "insect",
            "worm"
        ]
    },
    {
        "codepoints": "🐜",
        "name": "ant",
        "shortcodes": [
            ":ant:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "ant",
            "insect"
        ]
    },
    {
        "codepoints": "🐝",
        "name": "honeybee",
        "shortcodes": [
            ":honeybee:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bee",
            "honeybee",
            "insect"
        ]
    },
    {
        "codepoints": "🪲",
        "name": "beetle",
        "shortcodes": [
            ":beetle:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "beetle",
            "bug",
            "insect"
        ]
    },
    {
        "codepoints": "🐞",
        "name": "lady beetle",
        "shortcodes": [
            ":lady_beetle:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "beetle",
            "insect",
            "lady beetle",
            "ladybird",
            "ladybug"
        ]
    },
    {
        "codepoints": "🦗",
        "name": "cricket",
        "shortcodes": [
            ":cricket:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "cricket",
            "grasshopper"
        ]
    },
    {
        "codepoints": "🪳",
        "name": "cockroach",
        "shortcodes": [
            ":cockroach:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "cockroach",
            "insect",
            "pest",
            "roach"
        ]
    },
    {
        "codepoints": "🕷️",
        "name": "spider",
        "shortcodes": [
            ":spider:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "arachnid",
            "spider",
            "insect"
        ]
    },
    {
        "codepoints": "🕸️",
        "name": "spider web",
        "shortcodes": [
            ":spider_web:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "spider",
            "web"
        ]
    },
    {
        "codepoints": "🦂",
        "name": "scorpion",
        "shortcodes": [
            ":scorpion:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "scorpio",
            "Scorpio",
            "scorpion",
            "zodiac"
        ]
    },
    {
        "codepoints": "🦟",
        "name": "mosquito",
        "shortcodes": [
            ":mosquito:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "dengue",
            "fever",
            "insect",
            "malaria",
            "mosquito",
            "mozzie",
            "virus",
            "disease",
            "pest"
        ]
    },
    {
        "codepoints": "🪰",
        "name": "fly",
        "shortcodes": [
            ":fly:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "disease",
            "fly",
            "maggot",
            "pest",
            "rotting"
        ]
    },
    {
        "codepoints": "🪱",
        "name": "worm",
        "shortcodes": [
            ":worm:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "annelid",
            "earthworm",
            "parasite",
            "worm"
        ]
    },
    {
        "codepoints": "🦠",
        "name": "microbe",
        "shortcodes": [
            ":microbe:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "amoeba",
            "bacteria",
            "microbe",
            "virus"
        ]
    },
    {
        "codepoints": "💐",
        "name": "bouquet",
        "shortcodes": [
            ":bouquet:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "bouquet",
            "flower"
        ]
    },
    {
        "codepoints": "🌸",
        "name": "cherry blossom",
        "shortcodes": [
            ":cherry_blossom:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "blossom",
            "cherry",
            "flower"
        ]
    },
    {
        "codepoints": "💮",
        "name": "white flower",
        "shortcodes": [
            ":white_flower:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "flower",
            "white flower"
        ]
    },
    {
        "codepoints": "🪷",
        "name": "lotus",
        "shortcodes": [
            ":lotus:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "Buddhism",
            "flower",
            "Hinduism",
            "India",
            "lotus",
            "purity",
            "Vietnam"
        ]
    },
    {
        "codepoints": "🏵️",
        "name": "rosette",
        "shortcodes": [
            ":rosette:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "plant",
            "rosette"
        ]
    },
    {
        "codepoints": "🌹",
        "name": "rose",
        "shortcodes": [
            ":rose:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "flower",
            "rose"
        ]
    },
    {
        "codepoints": "🥀",
        "name": "wilted flower",
        "shortcodes": [
            ":wilted_flower:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "flower",
            "wilted"
        ]
    },
    {
        "codepoints": "🌺",
        "name": "hibiscus",
        "shortcodes": [
            ":hibiscus:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "flower",
            "hibiscus"
        ]
    },
    {
        "codepoints": "🌻",
        "name": "sunflower",
        "shortcodes": [
            ":sunflower:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "flower",
            "sun",
            "sunflower"
        ]
    },
    {
        "codepoints": "🌼",
        "name": "blossom",
        "shortcodes": [
            ":blossom:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "blossom",
            "flower"
        ]
    },
    {
        "codepoints": "🌷",
        "name": "tulip",
        "shortcodes": [
            ":tulip:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "flower",
            "tulip"
        ]
    },
    {
        "codepoints": "🌱",
        "name": "seedling",
        "shortcodes": [
            ":seedling:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "seedling",
            "young"
        ]
    },
    {
        "codepoints": "🪴",
        "name": "potted plant",
        "shortcodes": [
            ":potted_plant:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "grow",
            "house",
            "nurturing",
            "plant",
            "pot plant",
            "boring",
            "potted plant",
            "useless"
        ]
    },
    {
        "codepoints": "🌲",
        "name": "evergreen tree",
        "shortcodes": [
            ":evergreen_tree:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "evergreen tree",
            "tree"
        ]
    },
    {
        "codepoints": "🌳",
        "name": "deciduous tree",
        "shortcodes": [
            ":deciduous_tree:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "deciduous",
            "shedding",
            "tree"
        ]
    },
    {
        "codepoints": "🌴",
        "name": "palm tree",
        "shortcodes": [
            ":palm_tree:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "palm",
            "tree"
        ]
    },
    {
        "codepoints": "🌵",
        "name": "cactus",
        "shortcodes": [
            ":cactus:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "cactus",
            "plant"
        ]
    },
    {
        "codepoints": "🌾",
        "name": "sheaf of rice",
        "shortcodes": [
            ":sheaf_of_rice:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "ear",
            "grain",
            "rice",
            "sheaf of rice",
            "sheaf"
        ]
    },
    {
        "codepoints": "🌿",
        "name": "herb",
        "shortcodes": [
            ":herb:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "herb",
            "leaf"
        ]
    },
    {
        "codepoints": "☘️",
        "name": "shamrock",
        "shortcodes": [
            ":shamrock:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "plant",
            "shamrock"
        ]
    },
    {
        "codepoints": "🍀",
        "name": "four leaf clover",
        "shortcodes": [
            ":four_leaf_clover:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "4",
            "clover",
            "four",
            "four-leaf clover",
            "leaf"
        ]
    },
    {
        "codepoints": "🍁",
        "name": "maple leaf",
        "shortcodes": [
            ":maple_leaf:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "falling",
            "leaf",
            "maple"
        ]
    },
    {
        "codepoints": "🍂",
        "name": "fallen leaf",
        "shortcodes": [
            ":fallen_leaf:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "fallen leaf",
            "falling",
            "leaf"
        ]
    },
    {
        "codepoints": "🍃",
        "name": "leaf fluttering in wind",
        "shortcodes": [
            ":leaf_fluttering_in_wind:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "blow",
            "flutter",
            "leaf",
            "leaf fluttering in wind",
            "wind"
        ]
    },
    {
        "codepoints": "🪹",
        "name": "empty nest",
        "shortcodes": [
            ":empty_nest:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "empty nest",
            "nesting"
        ]
    },
    {
        "codepoints": "🪺",
        "name": "nest with eggs",
        "shortcodes": [
            ":nest_with_eggs:"
        ],
        "emoticons": [],
        "category": "Animals & Nature",
        "keywords": [
            "nest with eggs",
            "nesting"
        ]
    },
    {
        "codepoints": "🍇",
        "name": "grapes",
        "shortcodes": [
            ":grapes:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "grape",
            "grapes"
        ]
    },
    {
        "codepoints": "🍈",
        "name": "melon",
        "shortcodes": [
            ":melon:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "melon"
        ]
    },
    {
        "codepoints": "🍉",
        "name": "watermelon",
        "shortcodes": [
            ":watermelon:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "watermelon"
        ]
    },
    {
        "codepoints": "🍊",
        "name": "tangerine",
        "shortcodes": [
            ":tangerine:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "mandarin",
            "orange",
            "tangerine"
        ]
    },
    {
        "codepoints": "🍋",
        "name": "lemon",
        "shortcodes": [
            ":lemon:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "citrus",
            "fruit",
            "lemon"
        ]
    },
    {
        "codepoints": "🍌",
        "name": "banana",
        "shortcodes": [
            ":banana:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "banana",
            "fruit"
        ]
    },
    {
        "codepoints": "🍍",
        "name": "pineapple",
        "shortcodes": [
            ":pineapple:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "pineapple"
        ]
    },
    {
        "codepoints": "🥭",
        "name": "mango",
        "shortcodes": [
            ":mango:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "mango",
            "tropical"
        ]
    },
    {
        "codepoints": "🍎",
        "name": "red apple",
        "shortcodes": [
            ":red_apple:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "apple",
            "fruit",
            "red"
        ]
    },
    {
        "codepoints": "🍏",
        "name": "green apple",
        "shortcodes": [
            ":green_apple:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "apple",
            "fruit",
            "green"
        ]
    },
    {
        "codepoints": "🍐",
        "name": "pear",
        "shortcodes": [
            ":pear:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "pear"
        ]
    },
    {
        "codepoints": "🍑",
        "name": "peach",
        "shortcodes": [
            ":peach:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "peach"
        ]
    },
    {
        "codepoints": "🍒",
        "name": "cherries",
        "shortcodes": [
            ":cherries:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "berries",
            "cherries",
            "cherry",
            "fruit",
            "red"
        ]
    },
    {
        "codepoints": "🍓",
        "name": "strawberry",
        "shortcodes": [
            ":strawberry:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "berry",
            "fruit",
            "strawberry"
        ]
    },
    {
        "codepoints": "🫐",
        "name": "blueberries",
        "shortcodes": [
            ":blueberries:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "berry",
            "bilberry",
            "blue",
            "blueberries",
            "blueberry"
        ]
    },
    {
        "codepoints": "🥝",
        "name": "kiwi fruit",
        "shortcodes": [
            ":kiwi_fruit:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "food",
            "fruit",
            "kiwi fruit",
            "kiwi"
        ]
    },
    {
        "codepoints": "🍅",
        "name": "tomato",
        "shortcodes": [
            ":tomato:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fruit",
            "tomato",
            "vegetable"
        ]
    },
    {
        "codepoints": "🫒",
        "name": "olive",
        "shortcodes": [
            ":olive:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "food",
            "olive"
        ]
    },
    {
        "codepoints": "🥥",
        "name": "coconut",
        "shortcodes": [
            ":coconut:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "coconut",
            "palm",
            "piña colada"
        ]
    },
    {
        "codepoints": "🥑",
        "name": "avocado",
        "shortcodes": [
            ":avocado:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "avocado",
            "food",
            "fruit"
        ]
    },
    {
        "codepoints": "🍆",
        "name": "eggplant",
        "shortcodes": [
            ":eggplant:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "aubergine",
            "eggplant",
            "vegetable"
        ]
    },
    {
        "codepoints": "🥔",
        "name": "potato",
        "shortcodes": [
            ":potato:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "food",
            "potato",
            "vegetable"
        ]
    },
    {
        "codepoints": "🥕",
        "name": "carrot",
        "shortcodes": [
            ":carrot:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "carrot",
            "food",
            "vegetable"
        ]
    },
    {
        "codepoints": "🌽",
        "name": "ear of corn",
        "shortcodes": [
            ":ear_of_corn:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "corn",
            "corn on the cob",
            "sweetcorn",
            "ear",
            "ear of corn",
            "maize",
            "maze"
        ]
    },
    {
        "codepoints": "🌶️",
        "name": "hot pepper",
        "shortcodes": [
            ":hot_pepper:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "chilli",
            "hot pepper",
            "pepper",
            "hot"
        ]
    },
    {
        "codepoints": "🫑",
        "name": "bell pepper",
        "shortcodes": [
            ":bell_pepper:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bell pepper",
            "capsicum",
            "pepper",
            "vegetable",
            "sweet pepper"
        ]
    },
    {
        "codepoints": "🥒",
        "name": "cucumber",
        "shortcodes": [
            ":cucumber:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cucumber",
            "food",
            "pickle",
            "vegetable"
        ]
    },
    {
        "codepoints": "🥬",
        "name": "leafy green",
        "shortcodes": [
            ":leafy_green:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bok choy",
            "leafy green",
            "pak choi",
            "cabbage",
            "kale",
            "lettuce"
        ]
    },
    {
        "codepoints": "🥦",
        "name": "broccoli",
        "shortcodes": [
            ":broccoli:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "broccoli",
            "wild cabbage"
        ]
    },
    {
        "codepoints": "🧄",
        "name": "garlic",
        "shortcodes": [
            ":garlic:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "flavouring",
            "garlic",
            "flavoring"
        ]
    },
    {
        "codepoints": "🧅",
        "name": "onion",
        "shortcodes": [
            ":onion:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "flavouring",
            "onion",
            "flavoring"
        ]
    },
    {
        "codepoints": "🍄",
        "name": "mushroom",
        "shortcodes": [
            ":mushroom:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "mushroom",
            "toadstool"
        ]
    },
    {
        "codepoints": "🥜",
        "name": "peanuts",
        "shortcodes": [
            ":peanuts:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "food",
            "nut",
            "nuts",
            "peanut",
            "peanuts",
            "vegetable"
        ]
    },
    {
        "codepoints": "🫘",
        "name": "beans",
        "shortcodes": [
            ":beans:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "food",
            "kidney bean",
            "kidney beans",
            "legume",
            "beans",
            "kidney"
        ]
    },
    {
        "codepoints": "🌰",
        "name": "chestnut",
        "shortcodes": [
            ":chestnut:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "chestnut",
            "plant",
            "nut"
        ]
    },
    {
        "codepoints": "🍞",
        "name": "bread",
        "shortcodes": [
            ":bread:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bread",
            "loaf"
        ]
    },
    {
        "codepoints": "🥐",
        "name": "croissant",
        "shortcodes": [
            ":croissant:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bread",
            "breakfast",
            "croissant",
            "food",
            "french",
            "roll",
            "crescent roll",
            "French"
        ]
    },
    {
        "codepoints": "🥖",
        "name": "baguette bread",
        "shortcodes": [
            ":baguette_bread:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "baguette",
            "bread",
            "food",
            "french",
            "French stick",
            "French"
        ]
    },
    {
        "codepoints": "🫓",
        "name": "flatbread",
        "shortcodes": [
            ":flatbread:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "arepa",
            "flatbread",
            "lavash",
            "naan",
            "pita"
        ]
    },
    {
        "codepoints": "🥨",
        "name": "pretzel",
        "shortcodes": [
            ":pretzel:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "pretzel",
            "twisted"
        ]
    },
    {
        "codepoints": "🥯",
        "name": "bagel",
        "shortcodes": [
            ":bagel:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bagel",
            "bakery",
            "breakfast",
            "schmear"
        ]
    },
    {
        "codepoints": "🥞",
        "name": "pancakes",
        "shortcodes": [
            ":pancakes:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "breakfast",
            "crêpe",
            "food",
            "hotcake",
            "pancake",
            "pancakes"
        ]
    },
    {
        "codepoints": "🧇",
        "name": "waffle",
        "shortcodes": [
            ":waffle:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "waffle",
            "waffle with butter",
            "breakfast",
            "indecisive",
            "iron",
            "unclear",
            "vague"
        ]
    },
    {
        "codepoints": "🧀",
        "name": "cheese wedge",
        "shortcodes": [
            ":cheese_wedge:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cheese",
            "cheese wedge"
        ]
    },
    {
        "codepoints": "🍖",
        "name": "meat on bone",
        "shortcodes": [
            ":meat_on_bone:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bone",
            "meat",
            "meat on bone"
        ]
    },
    {
        "codepoints": "🍗",
        "name": "poultry leg",
        "shortcodes": [
            ":poultry_leg:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bone",
            "chicken",
            "drumstick",
            "leg",
            "poultry"
        ]
    },
    {
        "codepoints": "🥩",
        "name": "cut of meat",
        "shortcodes": [
            ":cut_of_meat:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "chop",
            "cut of meat",
            "lambchop",
            "porkchop",
            "steak",
            "lamb chop",
            "pork chop"
        ]
    },
    {
        "codepoints": "🥓",
        "name": "bacon",
        "shortcodes": [
            ":bacon:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bacon",
            "breakfast",
            "food",
            "meat"
        ]
    },
    {
        "codepoints": "🍔",
        "name": "hamburger",
        "shortcodes": [
            ":hamburger:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "beefburger",
            "burger",
            "hamburger"
        ]
    },
    {
        "codepoints": "🍟",
        "name": "french fries",
        "shortcodes": [
            ":french_fries:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "chips",
            "french fries",
            "fries",
            "french",
            "French"
        ]
    },
    {
        "codepoints": "🍕",
        "name": "pizza",
        "shortcodes": [
            ":pizza:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cheese",
            "pizza",
            "slice"
        ]
    },
    {
        "codepoints": "🌭",
        "name": "hot dog",
        "shortcodes": [
            ":hot_dog:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "frankfurter",
            "hot dog",
            "hotdog",
            "sausage"
        ]
    },
    {
        "codepoints": "🥪",
        "name": "sandwich",
        "shortcodes": [
            ":sandwich:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bread",
            "sandwich"
        ]
    },
    {
        "codepoints": "🌮",
        "name": "taco",
        "shortcodes": [
            ":taco:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "mexican",
            "taco",
            "Mexican"
        ]
    },
    {
        "codepoints": "🌯",
        "name": "burrito",
        "shortcodes": [
            ":burrito:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "burrito",
            "mexican",
            "wrap",
            "Mexican"
        ]
    },
    {
        "codepoints": "🫔",
        "name": "tamale",
        "shortcodes": [
            ":tamale:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "mexican",
            "tamale",
            "wrapped"
        ]
    },
    {
        "codepoints": "🥙",
        "name": "stuffed flatbread",
        "shortcodes": [
            ":stuffed_flatbread:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "falafel",
            "flatbread",
            "food",
            "gyro",
            "kebab",
            "pita",
            "pita roll",
            "stuffed"
        ]
    },
    {
        "codepoints": "🧆",
        "name": "falafel",
        "shortcodes": [
            ":falafel:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "chickpea",
            "falafel",
            "meatball",
            "chick pea"
        ]
    },
    {
        "codepoints": "🥚",
        "name": "egg",
        "shortcodes": [
            ":egg:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "breakfast",
            "egg",
            "food"
        ]
    },
    {
        "codepoints": "🍳",
        "name": "cooking",
        "shortcodes": [
            ":cooking:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "breakfast",
            "cooking",
            "egg",
            "frying",
            "pan"
        ]
    },
    {
        "codepoints": "🥘",
        "name": "shallow pan of food",
        "shortcodes": [
            ":shallow_pan_of_food:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "casserole",
            "food",
            "paella",
            "pan",
            "shallow",
            "shallow pan of food"
        ]
    },
    {
        "codepoints": "🍲",
        "name": "pot of food",
        "shortcodes": [
            ":pot_of_food:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "pot",
            "pot of food",
            "stew"
        ]
    },
    {
        "codepoints": "🫕",
        "name": "fondue",
        "shortcodes": [
            ":fondue:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cheese",
            "chocolate",
            "fondue",
            "melted",
            "pot",
            "Swiss"
        ]
    },
    {
        "codepoints": "🥣",
        "name": "bowl with spoon",
        "shortcodes": [
            ":bowl_with_spoon:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bowl with spoon",
            "breakfast",
            "cereal",
            "congee"
        ]
    },
    {
        "codepoints": "🥗",
        "name": "green salad",
        "shortcodes": [
            ":green_salad:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "food",
            "garden",
            "salad",
            "green"
        ]
    },
    {
        "codepoints": "🍿",
        "name": "popcorn",
        "shortcodes": [
            ":popcorn:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "popcorn"
        ]
    },
    {
        "codepoints": "🧈",
        "name": "butter",
        "shortcodes": [
            ":butter:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "butter",
            "dairy"
        ]
    },
    {
        "codepoints": "🧂",
        "name": "salt",
        "shortcodes": [
            ":salt:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "condiment",
            "salt",
            "shaker"
        ]
    },
    {
        "codepoints": "🥫",
        "name": "canned food",
        "shortcodes": [
            ":canned_food:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "can",
            "canned food"
        ]
    },
    {
        "codepoints": "🍱",
        "name": "bento box",
        "shortcodes": [
            ":bento_box:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bento",
            "box"
        ]
    },
    {
        "codepoints": "🍘",
        "name": "rice cracker",
        "shortcodes": [
            ":rice_cracker:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cracker",
            "rice"
        ]
    },
    {
        "codepoints": "🍙",
        "name": "rice ball",
        "shortcodes": [
            ":rice_ball:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "ball",
            "Japanese",
            "rice"
        ]
    },
    {
        "codepoints": "🍚",
        "name": "cooked rice",
        "shortcodes": [
            ":cooked_rice:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cooked",
            "rice"
        ]
    },
    {
        "codepoints": "🍛",
        "name": "curry rice",
        "shortcodes": [
            ":curry_rice:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "curry",
            "rice"
        ]
    },
    {
        "codepoints": "🍜",
        "name": "steaming bowl",
        "shortcodes": [
            ":steaming_bowl:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bowl",
            "noodle",
            "ramen",
            "steaming"
        ]
    },
    {
        "codepoints": "🍝",
        "name": "spaghetti",
        "shortcodes": [
            ":spaghetti:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "pasta",
            "spaghetti"
        ]
    },
    {
        "codepoints": "🍠",
        "name": "roasted sweet potato",
        "shortcodes": [
            ":roasted_sweet_potato:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "potato",
            "roasted",
            "sweet"
        ]
    },
    {
        "codepoints": "🍢",
        "name": "oden",
        "shortcodes": [
            ":oden:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "kebab",
            "oden",
            "seafood",
            "skewer",
            "stick"
        ]
    },
    {
        "codepoints": "🍣",
        "name": "sushi",
        "shortcodes": [
            ":sushi:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "sushi"
        ]
    },
    {
        "codepoints": "🍤",
        "name": "fried shrimp",
        "shortcodes": [
            ":fried_shrimp:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "battered",
            "fried",
            "prawn",
            "shrimp",
            "tempura"
        ]
    },
    {
        "codepoints": "🍥",
        "name": "fish cake with swirl",
        "shortcodes": [
            ":fish_cake_with_swirl:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cake",
            "fish",
            "fish cake with swirl",
            "pastry",
            "swirl",
            "narutomaki"
        ]
    },
    {
        "codepoints": "🥮",
        "name": "moon cake",
        "shortcodes": [
            ":moon_cake:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "autumn",
            "festival",
            "moon cake",
            "yuèbǐng"
        ]
    },
    {
        "codepoints": "🍡",
        "name": "dango",
        "shortcodes": [
            ":dango:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "dango",
            "dessert",
            "Japanese",
            "skewer",
            "stick",
            "sweet"
        ]
    },
    {
        "codepoints": "🥟",
        "name": "dumpling",
        "shortcodes": [
            ":dumpling:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "dumpling",
            "empanada",
            "gyōza",
            "pastie",
            "samosa",
            "jiaozi",
            "pierogi",
            "potsticker"
        ]
    },
    {
        "codepoints": "🥠",
        "name": "fortune cookie",
        "shortcodes": [
            ":fortune_cookie:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "fortune cookie",
            "prophecy"
        ]
    },
    {
        "codepoints": "🥡",
        "name": "takeout box",
        "shortcodes": [
            ":takeout_box:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "takeaway container",
            "takeout",
            "oyster pail",
            "takeout box",
            "takeaway box"
        ]
    },
    {
        "codepoints": "🦀",
        "name": "crab",
        "shortcodes": [
            ":crab:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "crab",
            "crustacean",
            "seafood",
            "shellfish",
            "Cancer",
            "zodiac"
        ]
    },
    {
        "codepoints": "🦞",
        "name": "lobster",
        "shortcodes": [
            ":lobster:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bisque",
            "claws",
            "lobster",
            "seafood",
            "shellfish"
        ]
    },
    {
        "codepoints": "🦐",
        "name": "shrimp",
        "shortcodes": [
            ":shrimp:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "prawn",
            "seafood",
            "shellfish",
            "shrimp",
            "food",
            "small"
        ]
    },
    {
        "codepoints": "🦑",
        "name": "squid",
        "shortcodes": [
            ":squid:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "decapod",
            "seafood",
            "squid",
            "food",
            "molusc"
        ]
    },
    {
        "codepoints": "🦪",
        "name": "oyster",
        "shortcodes": [
            ":oyster:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "diving",
            "oyster",
            "pearl"
        ]
    },
    {
        "codepoints": "🍦",
        "name": "soft ice cream",
        "shortcodes": [
            ":soft_ice_cream:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cream",
            "dessert",
            "ice cream",
            "soft serve",
            "sweet",
            "ice",
            "icecream",
            "soft"
        ]
    },
    {
        "codepoints": "🍧",
        "name": "shaved ice",
        "shortcodes": [
            ":shaved_ice:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "dessert",
            "granita",
            "ice",
            "sweet",
            "shaved"
        ]
    },
    {
        "codepoints": "🍨",
        "name": "ice cream",
        "shortcodes": [
            ":ice_cream:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cream",
            "dessert",
            "ice cream",
            "sweet",
            "ice"
        ]
    },
    {
        "codepoints": "🍩",
        "name": "doughnut",
        "shortcodes": [
            ":doughnut:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "breakfast",
            "dessert",
            "donut",
            "doughnut",
            "sweet"
        ]
    },
    {
        "codepoints": "🍪",
        "name": "cookie",
        "shortcodes": [
            ":cookie:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "biscuit",
            "cookie",
            "dessert",
            "sweet"
        ]
    },
    {
        "codepoints": "🎂",
        "name": "birthday cake",
        "shortcodes": [
            ":birthday_cake:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "birthday",
            "cake",
            "celebration",
            "dessert",
            "pastry",
            "sweet"
        ]
    },
    {
        "codepoints": "🍰",
        "name": "shortcake",
        "shortcodes": [
            ":shortcake:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cake",
            "dessert",
            "pastry",
            "shortcake",
            "slice",
            "sweet"
        ]
    },
    {
        "codepoints": "🧁",
        "name": "cupcake",
        "shortcodes": [
            ":cupcake:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bakery",
            "cupcake",
            "sweet"
        ]
    },
    {
        "codepoints": "🥧",
        "name": "pie",
        "shortcodes": [
            ":pie:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "filling",
            "pastry",
            "pie"
        ]
    },
    {
        "codepoints": "🍫",
        "name": "chocolate bar",
        "shortcodes": [
            ":chocolate_bar:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bar",
            "chocolate",
            "dessert",
            "sweet"
        ]
    },
    {
        "codepoints": "🍬",
        "name": "candy",
        "shortcodes": [
            ":candy:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "candy",
            "dessert",
            "sweet",
            "sweets"
        ]
    },
    {
        "codepoints": "🍭",
        "name": "lollipop",
        "shortcodes": [
            ":lollipop:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "candy",
            "dessert",
            "lollipop",
            "sweet"
        ]
    },
    {
        "codepoints": "🍮",
        "name": "custard",
        "shortcodes": [
            ":custard:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "baked custard",
            "dessert",
            "pudding",
            "sweet",
            "custard"
        ]
    },
    {
        "codepoints": "🍯",
        "name": "honey pot",
        "shortcodes": [
            ":honey_pot:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "honey",
            "honeypot",
            "pot",
            "sweet"
        ]
    },
    {
        "codepoints": "🍼",
        "name": "baby bottle",
        "shortcodes": [
            ":baby_bottle:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "baby",
            "bottle",
            "drink",
            "milk"
        ]
    },
    {
        "codepoints": "🥛",
        "name": "glass of milk",
        "shortcodes": [
            ":glass_of_milk:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "drink",
            "glass",
            "glass of milk",
            "milk"
        ]
    },
    {
        "codepoints": "☕",
        "name": "hot beverage",
        "shortcodes": [
            ":hot_beverage:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "beverage",
            "coffee",
            "drink",
            "hot",
            "steaming",
            "tea"
        ]
    },
    {
        "codepoints": "🫖",
        "name": "teapot",
        "shortcodes": [
            ":teapot:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "drink",
            "pot",
            "tea",
            "teapot"
        ]
    },
    {
        "codepoints": "🍵",
        "name": "teacup without handle",
        "shortcodes": [
            ":teacup_without_handle:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "beverage",
            "cup",
            "drink",
            "tea",
            "teacup",
            "teacup without handle"
        ]
    },
    {
        "codepoints": "🍶",
        "name": "sake",
        "shortcodes": [
            ":sake:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bar",
            "beverage",
            "bottle",
            "cup",
            "drink",
            "sake",
            "saké"
        ]
    },
    {
        "codepoints": "🍾",
        "name": "bottle with popping cork",
        "shortcodes": [
            ":bottle_with_popping_cork:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bar",
            "bottle",
            "bottle with popping cork",
            "cork",
            "drink",
            "popping"
        ]
    },
    {
        "codepoints": "🍷",
        "name": "wine glass",
        "shortcodes": [
            ":wine_glass:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bar",
            "beverage",
            "drink",
            "glass",
            "wine"
        ]
    },
    {
        "codepoints": "🍸",
        "name": "cocktail glass",
        "shortcodes": [
            ":cocktail_glass:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bar",
            "cocktail",
            "drink",
            "glass"
        ]
    },
    {
        "codepoints": "🍹",
        "name": "tropical drink",
        "shortcodes": [
            ":tropical_drink:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bar",
            "drink",
            "tropical"
        ]
    },
    {
        "codepoints": "🍺",
        "name": "beer mug",
        "shortcodes": [
            ":beer_mug:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bar",
            "beer",
            "drink",
            "mug"
        ]
    },
    {
        "codepoints": "🍻",
        "name": "clinking beer mugs",
        "shortcodes": [
            ":clinking_beer_mugs:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bar",
            "beer",
            "clink",
            "clinking beer mugs",
            "drink",
            "mug"
        ]
    },
    {
        "codepoints": "🥂",
        "name": "clinking glasses",
        "shortcodes": [
            ":clinking_glasses:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "celebrate",
            "clink",
            "clinking glasses",
            "drink",
            "glass"
        ]
    },
    {
        "codepoints": "🥃",
        "name": "tumbler glass",
        "shortcodes": [
            ":tumbler_glass:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "glass",
            "liquor",
            "shot",
            "tumbler",
            "whisky"
        ]
    },
    {
        "codepoints": "🫗",
        "name": "pouring liquid",
        "shortcodes": [
            ":pouring_liquid:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "drink",
            "empty",
            "glass",
            "pouring liquid",
            "spill"
        ]
    },
    {
        "codepoints": "🥤",
        "name": "cup with straw",
        "shortcodes": [
            ":cup_with_straw:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cup with straw",
            "juice",
            "soda"
        ]
    },
    {
        "codepoints": "🧋",
        "name": "bubble tea",
        "shortcodes": [
            ":bubble_tea:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "bubble",
            "milk",
            "pearl",
            "tea"
        ]
    },
    {
        "codepoints": "🧃",
        "name": "beverage box",
        "shortcodes": [
            ":beverage_box:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "drink carton",
            "juice box",
            "popper",
            "beverage",
            "box",
            "juice",
            "straw",
            "sweet"
        ]
    },
    {
        "codepoints": "🧉",
        "name": "mate",
        "shortcodes": [
            ":mate:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "drink",
            "mate",
            "maté"
        ]
    },
    {
        "codepoints": "🧊",
        "name": "ice",
        "shortcodes": [
            ":ice:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cold",
            "ice",
            "ice cube",
            "iceberg"
        ]
    },
    {
        "codepoints": "🥢",
        "name": "chopsticks",
        "shortcodes": [
            ":chopsticks:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "chopsticks",
            "pair of chopsticks",
            "hashi"
        ]
    },
    {
        "codepoints": "🍽️",
        "name": "fork and knife with plate",
        "shortcodes": [
            ":fork_and_knife_with_plate:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cooking",
            "fork",
            "fork and knife with plate",
            "knife",
            "plate"
        ]
    },
    {
        "codepoints": "🍴",
        "name": "fork and knife",
        "shortcodes": [
            ":fork_and_knife:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cooking",
            "cutlery",
            "fork",
            "fork and knife",
            "knife",
            "knife and fork"
        ]
    },
    {
        "codepoints": "🥄",
        "name": "spoon",
        "shortcodes": [
            ":spoon:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "spoon",
            "tableware"
        ]
    },
    {
        "codepoints": "🔪",
        "name": "kitchen knife",
        "shortcodes": [
            ":kitchen_knife:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "cooking",
            "hocho",
            "kitchen knife",
            "knife",
            "tool",
            "weapon"
        ]
    },
    {
        "codepoints": "🫙",
        "name": "jar",
        "shortcodes": [
            ":jar:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "condiment",
            "container",
            "empty",
            "jar",
            "sauce",
            "store"
        ]
    },
    {
        "codepoints": "🏺",
        "name": "amphora",
        "shortcodes": [
            ":amphora:"
        ],
        "emoticons": [],
        "category": "Food & Drink",
        "keywords": [
            "amphora",
            "Aquarius",
            "cooking",
            "drink",
            "jug",
            "zodiac",
            "jar"
        ]
    },
    {
        "codepoints": "🌍",
        "name": "globe showing Europe-Africa",
        "shortcodes": [
            ":globe_showing_Europe-Africa:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Africa",
            "earth",
            "Europe",
            "globe",
            "globe showing Europe-Africa",
            "world"
        ]
    },
    {
        "codepoints": "🌎",
        "name": "globe showing Americas",
        "shortcodes": [
            ":globe_showing_Americas:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Americas",
            "earth",
            "globe",
            "globe showing Americas",
            "world"
        ]
    },
    {
        "codepoints": "🌏",
        "name": "globe showing Asia-Australia",
        "shortcodes": [
            ":globe_showing_Asia-Australia:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Asia",
            "Australia",
            "earth",
            "globe",
            "globe showing Asia-Australia",
            "world"
        ]
    },
    {
        "codepoints": "🌐",
        "name": "globe with meridians",
        "shortcodes": [
            ":globe_with_meridians:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "earth",
            "globe",
            "globe with meridians",
            "meridians",
            "world"
        ]
    },
    {
        "codepoints": "🗺️",
        "name": "world map",
        "shortcodes": [
            ":world_map:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "map",
            "world"
        ]
    },
    {
        "codepoints": "🗾",
        "name": "map of Japan",
        "shortcodes": [
            ":map_of_Japan:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Japan",
            "map",
            "map of Japan"
        ]
    },
    {
        "codepoints": "🧭",
        "name": "compass",
        "shortcodes": [
            ":compass:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "compass",
            "magnetic",
            "navigation",
            "orienteering"
        ]
    },
    {
        "codepoints": "🏔️",
        "name": "snow-capped mountain",
        "shortcodes": [
            ":snow-capped_mountain:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cold",
            "mountain",
            "snow",
            "snow-capped mountain"
        ]
    },
    {
        "codepoints": "⛰️",
        "name": "mountain",
        "shortcodes": [
            ":mountain:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "mountain"
        ]
    },
    {
        "codepoints": "🌋",
        "name": "volcano",
        "shortcodes": [
            ":volcano:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "eruption",
            "mountain",
            "volcano"
        ]
    },
    {
        "codepoints": "🗻",
        "name": "mount fuji",
        "shortcodes": [
            ":mount_fuji:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Fuji",
            "mount Fuji",
            "mountain",
            "fuji",
            "mount fuji",
            "Mount Fuji"
        ]
    },
    {
        "codepoints": "🏕️",
        "name": "camping",
        "shortcodes": [
            ":camping:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "camping"
        ]
    },
    {
        "codepoints": "🏖️",
        "name": "beach with umbrella",
        "shortcodes": [
            ":beach_with_umbrella:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "beach",
            "beach with umbrella",
            "umbrella"
        ]
    },
    {
        "codepoints": "🏜️",
        "name": "desert",
        "shortcodes": [
            ":desert:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "desert"
        ]
    },
    {
        "codepoints": "🏝️",
        "name": "desert island",
        "shortcodes": [
            ":desert_island:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "desert",
            "island"
        ]
    },
    {
        "codepoints": "🏞️",
        "name": "national park",
        "shortcodes": [
            ":national_park:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "national park",
            "park"
        ]
    },
    {
        "codepoints": "🏟️",
        "name": "stadium",
        "shortcodes": [
            ":stadium:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "arena",
            "stadium"
        ]
    },
    {
        "codepoints": "🏛️",
        "name": "classical building",
        "shortcodes": [
            ":classical_building:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "classical",
            "classical building",
            "column"
        ]
    },
    {
        "codepoints": "🏗️",
        "name": "building construction",
        "shortcodes": [
            ":building_construction:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "building construction",
            "construction"
        ]
    },
    {
        "codepoints": "🧱",
        "name": "brick",
        "shortcodes": [
            ":brick:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "brick",
            "bricks",
            "clay",
            "mortar",
            "wall"
        ]
    },
    {
        "codepoints": "🪨",
        "name": "rock",
        "shortcodes": [
            ":rock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "boulder",
            "heavy",
            "rock",
            "solid",
            "stone"
        ]
    },
    {
        "codepoints": "🪵",
        "name": "wood",
        "shortcodes": [
            ":wood:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "log",
            "lumber",
            "timber",
            "wood"
        ]
    },
    {
        "codepoints": "🛖",
        "name": "hut",
        "shortcodes": [
            ":hut:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "house",
            "hut",
            "roundhouse",
            "yurt"
        ]
    },
    {
        "codepoints": "🏘️",
        "name": "houses",
        "shortcodes": [
            ":houses:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "houses"
        ]
    },
    {
        "codepoints": "🏚️",
        "name": "derelict house",
        "shortcodes": [
            ":derelict_house:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "derelict",
            "house"
        ]
    },
    {
        "codepoints": "🏠",
        "name": "house",
        "shortcodes": [
            ":house:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "home",
            "house"
        ]
    },
    {
        "codepoints": "🏡",
        "name": "house with garden",
        "shortcodes": [
            ":house_with_garden:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "garden",
            "home",
            "house",
            "house with garden"
        ]
    },
    {
        "codepoints": "🏢",
        "name": "office building",
        "shortcodes": [
            ":office_building:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "building",
            "office building"
        ]
    },
    {
        "codepoints": "🏣",
        "name": "Japanese post office",
        "shortcodes": [
            ":Japanese_post_office:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Japanese",
            "Japanese post office",
            "post"
        ]
    },
    {
        "codepoints": "🏤",
        "name": "post office",
        "shortcodes": [
            ":post_office:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "European",
            "post",
            "post office"
        ]
    },
    {
        "codepoints": "🏥",
        "name": "hospital",
        "shortcodes": [
            ":hospital:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "doctor",
            "hospital",
            "medicine"
        ]
    },
    {
        "codepoints": "🏦",
        "name": "bank",
        "shortcodes": [
            ":bank:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bank",
            "building"
        ]
    },
    {
        "codepoints": "🏨",
        "name": "hotel",
        "shortcodes": [
            ":hotel:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "building",
            "hotel"
        ]
    },
    {
        "codepoints": "🏩",
        "name": "love hotel",
        "shortcodes": [
            ":love_hotel:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "hotel",
            "love"
        ]
    },
    {
        "codepoints": "🏪",
        "name": "convenience store",
        "shortcodes": [
            ":convenience_store:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "convenience",
            "store",
            "dépanneur"
        ]
    },
    {
        "codepoints": "🏫",
        "name": "school",
        "shortcodes": [
            ":school:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "building",
            "school"
        ]
    },
    {
        "codepoints": "🏬",
        "name": "department store",
        "shortcodes": [
            ":department_store:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "department",
            "store"
        ]
    },
    {
        "codepoints": "🏭",
        "name": "factory",
        "shortcodes": [
            ":factory:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "building",
            "factory"
        ]
    },
    {
        "codepoints": "🏯",
        "name": "Japanese castle",
        "shortcodes": [
            ":Japanese_castle:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "castle",
            "Japanese"
        ]
    },
    {
        "codepoints": "🏰",
        "name": "castle",
        "shortcodes": [
            ":castle:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "castle",
            "European"
        ]
    },
    {
        "codepoints": "💒",
        "name": "wedding",
        "shortcodes": [
            ":wedding:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "chapel",
            "romance",
            "wedding"
        ]
    },
    {
        "codepoints": "🗼",
        "name": "Tokyo tower",
        "shortcodes": [
            ":Tokyo_tower:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Tokyo",
            "tower",
            "Tower"
        ]
    },
    {
        "codepoints": "🗽",
        "name": "Statue of Liberty",
        "shortcodes": [
            ":Statue_of_Liberty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "liberty",
            "statue",
            "Statue of Liberty",
            "Liberty",
            "Statue"
        ]
    },
    {
        "codepoints": "⛪",
        "name": "church",
        "shortcodes": [
            ":church:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Christian",
            "church",
            "cross",
            "religion"
        ]
    },
    {
        "codepoints": "🕌",
        "name": "mosque",
        "shortcodes": [
            ":mosque:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Islam",
            "mosque",
            "Muslim",
            "religion",
            "islam"
        ]
    },
    {
        "codepoints": "🛕",
        "name": "hindu temple",
        "shortcodes": [
            ":hindu_temple:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "hindu",
            "temple",
            "Hindu"
        ]
    },
    {
        "codepoints": "🕍",
        "name": "synagogue",
        "shortcodes": [
            ":synagogue:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Jew",
            "Jewish",
            "religion",
            "synagogue",
            "temple",
            "shul"
        ]
    },
    {
        "codepoints": "⛩️",
        "name": "shinto shrine",
        "shortcodes": [
            ":shinto_shrine:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "religion",
            "Shinto",
            "shrine",
            "shinto"
        ]
    },
    {
        "codepoints": "🕋",
        "name": "kaaba",
        "shortcodes": [
            ":kaaba:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Islam",
            "Kaaba",
            "Muslim",
            "religion",
            "islam",
            "kaaba"
        ]
    },
    {
        "codepoints": "⛲",
        "name": "fountain",
        "shortcodes": [
            ":fountain:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "fountain"
        ]
    },
    {
        "codepoints": "⛺",
        "name": "tent",
        "shortcodes": [
            ":tent:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "camping",
            "tent"
        ]
    },
    {
        "codepoints": "🌁",
        "name": "foggy",
        "shortcodes": [
            ":foggy:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "fog",
            "foggy"
        ]
    },
    {
        "codepoints": "🌃",
        "name": "night with stars",
        "shortcodes": [
            ":night_with_stars:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "night",
            "night with stars",
            "star"
        ]
    },
    {
        "codepoints": "🏙️",
        "name": "cityscape",
        "shortcodes": [
            ":cityscape:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "city",
            "cityscape"
        ]
    },
    {
        "codepoints": "🌄",
        "name": "sunrise over mountains",
        "shortcodes": [
            ":sunrise_over_mountains:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "morning",
            "mountain",
            "sun",
            "sunrise",
            "sunrise over mountains"
        ]
    },
    {
        "codepoints": "🌅",
        "name": "sunrise",
        "shortcodes": [
            ":sunrise:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "morning",
            "sun",
            "sunrise"
        ]
    },
    {
        "codepoints": "🌆",
        "name": "cityscape at dusk",
        "shortcodes": [
            ":cityscape_at_dusk:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "city",
            "cityscape at dusk",
            "dusk",
            "evening",
            "landscape",
            "sunset"
        ]
    },
    {
        "codepoints": "🌇",
        "name": "sunset",
        "shortcodes": [
            ":sunset:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "dusk",
            "sun",
            "sunset"
        ]
    },
    {
        "codepoints": "🌉",
        "name": "bridge at night",
        "shortcodes": [
            ":bridge_at_night:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bridge",
            "bridge at night",
            "night"
        ]
    },
    {
        "codepoints": "♨️",
        "name": "hot springs",
        "shortcodes": [
            ":hot_springs:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "hot",
            "hotsprings",
            "springs",
            "steaming"
        ]
    },
    {
        "codepoints": "🎠",
        "name": "carousel horse",
        "shortcodes": [
            ":carousel_horse:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "carousel",
            "horse",
            "merry-go-round"
        ]
    },
    {
        "codepoints": "🛝",
        "name": "playground slide",
        "shortcodes": [
            ":playground_slide:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "amusement park",
            "play",
            "playground slide"
        ]
    },
    {
        "codepoints": "🎡",
        "name": "ferris wheel",
        "shortcodes": [
            ":ferris_wheel:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "amusement park",
            "ferris",
            "wheel",
            "Ferris",
            "theme park"
        ]
    },
    {
        "codepoints": "🎢",
        "name": "roller coaster",
        "shortcodes": [
            ":roller_coaster:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "amusement park",
            "coaster",
            "roller"
        ]
    },
    {
        "codepoints": "💈",
        "name": "barber pole",
        "shortcodes": [
            ":barber_pole:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "barber",
            "haircut",
            "pole"
        ]
    },
    {
        "codepoints": "🎪",
        "name": "circus tent",
        "shortcodes": [
            ":circus_tent:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "big top",
            "circus",
            "tent"
        ]
    },
    {
        "codepoints": "🚂",
        "name": "locomotive",
        "shortcodes": [
            ":locomotive:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "engine",
            "locomotive",
            "railway",
            "steam",
            "train"
        ]
    },
    {
        "codepoints": "🚃",
        "name": "railway car",
        "shortcodes": [
            ":railway_car:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "car",
            "electric",
            "railway",
            "train",
            "tram",
            "trolley bus",
            "trolleybus",
            "railway carriage"
        ]
    },
    {
        "codepoints": "🚄",
        "name": "high-speed train",
        "shortcodes": [
            ":high-speed_train:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "high-speed train",
            "railway",
            "shinkansen",
            "speed",
            "train",
            "Shinkansen"
        ]
    },
    {
        "codepoints": "🚅",
        "name": "bullet train",
        "shortcodes": [
            ":bullet_train:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bullet",
            "railway",
            "shinkansen",
            "speed",
            "train",
            "Shinkansen"
        ]
    },
    {
        "codepoints": "🚆",
        "name": "train",
        "shortcodes": [
            ":train:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "railway",
            "train"
        ]
    },
    {
        "codepoints": "🚇",
        "name": "metro",
        "shortcodes": [
            ":metro:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "metro",
            "subway"
        ]
    },
    {
        "codepoints": "🚈",
        "name": "light rail",
        "shortcodes": [
            ":light_rail:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "light rail",
            "railway"
        ]
    },
    {
        "codepoints": "🚉",
        "name": "station",
        "shortcodes": [
            ":station:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "railway",
            "station",
            "train"
        ]
    },
    {
        "codepoints": "🚊",
        "name": "tram",
        "shortcodes": [
            ":tram:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "light rail",
            "oncoming",
            "oncoming light rail",
            "tram",
            "trolleybus",
            "car",
            "streetcar",
            "tramcar",
            "trolley",
            "trolley bus"
        ]
    },
    {
        "codepoints": "🚝",
        "name": "monorail",
        "shortcodes": [
            ":monorail:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "monorail",
            "vehicle"
        ]
    },
    {
        "codepoints": "🚞",
        "name": "mountain railway",
        "shortcodes": [
            ":mountain_railway:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "car",
            "mountain",
            "railway"
        ]
    },
    {
        "codepoints": "🚋",
        "name": "tram car",
        "shortcodes": [
            ":tram_car:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "car",
            "tram",
            "trolley bus",
            "trolleybus",
            "streetcar",
            "tramcar",
            "trolley"
        ]
    },
    {
        "codepoints": "🚌",
        "name": "bus",
        "shortcodes": [
            ":bus:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bus",
            "vehicle"
        ]
    },
    {
        "codepoints": "🚍",
        "name": "oncoming bus",
        "shortcodes": [
            ":oncoming_bus:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bus",
            "oncoming"
        ]
    },
    {
        "codepoints": "🚎",
        "name": "trolleybus",
        "shortcodes": [
            ":trolleybus:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bus",
            "tram",
            "trolley",
            "trolleybus",
            "streetcar"
        ]
    },
    {
        "codepoints": "🚐",
        "name": "minibus",
        "shortcodes": [
            ":minibus:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bus",
            "minibus"
        ]
    },
    {
        "codepoints": "🚑",
        "name": "ambulance",
        "shortcodes": [
            ":ambulance:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "ambulance",
            "vehicle"
        ]
    },
    {
        "codepoints": "🚒",
        "name": "fire engine",
        "shortcodes": [
            ":fire_engine:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "engine",
            "fire",
            "truck"
        ]
    },
    {
        "codepoints": "🚓",
        "name": "police car",
        "shortcodes": [
            ":police_car:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "car",
            "patrol",
            "police"
        ]
    },
    {
        "codepoints": "🚔",
        "name": "oncoming police car",
        "shortcodes": [
            ":oncoming_police_car:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "car",
            "oncoming",
            "police"
        ]
    },
    {
        "codepoints": "🚕",
        "name": "taxi",
        "shortcodes": [
            ":taxi:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "taxi",
            "vehicle"
        ]
    },
    {
        "codepoints": "🚖",
        "name": "oncoming taxi",
        "shortcodes": [
            ":oncoming_taxi:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "oncoming",
            "taxi"
        ]
    },
    {
        "codepoints": "🚗",
        "name": "automobile",
        "shortcodes": [
            ":automobile:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "automobile",
            "car"
        ]
    },
    {
        "codepoints": "🚘",
        "name": "oncoming automobile",
        "shortcodes": [
            ":oncoming_automobile:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "automobile",
            "car",
            "oncoming"
        ]
    },
    {
        "codepoints": "🚙",
        "name": "sport utility vehicle",
        "shortcodes": [
            ":sport_utility_vehicle:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "4WD",
            "four-wheel drive",
            "recreational",
            "sport utility",
            "sport utility vehicle",
            "4x4",
            "off-road vehicle",
            "SUV"
        ]
    },
    {
        "codepoints": "🛻",
        "name": "pickup truck",
        "shortcodes": [
            ":pickup_truck:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "pick-up",
            "pickup",
            "truck",
            "ute"
        ]
    },
    {
        "codepoints": "🚚",
        "name": "delivery truck",
        "shortcodes": [
            ":delivery_truck:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "delivery",
            "truck"
        ]
    },
    {
        "codepoints": "🚛",
        "name": "articulated lorry",
        "shortcodes": [
            ":articulated_lorry:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "articulated truck",
            "lorry",
            "semi",
            "truck",
            "articulated lorry"
        ]
    },
    {
        "codepoints": "🚜",
        "name": "tractor",
        "shortcodes": [
            ":tractor:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "tractor",
            "vehicle"
        ]
    },
    {
        "codepoints": "🏎️",
        "name": "racing car",
        "shortcodes": [
            ":racing_car:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "car",
            "racing"
        ]
    },
    {
        "codepoints": "🏍️",
        "name": "motorcycle",
        "shortcodes": [
            ":motorcycle:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "motorcycle",
            "racing"
        ]
    },
    {
        "codepoints": "🛵",
        "name": "motor scooter",
        "shortcodes": [
            ":motor_scooter:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "motor",
            "scooter"
        ]
    },
    {
        "codepoints": "🦽",
        "name": "manual wheelchair",
        "shortcodes": [
            ":manual_wheelchair:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "accessibility",
            "manual wheelchair"
        ]
    },
    {
        "codepoints": "🦼",
        "name": "motorized wheelchair",
        "shortcodes": [
            ":motorized_wheelchair:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "mobility scooter",
            "accessibility",
            "motorized wheelchair",
            "powered wheelchair"
        ]
    },
    {
        "codepoints": "🛺",
        "name": "auto rickshaw",
        "shortcodes": [
            ":auto_rickshaw:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "auto rickshaw",
            "tuk tuk",
            "tuk-tuk",
            "tuktuk"
        ]
    },
    {
        "codepoints": "🚲",
        "name": "bicycle",
        "shortcodes": [
            ":bicycle:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bicycle",
            "bike"
        ]
    },
    {
        "codepoints": "🛴",
        "name": "kick scooter",
        "shortcodes": [
            ":kick_scooter:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "kick",
            "scooter"
        ]
    },
    {
        "codepoints": "🛹",
        "name": "skateboard",
        "shortcodes": [
            ":skateboard:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "board",
            "skateboard"
        ]
    },
    {
        "codepoints": "🛼",
        "name": "roller skate",
        "shortcodes": [
            ":roller_skate:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "roller",
            "rollerskate",
            "skate"
        ]
    },
    {
        "codepoints": "🚏",
        "name": "bus stop",
        "shortcodes": [
            ":bus_stop:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bus",
            "stop",
            "busstop"
        ]
    },
    {
        "codepoints": "🛣️",
        "name": "motorway",
        "shortcodes": [
            ":motorway:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "freeway",
            "highway",
            "road",
            "motorway"
        ]
    },
    {
        "codepoints": "🛤️",
        "name": "railway track",
        "shortcodes": [
            ":railway_track:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "railway",
            "railway track",
            "train"
        ]
    },
    {
        "codepoints": "🛢️",
        "name": "oil drum",
        "shortcodes": [
            ":oil_drum:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "drum",
            "oil"
        ]
    },
    {
        "codepoints": "⛽",
        "name": "fuel pump",
        "shortcodes": [
            ":fuel_pump:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "diesel",
            "fuel",
            "gas",
            "petrol pump",
            "pump",
            "station",
            "fuelpump"
        ]
    },
    {
        "codepoints": "🛞",
        "name": "wheel",
        "shortcodes": [
            ":wheel:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "circle",
            "turn",
            "tyre",
            "wheel",
            "tire"
        ]
    },
    {
        "codepoints": "🚨",
        "name": "police car light",
        "shortcodes": [
            ":police_car_light:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "beacon",
            "car",
            "light",
            "police",
            "revolving"
        ]
    },
    {
        "codepoints": "🚥",
        "name": "horizontal traffic light",
        "shortcodes": [
            ":horizontal_traffic_light:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "horizontal traffic lights",
            "lights",
            "signal",
            "traffic",
            "horizontal traffic light",
            "light"
        ]
    },
    {
        "codepoints": "🚦",
        "name": "vertical traffic light",
        "shortcodes": [
            ":vertical_traffic_light:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "lights",
            "signal",
            "traffic",
            "vertical traffic lights",
            "light",
            "vertical traffic light"
        ]
    },
    {
        "codepoints": "🛑",
        "name": "stop sign",
        "shortcodes": [
            ":stop_sign:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "octagonal",
            "sign",
            "stop"
        ]
    },
    {
        "codepoints": "🚧",
        "name": "construction",
        "shortcodes": [
            ":construction:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "barrier",
            "construction"
        ]
    },
    {
        "codepoints": "⚓",
        "name": "anchor",
        "shortcodes": [
            ":anchor:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "anchor",
            "ship",
            "tool"
        ]
    },
    {
        "codepoints": "🛟",
        "name": "ring buoy",
        "shortcodes": [
            ":ring_buoy:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "buoy",
            "float",
            "life preserver",
            "rescue",
            "ring buoy",
            "safety",
            "life saver"
        ]
    },
    {
        "codepoints": "⛵",
        "name": "sailboat",
        "shortcodes": [
            ":sailboat:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "boat",
            "resort",
            "sailboat",
            "sea",
            "yacht"
        ]
    },
    {
        "codepoints": "🛶",
        "name": "canoe",
        "shortcodes": [
            ":canoe:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "boat",
            "canoe"
        ]
    },
    {
        "codepoints": "🚤",
        "name": "speedboat",
        "shortcodes": [
            ":speedboat:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "boat",
            "speedboat"
        ]
    },
    {
        "codepoints": "🛳️",
        "name": "passenger ship",
        "shortcodes": [
            ":passenger_ship:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "passenger",
            "ship"
        ]
    },
    {
        "codepoints": "⛴️",
        "name": "ferry",
        "shortcodes": [
            ":ferry:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "boat",
            "ferry",
            "passenger"
        ]
    },
    {
        "codepoints": "🛥️",
        "name": "motor boat",
        "shortcodes": [
            ":motor_boat:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "boat",
            "motor boat",
            "motorboat"
        ]
    },
    {
        "codepoints": "🚢",
        "name": "ship",
        "shortcodes": [
            ":ship:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "boat",
            "passenger",
            "ship"
        ]
    },
    {
        "codepoints": "✈️",
        "name": "airplane",
        "shortcodes": [
            ":airplane:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "aeroplane",
            "airplane"
        ]
    },
    {
        "codepoints": "🛩️",
        "name": "small airplane",
        "shortcodes": [
            ":small_airplane:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "aeroplane",
            "airplane",
            "small airplane"
        ]
    },
    {
        "codepoints": "🛫",
        "name": "airplane departure",
        "shortcodes": [
            ":airplane_departure:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "aeroplane",
            "airplane",
            "check-in",
            "departure",
            "departures",
            "take-off"
        ]
    },
    {
        "codepoints": "🛬",
        "name": "airplane arrival",
        "shortcodes": [
            ":airplane_arrival:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "aeroplane",
            "airplane",
            "airplane arrival",
            "arrivals",
            "arriving",
            "landing"
        ]
    },
    {
        "codepoints": "🪂",
        "name": "parachute",
        "shortcodes": [
            ":parachute:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "hang-glide",
            "parachute",
            "parasail",
            "skydive",
            "parascend"
        ]
    },
    {
        "codepoints": "💺",
        "name": "seat",
        "shortcodes": [
            ":seat:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "chair",
            "seat"
        ]
    },
    {
        "codepoints": "🚁",
        "name": "helicopter",
        "shortcodes": [
            ":helicopter:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "helicopter",
            "vehicle"
        ]
    },
    {
        "codepoints": "🚟",
        "name": "suspension railway",
        "shortcodes": [
            ":suspension_railway:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cable",
            "railway",
            "suspension"
        ]
    },
    {
        "codepoints": "🚠",
        "name": "mountain cableway",
        "shortcodes": [
            ":mountain_cableway:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cable",
            "cableway",
            "gondola",
            "mountain",
            "mountain cableway"
        ]
    },
    {
        "codepoints": "🚡",
        "name": "aerial tramway",
        "shortcodes": [
            ":aerial_tramway:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "aerial",
            "cable",
            "car",
            "gondola",
            "tramway"
        ]
    },
    {
        "codepoints": "🛰️",
        "name": "satellite",
        "shortcodes": [
            ":satellite:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "satellite",
            "space"
        ]
    },
    {
        "codepoints": "🚀",
        "name": "rocket",
        "shortcodes": [
            ":rocket:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "rocket",
            "space"
        ]
    },
    {
        "codepoints": "🛸",
        "name": "flying saucer",
        "shortcodes": [
            ":flying_saucer:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "flying saucer",
            "UFO"
        ]
    },
    {
        "codepoints": "🛎️",
        "name": "bellhop bell",
        "shortcodes": [
            ":bellhop_bell:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bell",
            "hotel",
            "porter",
            "bellhop"
        ]
    },
    {
        "codepoints": "🧳",
        "name": "luggage",
        "shortcodes": [
            ":luggage:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "luggage",
            "packing",
            "travel"
        ]
    },
    {
        "codepoints": "⌛",
        "name": "hourglass done",
        "shortcodes": [
            ":hourglass_done:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "hourglass",
            "hourglass done",
            "sand",
            "timer"
        ]
    },
    {
        "codepoints": "⏳",
        "name": "hourglass not done",
        "shortcodes": [
            ":hourglass_not_done:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "hourglass",
            "hourglass not done",
            "sand",
            "timer"
        ]
    },
    {
        "codepoints": "⌚",
        "name": "watch",
        "shortcodes": [
            ":watch:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "clock",
            "watch"
        ]
    },
    {
        "codepoints": "⏰",
        "name": "alarm clock",
        "shortcodes": [
            ":alarm_clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "alarm",
            "clock"
        ]
    },
    {
        "codepoints": "⏱️",
        "name": "stopwatch",
        "shortcodes": [
            ":stopwatch:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "clock",
            "stopwatch"
        ]
    },
    {
        "codepoints": "⏲️",
        "name": "timer clock",
        "shortcodes": [
            ":timer_clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "clock",
            "timer"
        ]
    },
    {
        "codepoints": "🕰️",
        "name": "mantelpiece clock",
        "shortcodes": [
            ":mantelpiece_clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "clock",
            "mantelpiece clock"
        ]
    },
    {
        "codepoints": "🕛",
        "name": "twelve o’clock",
        "shortcodes": [
            ":twelve_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "12",
            "12:00",
            "clock",
            "o’clock",
            "twelve"
        ]
    },
    {
        "codepoints": "🕧",
        "name": "twelve-thirty",
        "shortcodes": [
            ":twelve-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "12",
            "12:30",
            "clock",
            "thirty",
            "twelve",
            "twelve-thirty",
            "half past twelve",
            "12.30"
        ]
    },
    {
        "codepoints": "🕐",
        "name": "one o’clock",
        "shortcodes": [
            ":one_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "1",
            "1:00",
            "clock",
            "o’clock",
            "one"
        ]
    },
    {
        "codepoints": "🕜",
        "name": "one-thirty",
        "shortcodes": [
            ":one-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "1",
            "1:30",
            "clock",
            "one",
            "one-thirty",
            "thirty",
            "half past one",
            "1.30"
        ]
    },
    {
        "codepoints": "🕑",
        "name": "two o’clock",
        "shortcodes": [
            ":two_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "2",
            "2:00",
            "clock",
            "o’clock",
            "two"
        ]
    },
    {
        "codepoints": "🕝",
        "name": "two-thirty",
        "shortcodes": [
            ":two-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "2",
            "2:30",
            "clock",
            "thirty",
            "two",
            "two-thirty",
            "half past two",
            "2.30"
        ]
    },
    {
        "codepoints": "🕒",
        "name": "three o’clock",
        "shortcodes": [
            ":three_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "3",
            "3:00",
            "clock",
            "o’clock",
            "three"
        ]
    },
    {
        "codepoints": "🕞",
        "name": "three-thirty",
        "shortcodes": [
            ":three-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "3",
            "3:30",
            "clock",
            "thirty",
            "three",
            "three-thirty",
            "half past three",
            "3.30"
        ]
    },
    {
        "codepoints": "🕓",
        "name": "four o’clock",
        "shortcodes": [
            ":four_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "4",
            "4:00",
            "clock",
            "four",
            "o’clock"
        ]
    },
    {
        "codepoints": "🕟",
        "name": "four-thirty",
        "shortcodes": [
            ":four-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "4",
            "4:30",
            "clock",
            "four",
            "four-thirty",
            "thirty",
            "half past four",
            "4.30"
        ]
    },
    {
        "codepoints": "🕔",
        "name": "five o’clock",
        "shortcodes": [
            ":five_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "5",
            "5:00",
            "clock",
            "five",
            "o’clock"
        ]
    },
    {
        "codepoints": "🕠",
        "name": "five-thirty",
        "shortcodes": [
            ":five-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "5",
            "5:30",
            "clock",
            "five",
            "five-thirty",
            "thirty",
            "half past five",
            "5.30"
        ]
    },
    {
        "codepoints": "🕕",
        "name": "six o’clock",
        "shortcodes": [
            ":six_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "6",
            "6:00",
            "clock",
            "o’clock",
            "six"
        ]
    },
    {
        "codepoints": "🕡",
        "name": "six-thirty",
        "shortcodes": [
            ":six-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "6",
            "6:30",
            "clock",
            "six",
            "six-thirty",
            "thirty",
            "half past six",
            "6.30"
        ]
    },
    {
        "codepoints": "🕖",
        "name": "seven o’clock",
        "shortcodes": [
            ":seven_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "7",
            "7:00",
            "clock",
            "o’clock",
            "seven"
        ]
    },
    {
        "codepoints": "🕢",
        "name": "seven-thirty",
        "shortcodes": [
            ":seven-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "7",
            "7:30",
            "clock",
            "seven",
            "seven-thirty",
            "thirty",
            "half past seven",
            "7.30"
        ]
    },
    {
        "codepoints": "🕗",
        "name": "eight o’clock",
        "shortcodes": [
            ":eight_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "8",
            "8:00",
            "clock",
            "eight",
            "o’clock"
        ]
    },
    {
        "codepoints": "🕣",
        "name": "eight-thirty",
        "shortcodes": [
            ":eight-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "8",
            "8:30",
            "clock",
            "eight",
            "eight-thirty",
            "thirty",
            "half past eight",
            "8.30"
        ]
    },
    {
        "codepoints": "🕘",
        "name": "nine o’clock",
        "shortcodes": [
            ":nine_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "9",
            "9:00",
            "clock",
            "nine",
            "o’clock"
        ]
    },
    {
        "codepoints": "🕤",
        "name": "nine-thirty",
        "shortcodes": [
            ":nine-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "9",
            "9:30",
            "clock",
            "nine",
            "nine-thirty",
            "thirty",
            "half past nine",
            "9.30"
        ]
    },
    {
        "codepoints": "🕙",
        "name": "ten o’clock",
        "shortcodes": [
            ":ten_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "10",
            "10:00",
            "clock",
            "o’clock",
            "ten"
        ]
    },
    {
        "codepoints": "🕥",
        "name": "ten-thirty",
        "shortcodes": [
            ":ten-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "10",
            "10:30",
            "clock",
            "ten",
            "ten-thirty",
            "thirty",
            "half past ten",
            "10.30"
        ]
    },
    {
        "codepoints": "🕚",
        "name": "eleven o’clock",
        "shortcodes": [
            ":eleven_o’clock:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "00",
            "11",
            "11:00",
            "clock",
            "eleven",
            "o’clock"
        ]
    },
    {
        "codepoints": "🕦",
        "name": "eleven-thirty",
        "shortcodes": [
            ":eleven-thirty:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "11",
            "11:30",
            "clock",
            "eleven",
            "eleven-thirty",
            "thirty",
            "half past eleven",
            "11.30"
        ]
    },
    {
        "codepoints": "🌑",
        "name": "new moon",
        "shortcodes": [
            ":new_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "dark",
            "moon",
            "new moon"
        ]
    },
    {
        "codepoints": "🌒",
        "name": "waxing crescent moon",
        "shortcodes": [
            ":waxing_crescent_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "crescent",
            "moon",
            "waxing"
        ]
    },
    {
        "codepoints": "🌓",
        "name": "first quarter moon",
        "shortcodes": [
            ":first_quarter_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "first quarter moon",
            "moon",
            "quarter"
        ]
    },
    {
        "codepoints": "🌔",
        "name": "waxing gibbous moon",
        "shortcodes": [
            ":waxing_gibbous_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "gibbous",
            "moon",
            "waxing"
        ]
    },
    {
        "codepoints": "🌕",
        "name": "full moon",
        "shortcodes": [
            ":full_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "full",
            "moon"
        ]
    },
    {
        "codepoints": "🌖",
        "name": "waning gibbous moon",
        "shortcodes": [
            ":waning_gibbous_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "gibbous",
            "moon",
            "waning"
        ]
    },
    {
        "codepoints": "🌗",
        "name": "last quarter moon",
        "shortcodes": [
            ":last_quarter_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "last quarter moon",
            "moon",
            "quarter"
        ]
    },
    {
        "codepoints": "🌘",
        "name": "waning crescent moon",
        "shortcodes": [
            ":waning_crescent_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "crescent",
            "moon",
            "waning"
        ]
    },
    {
        "codepoints": "🌙",
        "name": "crescent moon",
        "shortcodes": [
            ":crescent_moon:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "crescent",
            "moon"
        ]
    },
    {
        "codepoints": "🌚",
        "name": "new moon face",
        "shortcodes": [
            ":new_moon_face:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "face",
            "moon",
            "new moon face"
        ]
    },
    {
        "codepoints": "🌛",
        "name": "first quarter moon face",
        "shortcodes": [
            ":first_quarter_moon_face:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "face",
            "first quarter moon face",
            "moon",
            "quarter"
        ]
    },
    {
        "codepoints": "🌜",
        "name": "last quarter moon face",
        "shortcodes": [
            ":last_quarter_moon_face:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "face",
            "last quarter moon face",
            "moon",
            "quarter"
        ]
    },
    {
        "codepoints": "🌡️",
        "name": "thermometer",
        "shortcodes": [
            ":thermometer:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "thermometer",
            "weather"
        ]
    },
    {
        "codepoints": "☀️",
        "name": "sun",
        "shortcodes": [
            ":sun:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bright",
            "rays",
            "sun",
            "sunny"
        ]
    },
    {
        "codepoints": "🌝",
        "name": "full moon face",
        "shortcodes": [
            ":full_moon_face:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bright",
            "face",
            "full",
            "moon",
            "full-moon face"
        ]
    },
    {
        "codepoints": "🌞",
        "name": "sun with face",
        "shortcodes": [
            ":sun_with_face:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "bright",
            "face",
            "sun",
            "sun with face"
        ]
    },
    {
        "codepoints": "🪐",
        "name": "ringed planet",
        "shortcodes": [
            ":ringed_planet:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "ringed planet",
            "saturn",
            "saturnine"
        ]
    },
    {
        "codepoints": "⭐",
        "name": "star",
        "shortcodes": [
            ":star:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "star"
        ]
    },
    {
        "codepoints": "🌟",
        "name": "glowing star",
        "shortcodes": [
            ":glowing_star:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "glittery",
            "glow",
            "glowing star",
            "shining",
            "sparkle",
            "star"
        ]
    },
    {
        "codepoints": "🌠",
        "name": "shooting star",
        "shortcodes": [
            ":shooting_star:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "falling",
            "shooting",
            "star"
        ]
    },
    {
        "codepoints": "🌌",
        "name": "milky way",
        "shortcodes": [
            ":milky_way:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "Milky Way",
            "space",
            "milky way",
            "Milky",
            "Way"
        ]
    },
    {
        "codepoints": "☁️",
        "name": "cloud",
        "shortcodes": [
            ":cloud:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "weather"
        ]
    },
    {
        "codepoints": "⛅",
        "name": "sun behind cloud",
        "shortcodes": [
            ":sun_behind_cloud:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "sun",
            "sun behind cloud"
        ]
    },
    {
        "codepoints": "⛈️",
        "name": "cloud with lightning and rain",
        "shortcodes": [
            ":cloud_with_lightning_and_rain:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "cloud with lightning and rain",
            "rain",
            "thunder"
        ]
    },
    {
        "codepoints": "🌤️",
        "name": "sun behind small cloud",
        "shortcodes": [
            ":sun_behind_small_cloud:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "sun",
            "sun behind small cloud"
        ]
    },
    {
        "codepoints": "🌥️",
        "name": "sun behind large cloud",
        "shortcodes": [
            ":sun_behind_large_cloud:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "sun",
            "sun behind large cloud"
        ]
    },
    {
        "codepoints": "🌦️",
        "name": "sun behind rain cloud",
        "shortcodes": [
            ":sun_behind_rain_cloud:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "rain",
            "sun",
            "sun behind rain cloud"
        ]
    },
    {
        "codepoints": "🌧️",
        "name": "cloud with rain",
        "shortcodes": [
            ":cloud_with_rain:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "cloud with rain",
            "rain"
        ]
    },
    {
        "codepoints": "🌨️",
        "name": "cloud with snow",
        "shortcodes": [
            ":cloud_with_snow:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "cloud with snow",
            "cold",
            "snow"
        ]
    },
    {
        "codepoints": "🌩️",
        "name": "cloud with lightning",
        "shortcodes": [
            ":cloud_with_lightning:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "cloud with lightning",
            "lightning"
        ]
    },
    {
        "codepoints": "🌪️",
        "name": "tornado",
        "shortcodes": [
            ":tornado:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "tornado",
            "whirlwind"
        ]
    },
    {
        "codepoints": "🌫️",
        "name": "fog",
        "shortcodes": [
            ":fog:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cloud",
            "fog"
        ]
    },
    {
        "codepoints": "🌬️",
        "name": "wind face",
        "shortcodes": [
            ":wind_face:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "blow",
            "cloud",
            "face",
            "wind"
        ]
    },
    {
        "codepoints": "🌀",
        "name": "cyclone",
        "shortcodes": [
            ":cyclone:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cyclone",
            "dizzy",
            "hurricane",
            "twister",
            "typhoon"
        ]
    },
    {
        "codepoints": "🌈",
        "name": "rainbow",
        "shortcodes": [
            ":rainbow:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "rain",
            "rainbow"
        ]
    },
    {
        "codepoints": "🌂",
        "name": "closed umbrella",
        "shortcodes": [
            ":closed_umbrella:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "closed umbrella",
            "clothing",
            "rain",
            "umbrella"
        ]
    },
    {
        "codepoints": "☂️",
        "name": "umbrella",
        "shortcodes": [
            ":umbrella:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "clothing",
            "rain",
            "umbrella"
        ]
    },
    {
        "codepoints": "☔",
        "name": "umbrella with rain drops",
        "shortcodes": [
            ":umbrella_with_rain_drops:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "clothing",
            "drop",
            "rain",
            "umbrella",
            "umbrella with rain drops"
        ]
    },
    {
        "codepoints": "⛱️",
        "name": "umbrella on ground",
        "shortcodes": [
            ":umbrella_on_ground:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "beach",
            "sand",
            "sun",
            "umbrella",
            "rain",
            "umbrella on ground"
        ]
    },
    {
        "codepoints": "⚡",
        "name": "high voltage",
        "shortcodes": [
            ":high_voltage:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "danger",
            "electric",
            "high voltage",
            "lightning",
            "voltage",
            "zap"
        ]
    },
    {
        "codepoints": "❄️",
        "name": "snowflake",
        "shortcodes": [
            ":snowflake:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cold",
            "snow",
            "snowflake"
        ]
    },
    {
        "codepoints": "☃️",
        "name": "snowman",
        "shortcodes": [
            ":snowman:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cold",
            "snow",
            "snowman"
        ]
    },
    {
        "codepoints": "⛄",
        "name": "snowman without snow",
        "shortcodes": [
            ":snowman_without_snow:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cold",
            "snow",
            "snowman",
            "snowman without snow"
        ]
    },
    {
        "codepoints": "☄️",
        "name": "comet",
        "shortcodes": [
            ":comet:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "comet",
            "space"
        ]
    },
    {
        "codepoints": "🔥",
        "name": "fire",
        "shortcodes": [
            ":fire:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "fire",
            "flame",
            "tool"
        ]
    },
    {
        "codepoints": "💧",
        "name": "droplet",
        "shortcodes": [
            ":droplet:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "cold",
            "comic",
            "drop",
            "droplet",
            "sweat"
        ]
    },
    {
        "codepoints": "🌊",
        "name": "water wave",
        "shortcodes": [
            ":water_wave:"
        ],
        "emoticons": [],
        "category": "Travel & Places",
        "keywords": [
            "ocean",
            "water",
            "wave"
        ]
    },
    {
        "codepoints": "🎃",
        "name": "jack-o-lantern",
        "shortcodes": [
            ":jack-o-lantern:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "halloween",
            "jack",
            "jack-o-lantern",
            "lantern",
            "Halloween",
            "jack-o’-lantern"
        ]
    },
    {
        "codepoints": "🎄",
        "name": "Christmas tree",
        "shortcodes": [
            ":Christmas_tree:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "Christmas",
            "tree"
        ]
    },
    {
        "codepoints": "🎆",
        "name": "fireworks",
        "shortcodes": [
            ":fireworks:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "fireworks"
        ]
    },
    {
        "codepoints": "🎇",
        "name": "sparkler",
        "shortcodes": [
            ":sparkler:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "fireworks",
            "sparkle",
            "sparkler"
        ]
    },
    {
        "codepoints": "🧨",
        "name": "firecracker",
        "shortcodes": [
            ":firecracker:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "dynamite",
            "explosive",
            "firecracker",
            "fireworks"
        ]
    },
    {
        "codepoints": "✨",
        "name": "sparkles",
        "shortcodes": [
            ":sparkles:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "*",
            "sparkle",
            "sparkles",
            "star"
        ]
    },
    {
        "codepoints": "🎈",
        "name": "balloon",
        "shortcodes": [
            ":balloon:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "balloon",
            "celebration"
        ]
    },
    {
        "codepoints": "🎉",
        "name": "party popper",
        "shortcodes": [
            ":party_popper:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "party",
            "popper",
            "ta-da",
            "tada"
        ]
    },
    {
        "codepoints": "🎊",
        "name": "confetti ball",
        "shortcodes": [
            ":confetti_ball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "celebration",
            "confetti"
        ]
    },
    {
        "codepoints": "🎋",
        "name": "tanabata tree",
        "shortcodes": [
            ":tanabata_tree:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "banner",
            "celebration",
            "Japanese",
            "tanabata tree",
            "tree",
            "Tanabata tree"
        ]
    },
    {
        "codepoints": "🎍",
        "name": "pine decoration",
        "shortcodes": [
            ":pine_decoration:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "bamboo",
            "celebration",
            "decoration",
            "Japanese",
            "pine",
            "pine decoration"
        ]
    },
    {
        "codepoints": "🎎",
        "name": "Japanese dolls",
        "shortcodes": [
            ":Japanese_dolls:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "doll",
            "festival",
            "Japanese",
            "Japanese dolls"
        ]
    },
    {
        "codepoints": "🎏",
        "name": "carp streamer",
        "shortcodes": [
            ":carp_streamer:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "carp",
            "celebration",
            "streamer",
            "carp wind sock",
            "Japanese wind socks",
            "koinobori"
        ]
    },
    {
        "codepoints": "🎐",
        "name": "wind chime",
        "shortcodes": [
            ":wind_chime:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "bell",
            "celebration",
            "chime",
            "wind"
        ]
    },
    {
        "codepoints": "🎑",
        "name": "moon viewing ceremony",
        "shortcodes": [
            ":moon_viewing_ceremony:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "ceremony",
            "moon",
            "moon viewing ceremony",
            "moon-viewing ceremony"
        ]
    },
    {
        "codepoints": "🧧",
        "name": "red envelope",
        "shortcodes": [
            ":red_envelope:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "gift",
            "good luck",
            "hóngbāo",
            "lai see",
            "money",
            "red envelope"
        ]
    },
    {
        "codepoints": "🎀",
        "name": "ribbon",
        "shortcodes": [
            ":ribbon:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "ribbon"
        ]
    },
    {
        "codepoints": "🎁",
        "name": "wrapped gift",
        "shortcodes": [
            ":wrapped_gift:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "box",
            "celebration",
            "gift",
            "present",
            "wrapped"
        ]
    },
    {
        "codepoints": "🎗️",
        "name": "reminder ribbon",
        "shortcodes": [
            ":reminder_ribbon:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "reminder",
            "ribbon"
        ]
    },
    {
        "codepoints": "🎟️",
        "name": "admission tickets",
        "shortcodes": [
            ":admission_tickets:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "admission",
            "admission tickets",
            "entry",
            "ticket"
        ]
    },
    {
        "codepoints": "🎫",
        "name": "ticket",
        "shortcodes": [
            ":ticket:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "admission",
            "ticket"
        ]
    },
    {
        "codepoints": "🎖️",
        "name": "military medal",
        "shortcodes": [
            ":military_medal:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "medal",
            "military"
        ]
    },
    {
        "codepoints": "🏆",
        "name": "trophy",
        "shortcodes": [
            ":trophy:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "prize",
            "trophy"
        ]
    },
    {
        "codepoints": "🏅",
        "name": "sports medal",
        "shortcodes": [
            ":sports_medal:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "medal",
            "sports",
            "sports medal"
        ]
    },
    {
        "codepoints": "🥇",
        "name": "1st place medal",
        "shortcodes": [
            ":1st_place_medal:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "1st place medal",
            "first",
            "gold",
            "medal"
        ]
    },
    {
        "codepoints": "🥈",
        "name": "2nd place medal",
        "shortcodes": [
            ":2nd_place_medal:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "2nd place medal",
            "medal",
            "second",
            "silver"
        ]
    },
    {
        "codepoints": "🥉",
        "name": "3rd place medal",
        "shortcodes": [
            ":3rd_place_medal:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "3rd place medal",
            "bronze",
            "medal",
            "third"
        ]
    },
    {
        "codepoints": "⚽",
        "name": "soccer ball",
        "shortcodes": [
            ":soccer_ball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "football",
            "soccer"
        ]
    },
    {
        "codepoints": "⚾",
        "name": "baseball",
        "shortcodes": [
            ":baseball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "baseball"
        ]
    },
    {
        "codepoints": "🥎",
        "name": "softball",
        "shortcodes": [
            ":softball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "glove",
            "softball",
            "underarm"
        ]
    },
    {
        "codepoints": "🏀",
        "name": "basketball",
        "shortcodes": [
            ":basketball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "basketball",
            "hoop"
        ]
    },
    {
        "codepoints": "🏐",
        "name": "volleyball",
        "shortcodes": [
            ":volleyball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "game",
            "volleyball"
        ]
    },
    {
        "codepoints": "🏈",
        "name": "american football",
        "shortcodes": [
            ":american_football:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "american",
            "ball",
            "football"
        ]
    },
    {
        "codepoints": "🏉",
        "name": "rugby football",
        "shortcodes": [
            ":rugby_football:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "australian football",
            "rugby ball",
            "rugby league",
            "rugby union",
            "ball",
            "football",
            "rugby"
        ]
    },
    {
        "codepoints": "🎾",
        "name": "tennis",
        "shortcodes": [
            ":tennis:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "racquet",
            "tennis"
        ]
    },
    {
        "codepoints": "🥏",
        "name": "flying disc",
        "shortcodes": [
            ":flying_disc:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "flying disc",
            "frisbee",
            "ultimate",
            "Frisbee"
        ]
    },
    {
        "codepoints": "🎳",
        "name": "bowling",
        "shortcodes": [
            ":bowling:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "game",
            "tenpin bowling",
            "bowling"
        ]
    },
    {
        "codepoints": "🏏",
        "name": "cricket game",
        "shortcodes": [
            ":cricket_game:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "bat",
            "cricket game",
            "game",
            "cricket",
            "cricket match"
        ]
    },
    {
        "codepoints": "🏑",
        "name": "field hockey",
        "shortcodes": [
            ":field_hockey:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "field",
            "game",
            "hockey",
            "stick"
        ]
    },
    {
        "codepoints": "🏒",
        "name": "ice hockey",
        "shortcodes": [
            ":ice_hockey:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "game",
            "hockey",
            "ice",
            "puck",
            "stick"
        ]
    },
    {
        "codepoints": "🥍",
        "name": "lacrosse",
        "shortcodes": [
            ":lacrosse:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "goal",
            "lacrosse",
            "stick"
        ]
    },
    {
        "codepoints": "🏓",
        "name": "ping pong",
        "shortcodes": [
            ":ping_pong:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "bat",
            "game",
            "paddle",
            "ping pong",
            "table tennis"
        ]
    },
    {
        "codepoints": "🏸",
        "name": "badminton",
        "shortcodes": [
            ":badminton:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "badminton",
            "birdie",
            "game",
            "racquet",
            "shuttlecock"
        ]
    },
    {
        "codepoints": "🥊",
        "name": "boxing glove",
        "shortcodes": [
            ":boxing_glove:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "boxing",
            "glove"
        ]
    },
    {
        "codepoints": "🥋",
        "name": "martial arts uniform",
        "shortcodes": [
            ":martial_arts_uniform:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "judo",
            "karate",
            "martial arts",
            "martial arts uniform",
            "taekwondo",
            "uniform"
        ]
    },
    {
        "codepoints": "🥅",
        "name": "goal net",
        "shortcodes": [
            ":goal_net:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "goal",
            "goal cage",
            "net"
        ]
    },
    {
        "codepoints": "⛳",
        "name": "flag in hole",
        "shortcodes": [
            ":flag_in_hole:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "flag",
            "flag in hole",
            "golf",
            "hole"
        ]
    },
    {
        "codepoints": "⛸️",
        "name": "ice skate",
        "shortcodes": [
            ":ice_skate:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ice",
            "ice skating",
            "skate"
        ]
    },
    {
        "codepoints": "🎣",
        "name": "fishing pole",
        "shortcodes": [
            ":fishing_pole:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "fish",
            "fishing",
            "pole",
            "rod",
            "fishing pole"
        ]
    },
    {
        "codepoints": "🤿",
        "name": "diving mask",
        "shortcodes": [
            ":diving_mask:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "diving",
            "diving mask",
            "scuba",
            "snorkeling",
            "snorkelling"
        ]
    },
    {
        "codepoints": "🎽",
        "name": "running shirt",
        "shortcodes": [
            ":running_shirt:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "athletics",
            "running",
            "sash",
            "shirt"
        ]
    },
    {
        "codepoints": "🎿",
        "name": "skis",
        "shortcodes": [
            ":skis:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ski",
            "skiing",
            "skis",
            "snow"
        ]
    },
    {
        "codepoints": "🛷",
        "name": "sled",
        "shortcodes": [
            ":sled:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "sled",
            "sledge",
            "sleigh"
        ]
    },
    {
        "codepoints": "🥌",
        "name": "curling stone",
        "shortcodes": [
            ":curling_stone:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "curling",
            "game",
            "rock",
            "stone",
            "curling stone",
            "curling rock"
        ]
    },
    {
        "codepoints": "🎯",
        "name": "bullseye",
        "shortcodes": [
            ":bullseye:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "bullseye",
            "dart",
            "direct hit",
            "game",
            "hit",
            "target"
        ]
    },
    {
        "codepoints": "🪀",
        "name": "yo-yo",
        "shortcodes": [
            ":yo-yo:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "fluctuate",
            "toy",
            "yo-yo"
        ]
    },
    {
        "codepoints": "🪁",
        "name": "kite",
        "shortcodes": [
            ":kite:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "fly",
            "kite",
            "soar"
        ]
    },
    {
        "codepoints": "🎱",
        "name": "pool 8 ball",
        "shortcodes": [
            ":pool_8_ball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "8",
            "ball",
            "billiard",
            "eight",
            "game",
            "pool 8 ball"
        ]
    },
    {
        "codepoints": "🔮",
        "name": "crystal ball",
        "shortcodes": [
            ":crystal_ball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "crystal",
            "fairy tale",
            "fantasy",
            "fortune",
            "tool"
        ]
    },
    {
        "codepoints": "🪄",
        "name": "magic wand",
        "shortcodes": [
            ":magic_wand:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "magic",
            "magic wand",
            "witch",
            "wizard"
        ]
    },
    {
        "codepoints": "🧿",
        "name": "nazar amulet",
        "shortcodes": [
            ":nazar_amulet:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "amulet",
            "charm",
            "evil-eye",
            "nazar",
            "talisman",
            "bead",
            "nazar amulet",
            "evil eye"
        ]
    },
    {
        "codepoints": "🪬",
        "name": "hamsa",
        "shortcodes": [
            ":hamsa:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "amulet",
            "Fatima",
            "hamsa",
            "hand",
            "Mary",
            "Miriam",
            "protection"
        ]
    },
    {
        "codepoints": "🎮",
        "name": "video game",
        "shortcodes": [
            ":video_game:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "controller",
            "game",
            "video game"
        ]
    },
    {
        "codepoints": "🕹️",
        "name": "joystick",
        "shortcodes": [
            ":joystick:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "game",
            "joystick",
            "video game"
        ]
    },
    {
        "codepoints": "🎰",
        "name": "slot machine",
        "shortcodes": [
            ":slot_machine:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "game",
            "pokie",
            "pokies",
            "slot",
            "slot machine"
        ]
    },
    {
        "codepoints": "🎲",
        "name": "game die",
        "shortcodes": [
            ":game_die:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "dice",
            "die",
            "game"
        ]
    },
    {
        "codepoints": "🧩",
        "name": "puzzle piece",
        "shortcodes": [
            ":puzzle_piece:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "clue",
            "interlocking",
            "jigsaw",
            "piece",
            "puzzle"
        ]
    },
    {
        "codepoints": "🧸",
        "name": "teddy bear",
        "shortcodes": [
            ":teddy_bear:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "plaything",
            "plush",
            "stuffed",
            "teddy bear",
            "toy"
        ]
    },
    {
        "codepoints": "🪅",
        "name": "piñata",
        "shortcodes": [
            ":piñata:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "celebration",
            "party",
            "piñata"
        ]
    },
    {
        "codepoints": "🪩",
        "name": "mirror ball",
        "shortcodes": [
            ":mirror_ball:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "dance",
            "disco",
            "glitter",
            "mirror ball",
            "party"
        ]
    },
    {
        "codepoints": "🪆",
        "name": "nesting dolls",
        "shortcodes": [
            ":nesting_dolls:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "doll",
            "nesting",
            "nesting dolls",
            "russia",
            "babushka",
            "matryoshka",
            "Russian dolls"
        ]
    },
    {
        "codepoints": "♠️",
        "name": "spade suit",
        "shortcodes": [
            ":spade_suit:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "card",
            "game",
            "spade suit"
        ]
    },
    {
        "codepoints": "♥️",
        "name": "heart suit",
        "shortcodes": [
            ":heart_suit:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "card",
            "game",
            "heart suit"
        ]
    },
    {
        "codepoints": "♦️",
        "name": "diamond suit",
        "shortcodes": [
            ":diamond_suit:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "card",
            "diamond suit",
            "diamonds",
            "game"
        ]
    },
    {
        "codepoints": "♣️",
        "name": "club suit",
        "shortcodes": [
            ":club_suit:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "card",
            "club suit",
            "clubs",
            "game"
        ]
    },
    {
        "codepoints": "♟️",
        "name": "chess pawn",
        "shortcodes": [
            ":chess_pawn:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "chess",
            "chess pawn",
            "dupe",
            "expendable"
        ]
    },
    {
        "codepoints": "🃏",
        "name": "joker",
        "shortcodes": [
            ":joker:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "card",
            "game",
            "joker",
            "wildcard"
        ]
    },
    {
        "codepoints": "🀄",
        "name": "mahjong red dragon",
        "shortcodes": [
            ":mahjong_red_dragon:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "game",
            "mahjong",
            "mahjong red dragon",
            "red",
            "Mahjong",
            "Mahjong red dragon"
        ]
    },
    {
        "codepoints": "🎴",
        "name": "flower playing cards",
        "shortcodes": [
            ":flower_playing_cards:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "card",
            "flower",
            "flower playing cards",
            "game",
            "Japanese",
            "playing"
        ]
    },
    {
        "codepoints": "🎭",
        "name": "performing arts",
        "shortcodes": [
            ":performing_arts:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "art",
            "mask",
            "performing",
            "performing arts",
            "theater",
            "theatre"
        ]
    },
    {
        "codepoints": "🖼️",
        "name": "framed picture",
        "shortcodes": [
            ":framed_picture:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "art",
            "frame",
            "framed picture",
            "museum",
            "painting",
            "picture"
        ]
    },
    {
        "codepoints": "🎨",
        "name": "artist palette",
        "shortcodes": [
            ":artist_palette:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "art",
            "artist palette",
            "museum",
            "painting",
            "palette"
        ]
    },
    {
        "codepoints": "🧵",
        "name": "thread",
        "shortcodes": [
            ":thread:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "needle",
            "sewing",
            "spool",
            "string",
            "thread"
        ]
    },
    {
        "codepoints": "🪡",
        "name": "sewing needle",
        "shortcodes": [
            ":sewing_needle:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "embroidery",
            "needle",
            "needle and thread",
            "sewing",
            "stitches",
            "sutures",
            "tailoring"
        ]
    },
    {
        "codepoints": "🧶",
        "name": "yarn",
        "shortcodes": [
            ":yarn:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "ball",
            "crochet",
            "knit",
            "yarn"
        ]
    },
    {
        "codepoints": "🪢",
        "name": "knot",
        "shortcodes": [
            ":knot:"
        ],
        "emoticons": [],
        "category": "Activities",
        "keywords": [
            "knot",
            "rope",
            "tangled",
            "tie",
            "twine",
            "twist"
        ]
    },
    {
        "codepoints": "👓",
        "name": "glasses",
        "shortcodes": [
            ":glasses:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "eye",
            "eyeglasses",
            "eyewear",
            "glasses"
        ]
    },
    {
        "codepoints": "🕶️",
        "name": "sunglasses",
        "shortcodes": [
            ":sunglasses:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "dark",
            "eye",
            "eyewear",
            "glasses",
            "sunglasses",
            "sunnies"
        ]
    },
    {
        "codepoints": "🥽",
        "name": "goggles",
        "shortcodes": [
            ":goggles:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "eye protection",
            "goggles",
            "swimming",
            "welding"
        ]
    },
    {
        "codepoints": "🥼",
        "name": "lab coat",
        "shortcodes": [
            ":lab_coat:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "doctor",
            "experiment",
            "lab coat",
            "scientist"
        ]
    },
    {
        "codepoints": "🦺",
        "name": "safety vest",
        "shortcodes": [
            ":safety_vest:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "emergency",
            "safety",
            "vest",
            "hi-vis",
            "high-vis",
            "jacket",
            "life jacket"
        ]
    },
    {
        "codepoints": "👔",
        "name": "necktie",
        "shortcodes": [
            ":necktie:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "necktie",
            "tie"
        ]
    },
    {
        "codepoints": "👕",
        "name": "t-shirt",
        "shortcodes": [
            ":t-shirt:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "shirt",
            "t-shirt",
            "T-shirt",
            "tee",
            "tshirt",
            "tee-shirt"
        ]
    },
    {
        "codepoints": "👖",
        "name": "jeans",
        "shortcodes": [
            ":jeans:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "jeans",
            "pants",
            "trousers"
        ]
    },
    {
        "codepoints": "🧣",
        "name": "scarf",
        "shortcodes": [
            ":scarf:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "neck",
            "scarf"
        ]
    },
    {
        "codepoints": "🧤",
        "name": "gloves",
        "shortcodes": [
            ":gloves:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "gloves",
            "hand"
        ]
    },
    {
        "codepoints": "🧥",
        "name": "coat",
        "shortcodes": [
            ":coat:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "coat",
            "jacket"
        ]
    },
    {
        "codepoints": "🧦",
        "name": "socks",
        "shortcodes": [
            ":socks:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "socks",
            "stocking"
        ]
    },
    {
        "codepoints": "👗",
        "name": "dress",
        "shortcodes": [
            ":dress:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "dress",
            "woman’s clothes"
        ]
    },
    {
        "codepoints": "👘",
        "name": "kimono",
        "shortcodes": [
            ":kimono:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "kimono"
        ]
    },
    {
        "codepoints": "🥻",
        "name": "sari",
        "shortcodes": [
            ":sari:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "dress",
            "sari"
        ]
    },
    {
        "codepoints": "🩱",
        "name": "one-piece swimsuit",
        "shortcodes": [
            ":one-piece_swimsuit:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bathing suit",
            "one-piece swimsuit",
            "swimming costume"
        ]
    },
    {
        "codepoints": "🩲",
        "name": "briefs",
        "shortcodes": [
            ":briefs:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bathers",
            "briefs",
            "speedos",
            "underwear",
            "bathing suit",
            "one-piece",
            "swimsuit",
            "pants"
        ]
    },
    {
        "codepoints": "🩳",
        "name": "shorts",
        "shortcodes": [
            ":shorts:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bathing suit",
            "boardies",
            "boardshorts",
            "shorts",
            "swim shorts",
            "underwear",
            "pants"
        ]
    },
    {
        "codepoints": "👙",
        "name": "bikini",
        "shortcodes": [
            ":bikini:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bikini",
            "clothing",
            "swim suit",
            "two-piece",
            "swim"
        ]
    },
    {
        "codepoints": "👚",
        "name": "woman’s clothes",
        "shortcodes": [
            ":woman’s_clothes:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "blouse",
            "clothing",
            "top",
            "woman",
            "woman’s clothes"
        ]
    },
    {
        "codepoints": "👛",
        "name": "purse",
        "shortcodes": [
            ":purse:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "accessories",
            "coin",
            "purse",
            "clothing"
        ]
    },
    {
        "codepoints": "👜",
        "name": "handbag",
        "shortcodes": [
            ":handbag:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "accessories",
            "bag",
            "handbag",
            "tote",
            "clothing",
            "purse"
        ]
    },
    {
        "codepoints": "👝",
        "name": "clutch bag",
        "shortcodes": [
            ":clutch_bag:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "accessories",
            "bag",
            "clutch bag",
            "pouch",
            "clothing"
        ]
    },
    {
        "codepoints": "🛍️",
        "name": "shopping bags",
        "shortcodes": [
            ":shopping_bags:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bag",
            "hotel",
            "shopping",
            "shopping bags"
        ]
    },
    {
        "codepoints": "🎒",
        "name": "backpack",
        "shortcodes": [
            ":backpack:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "backpack",
            "bag",
            "rucksack",
            "satchel",
            "school"
        ]
    },
    {
        "codepoints": "🩴",
        "name": "thong sandal",
        "shortcodes": [
            ":thong_sandal:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "beach sandals",
            "sandals",
            "thong sandal",
            "thong sandals",
            "thongs",
            "zōri",
            "flip-flop",
            "beach sandal",
            "sandal",
            "thong",
            "flipflop",
            "zori"
        ]
    },
    {
        "codepoints": "👞",
        "name": "man’s shoe",
        "shortcodes": [
            ":man’s_shoe:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "man",
            "man’s shoe",
            "shoe"
        ]
    },
    {
        "codepoints": "👟",
        "name": "running shoe",
        "shortcodes": [
            ":running_shoe:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "athletic",
            "clothing",
            "runners",
            "running shoe",
            "shoe",
            "sneaker",
            "trainer"
        ]
    },
    {
        "codepoints": "🥾",
        "name": "hiking boot",
        "shortcodes": [
            ":hiking_boot:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "backpacking",
            "boot",
            "camping",
            "hiking"
        ]
    },
    {
        "codepoints": "🥿",
        "name": "flat shoe",
        "shortcodes": [
            ":flat_shoe:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ballet flat",
            "flat shoe",
            "slip-on",
            "slipper",
            "pump"
        ]
    },
    {
        "codepoints": "👠",
        "name": "high-heeled shoe",
        "shortcodes": [
            ":high-heeled_shoe:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "heel",
            "high-heeled shoe",
            "shoe",
            "woman"
        ]
    },
    {
        "codepoints": "👡",
        "name": "woman’s sandal",
        "shortcodes": [
            ":woman’s_sandal:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "sandal",
            "shoe",
            "woman",
            "woman’s sandal"
        ]
    },
    {
        "codepoints": "🩰",
        "name": "ballet shoes",
        "shortcodes": [
            ":ballet_shoes:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ballet",
            "ballet shoes",
            "dance"
        ]
    },
    {
        "codepoints": "👢",
        "name": "woman’s boot",
        "shortcodes": [
            ":woman’s_boot:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "boot",
            "clothing",
            "shoe",
            "woman",
            "woman’s boot"
        ]
    },
    {
        "codepoints": "👑",
        "name": "crown",
        "shortcodes": [
            ":crown:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "crown",
            "king",
            "queen"
        ]
    },
    {
        "codepoints": "👒",
        "name": "woman’s hat",
        "shortcodes": [
            ":woman’s_hat:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "hat",
            "woman",
            "woman’s hat"
        ]
    },
    {
        "codepoints": "🎩",
        "name": "top hat",
        "shortcodes": [
            ":top_hat:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clothing",
            "hat",
            "top",
            "tophat"
        ]
    },
    {
        "codepoints": "🎓",
        "name": "graduation cap",
        "shortcodes": [
            ":graduation_cap:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cap",
            "celebration",
            "clothing",
            "graduation",
            "hat"
        ]
    },
    {
        "codepoints": "🧢",
        "name": "billed cap",
        "shortcodes": [
            ":billed_cap:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "baseball cap",
            "billed cap"
        ]
    },
    {
        "codepoints": "🪖",
        "name": "military helmet",
        "shortcodes": [
            ":military_helmet:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "army",
            "helmet",
            "military",
            "soldier",
            "warrior"
        ]
    },
    {
        "codepoints": "⛑️",
        "name": "rescue worker’s helmet",
        "shortcodes": [
            ":rescue_worker’s_helmet:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "aid",
            "cross",
            "face",
            "hat",
            "helmet",
            "rescue worker’s helmet"
        ]
    },
    {
        "codepoints": "📿",
        "name": "prayer beads",
        "shortcodes": [
            ":prayer_beads:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "beads",
            "clothing",
            "necklace",
            "prayer",
            "religion"
        ]
    },
    {
        "codepoints": "💄",
        "name": "lipstick",
        "shortcodes": [
            ":lipstick:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cosmetics",
            "lipstick",
            "make-up",
            "makeup"
        ]
    },
    {
        "codepoints": "💍",
        "name": "ring",
        "shortcodes": [
            ":ring:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "diamond",
            "ring"
        ]
    },
    {
        "codepoints": "💎",
        "name": "gem stone",
        "shortcodes": [
            ":gem_stone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "diamond",
            "gem",
            "gem stone",
            "jewel",
            "gemstone"
        ]
    },
    {
        "codepoints": "🔇",
        "name": "muted speaker",
        "shortcodes": [
            ":muted_speaker:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "mute",
            "muted speaker",
            "quiet",
            "silent",
            "speaker"
        ]
    },
    {
        "codepoints": "🔈",
        "name": "speaker low volume",
        "shortcodes": [
            ":speaker_low_volume:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "low",
            "quiet",
            "soft",
            "speaker",
            "volume",
            "speaker low volume"
        ]
    },
    {
        "codepoints": "🔉",
        "name": "speaker medium volume",
        "shortcodes": [
            ":speaker_medium_volume:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "medium",
            "speaker medium volume"
        ]
    },
    {
        "codepoints": "🔊",
        "name": "speaker high volume",
        "shortcodes": [
            ":speaker_high_volume:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "loud",
            "speaker high volume"
        ]
    },
    {
        "codepoints": "📢",
        "name": "loudspeaker",
        "shortcodes": [
            ":loudspeaker:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "loud",
            "loudspeaker",
            "public address"
        ]
    },
    {
        "codepoints": "📣",
        "name": "megaphone",
        "shortcodes": [
            ":megaphone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cheering",
            "megaphone"
        ]
    },
    {
        "codepoints": "📯",
        "name": "postal horn",
        "shortcodes": [
            ":postal_horn:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "horn",
            "post",
            "postal"
        ]
    },
    {
        "codepoints": "🔔",
        "name": "bell",
        "shortcodes": [
            ":bell:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bell"
        ]
    },
    {
        "codepoints": "🔕",
        "name": "bell with slash",
        "shortcodes": [
            ":bell_with_slash:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bell",
            "bell with slash",
            "forbidden",
            "mute",
            "quiet",
            "silent"
        ]
    },
    {
        "codepoints": "🎼",
        "name": "musical score",
        "shortcodes": [
            ":musical_score:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "music",
            "musical score",
            "score"
        ]
    },
    {
        "codepoints": "🎵",
        "name": "musical note",
        "shortcodes": [
            ":musical_note:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "music",
            "musical note",
            "note"
        ]
    },
    {
        "codepoints": "🎶",
        "name": "musical notes",
        "shortcodes": [
            ":musical_notes:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "music",
            "musical notes",
            "note",
            "notes"
        ]
    },
    {
        "codepoints": "🎙️",
        "name": "studio microphone",
        "shortcodes": [
            ":studio_microphone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "mic",
            "microphone",
            "music",
            "studio"
        ]
    },
    {
        "codepoints": "🎚️",
        "name": "level slider",
        "shortcodes": [
            ":level_slider:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "level",
            "music",
            "slider"
        ]
    },
    {
        "codepoints": "🎛️",
        "name": "control knobs",
        "shortcodes": [
            ":control_knobs:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "control",
            "knobs",
            "music"
        ]
    },
    {
        "codepoints": "🎤",
        "name": "microphone",
        "shortcodes": [
            ":microphone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "karaoke",
            "mic",
            "microphone"
        ]
    },
    {
        "codepoints": "🎧",
        "name": "headphone",
        "shortcodes": [
            ":headphone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "earbud",
            "headphone"
        ]
    },
    {
        "codepoints": "📻",
        "name": "radio",
        "shortcodes": [
            ":radio:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "AM",
            "FM",
            "radio",
            "wireless",
            "video"
        ]
    },
    {
        "codepoints": "🎷",
        "name": "saxophone",
        "shortcodes": [
            ":saxophone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "instrument",
            "music",
            "sax",
            "saxophone"
        ]
    },
    {
        "codepoints": "🪗",
        "name": "accordion",
        "shortcodes": [
            ":accordion:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "accordion",
            "concertina",
            "squeeze box"
        ]
    },
    {
        "codepoints": "🎸",
        "name": "guitar",
        "shortcodes": [
            ":guitar:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "guitar",
            "instrument",
            "music"
        ]
    },
    {
        "codepoints": "🎹",
        "name": "musical keyboard",
        "shortcodes": [
            ":musical_keyboard:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "instrument",
            "keyboard",
            "music",
            "musical keyboard",
            "organ",
            "piano"
        ]
    },
    {
        "codepoints": "🎺",
        "name": "trumpet",
        "shortcodes": [
            ":trumpet:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "instrument",
            "music",
            "trumpet"
        ]
    },
    {
        "codepoints": "🎻",
        "name": "violin",
        "shortcodes": [
            ":violin:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "instrument",
            "music",
            "violin"
        ]
    },
    {
        "codepoints": "🪕",
        "name": "banjo",
        "shortcodes": [
            ":banjo:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "banjo",
            "music",
            "stringed"
        ]
    },
    {
        "codepoints": "🥁",
        "name": "drum",
        "shortcodes": [
            ":drum:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "drum",
            "drumsticks",
            "music",
            "percussions"
        ]
    },
    {
        "codepoints": "🪘",
        "name": "long drum",
        "shortcodes": [
            ":long_drum:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "beat",
            "conga",
            "drum",
            "long drum",
            "rhythm"
        ]
    },
    {
        "codepoints": "📱",
        "name": "mobile phone",
        "shortcodes": [
            ":mobile_phone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cell",
            "mobile",
            "phone",
            "telephone"
        ]
    },
    {
        "codepoints": "📲",
        "name": "mobile phone with arrow",
        "shortcodes": [
            ":mobile_phone_with_arrow:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "arrow",
            "cell",
            "mobile",
            "mobile phone with arrow",
            "phone",
            "receive"
        ]
    },
    {
        "codepoints": "☎️",
        "name": "telephone",
        "shortcodes": [
            ":telephone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "landline",
            "phone",
            "telephone"
        ]
    },
    {
        "codepoints": "📞",
        "name": "telephone receiver",
        "shortcodes": [
            ":telephone_receiver:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "phone",
            "receiver",
            "telephone"
        ]
    },
    {
        "codepoints": "📟",
        "name": "pager",
        "shortcodes": [
            ":pager:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "pager"
        ]
    },
    {
        "codepoints": "📠",
        "name": "fax machine",
        "shortcodes": [
            ":fax_machine:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "fax",
            "fax machine"
        ]
    },
    {
        "codepoints": "🔋",
        "name": "battery",
        "shortcodes": [
            ":battery:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "battery"
        ]
    },
    {
        "codepoints": "🪫",
        "name": "low battery",
        "shortcodes": [
            ":low_battery:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "electronic",
            "low battery",
            "low energy"
        ]
    },
    {
        "codepoints": "🔌",
        "name": "electric plug",
        "shortcodes": [
            ":electric_plug:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "electric",
            "electricity",
            "plug"
        ]
    },
    {
        "codepoints": "💻",
        "name": "laptop",
        "shortcodes": [
            ":laptop:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "computer",
            "laptop",
            "PC",
            "personal",
            "pc"
        ]
    },
    {
        "codepoints": "🖥️",
        "name": "desktop computer",
        "shortcodes": [
            ":desktop_computer:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "computer",
            "desktop"
        ]
    },
    {
        "codepoints": "🖨️",
        "name": "printer",
        "shortcodes": [
            ":printer:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "computer",
            "printer"
        ]
    },
    {
        "codepoints": "⌨️",
        "name": "keyboard",
        "shortcodes": [
            ":keyboard:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "computer",
            "keyboard"
        ]
    },
    {
        "codepoints": "🖱️",
        "name": "computer mouse",
        "shortcodes": [
            ":computer_mouse:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "computer",
            "computer mouse"
        ]
    },
    {
        "codepoints": "🖲️",
        "name": "trackball",
        "shortcodes": [
            ":trackball:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "computer",
            "trackball"
        ]
    },
    {
        "codepoints": "💽",
        "name": "computer disk",
        "shortcodes": [
            ":computer_disk:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "computer",
            "disk",
            "minidisk",
            "optical"
        ]
    },
    {
        "codepoints": "💾",
        "name": "floppy disk",
        "shortcodes": [
            ":floppy_disk:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "computer",
            "disk",
            "diskette",
            "floppy"
        ]
    },
    {
        "codepoints": "💿",
        "name": "optical disk",
        "shortcodes": [
            ":optical_disk:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "CD",
            "computer",
            "disk",
            "optical"
        ]
    },
    {
        "codepoints": "📀",
        "name": "dvd",
        "shortcodes": [
            ":dvd:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "blu-ray",
            "computer",
            "disk",
            "dvd",
            "DVD",
            "optical",
            "Blu-ray"
        ]
    },
    {
        "codepoints": "🧮",
        "name": "abacus",
        "shortcodes": [
            ":abacus:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "abacus",
            "calculation"
        ]
    },
    {
        "codepoints": "🎥",
        "name": "movie camera",
        "shortcodes": [
            ":movie_camera:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "camera",
            "cinema",
            "movie"
        ]
    },
    {
        "codepoints": "🎞️",
        "name": "film frames",
        "shortcodes": [
            ":film_frames:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cinema",
            "film",
            "frames",
            "movie"
        ]
    },
    {
        "codepoints": "📽️",
        "name": "film projector",
        "shortcodes": [
            ":film_projector:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cinema",
            "film",
            "movie",
            "projector",
            "video"
        ]
    },
    {
        "codepoints": "🎬",
        "name": "clapper board",
        "shortcodes": [
            ":clapper_board:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clapper",
            "clapper board",
            "clapperboard",
            "film",
            "movie"
        ]
    },
    {
        "codepoints": "📺",
        "name": "television",
        "shortcodes": [
            ":television:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "television",
            "TV",
            "video",
            "tv"
        ]
    },
    {
        "codepoints": "📷",
        "name": "camera",
        "shortcodes": [
            ":camera:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "camera",
            "video"
        ]
    },
    {
        "codepoints": "📸",
        "name": "camera with flash",
        "shortcodes": [
            ":camera_with_flash:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "camera",
            "camera with flash",
            "flash",
            "video"
        ]
    },
    {
        "codepoints": "📹",
        "name": "video camera",
        "shortcodes": [
            ":video_camera:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "camera",
            "video"
        ]
    },
    {
        "codepoints": "📼",
        "name": "videocassette",
        "shortcodes": [
            ":videocassette:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "tape",
            "VHS",
            "video",
            "videocassette",
            "vhs"
        ]
    },
    {
        "codepoints": "🔍",
        "name": "magnifying glass tilted left",
        "shortcodes": [
            ":magnifying_glass_tilted_left:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "glass",
            "magnifying",
            "magnifying glass tilted left",
            "search",
            "tool"
        ]
    },
    {
        "codepoints": "🔎",
        "name": "magnifying glass tilted right",
        "shortcodes": [
            ":magnifying_glass_tilted_right:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "glass",
            "magnifying",
            "magnifying glass tilted right",
            "search",
            "tool"
        ]
    },
    {
        "codepoints": "🕯️",
        "name": "candle",
        "shortcodes": [
            ":candle:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "candle",
            "light"
        ]
    },
    {
        "codepoints": "💡",
        "name": "light bulb",
        "shortcodes": [
            ":light_bulb:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bulb",
            "comic",
            "electric",
            "globe",
            "idea",
            "light"
        ]
    },
    {
        "codepoints": "🔦",
        "name": "flashlight",
        "shortcodes": [
            ":flashlight:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "electric",
            "flashlight",
            "light",
            "tool",
            "torch"
        ]
    },
    {
        "codepoints": "🏮",
        "name": "red paper lantern",
        "shortcodes": [
            ":red_paper_lantern:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bar",
            "lantern",
            "light",
            "red",
            "red paper lantern"
        ]
    },
    {
        "codepoints": "🪔",
        "name": "diya lamp",
        "shortcodes": [
            ":diya_lamp:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "diya",
            "lamp",
            "oil"
        ]
    },
    {
        "codepoints": "📔",
        "name": "notebook with decorative cover",
        "shortcodes": [
            ":notebook_with_decorative_cover:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "book",
            "cover",
            "decorated",
            "notebook",
            "notebook with decorative cover"
        ]
    },
    {
        "codepoints": "📕",
        "name": "closed book",
        "shortcodes": [
            ":closed_book:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "book",
            "closed"
        ]
    },
    {
        "codepoints": "📖",
        "name": "open book",
        "shortcodes": [
            ":open_book:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "book",
            "open"
        ]
    },
    {
        "codepoints": "📗",
        "name": "green book",
        "shortcodes": [
            ":green_book:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "book",
            "green"
        ]
    },
    {
        "codepoints": "📘",
        "name": "blue book",
        "shortcodes": [
            ":blue_book:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "blue",
            "book"
        ]
    },
    {
        "codepoints": "📙",
        "name": "orange book",
        "shortcodes": [
            ":orange_book:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "book",
            "orange"
        ]
    },
    {
        "codepoints": "📚",
        "name": "books",
        "shortcodes": [
            ":books:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "book",
            "books"
        ]
    },
    {
        "codepoints": "📓",
        "name": "notebook",
        "shortcodes": [
            ":notebook:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "notebook"
        ]
    },
    {
        "codepoints": "📒",
        "name": "ledger",
        "shortcodes": [
            ":ledger:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ledger",
            "notebook"
        ]
    },
    {
        "codepoints": "📃",
        "name": "page with curl",
        "shortcodes": [
            ":page_with_curl:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "curl",
            "document",
            "page",
            "page with curl"
        ]
    },
    {
        "codepoints": "📜",
        "name": "scroll",
        "shortcodes": [
            ":scroll:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "paper",
            "scroll"
        ]
    },
    {
        "codepoints": "📄",
        "name": "page facing up",
        "shortcodes": [
            ":page_facing_up:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "document",
            "page",
            "page facing up"
        ]
    },
    {
        "codepoints": "📰",
        "name": "newspaper",
        "shortcodes": [
            ":newspaper:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "news",
            "newspaper",
            "paper"
        ]
    },
    {
        "codepoints": "🗞️",
        "name": "rolled-up newspaper",
        "shortcodes": [
            ":rolled-up_newspaper:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "news",
            "newspaper",
            "paper",
            "rolled",
            "rolled-up newspaper"
        ]
    },
    {
        "codepoints": "📑",
        "name": "bookmark tabs",
        "shortcodes": [
            ":bookmark_tabs:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bookmark",
            "mark",
            "marker",
            "tabs"
        ]
    },
    {
        "codepoints": "🔖",
        "name": "bookmark",
        "shortcodes": [
            ":bookmark:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bookmark",
            "mark"
        ]
    },
    {
        "codepoints": "🏷️",
        "name": "label",
        "shortcodes": [
            ":label:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "label"
        ]
    },
    {
        "codepoints": "💰",
        "name": "money bag",
        "shortcodes": [
            ":money_bag:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bag",
            "dollar",
            "money",
            "moneybag"
        ]
    },
    {
        "codepoints": "🪙",
        "name": "coin",
        "shortcodes": [
            ":coin:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "coin",
            "gold",
            "metal",
            "money",
            "silver",
            "treasure"
        ]
    },
    {
        "codepoints": "💴",
        "name": "yen banknote",
        "shortcodes": [
            ":yen_banknote:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "banknote",
            "bill",
            "currency",
            "money",
            "note",
            "yen"
        ]
    },
    {
        "codepoints": "💵",
        "name": "dollar banknote",
        "shortcodes": [
            ":dollar_banknote:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "banknote",
            "bill",
            "currency",
            "dollar",
            "money",
            "note"
        ]
    },
    {
        "codepoints": "💶",
        "name": "euro banknote",
        "shortcodes": [
            ":euro_banknote:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "banknote",
            "bill",
            "currency",
            "euro",
            "money",
            "note"
        ]
    },
    {
        "codepoints": "💷",
        "name": "pound banknote",
        "shortcodes": [
            ":pound_banknote:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "banknote",
            "bill",
            "currency",
            "money",
            "note",
            "pound",
            "sterling"
        ]
    },
    {
        "codepoints": "💸",
        "name": "money with wings",
        "shortcodes": [
            ":money_with_wings:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "banknote",
            "bill",
            "fly",
            "money",
            "money with wings",
            "wings"
        ]
    },
    {
        "codepoints": "💳",
        "name": "credit card",
        "shortcodes": [
            ":credit_card:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "card",
            "credit",
            "money"
        ]
    },
    {
        "codepoints": "🧾",
        "name": "receipt",
        "shortcodes": [
            ":receipt:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "accounting",
            "bookkeeping",
            "evidence",
            "proof",
            "receipt"
        ]
    },
    {
        "codepoints": "💹",
        "name": "chart increasing with yen",
        "shortcodes": [
            ":chart_increasing_with_yen:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "chart",
            "chart increasing with yen",
            "graph",
            "graph increasing with yen",
            "growth",
            "money",
            "yen"
        ]
    },
    {
        "codepoints": "✉️",
        "name": "envelope",
        "shortcodes": [
            ":envelope:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "email",
            "envelope",
            "letter",
            "e-mail"
        ]
    },
    {
        "codepoints": "📧",
        "name": "e-mail",
        "shortcodes": [
            ":e-mail:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "e-mail",
            "email",
            "letter",
            "mail"
        ]
    },
    {
        "codepoints": "📨",
        "name": "incoming envelope",
        "shortcodes": [
            ":incoming_envelope:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "e-mail",
            "email",
            "envelope",
            "incoming",
            "letter",
            "receive"
        ]
    },
    {
        "codepoints": "📩",
        "name": "envelope with arrow",
        "shortcodes": [
            ":envelope_with_arrow:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "arrow",
            "e-mail",
            "email",
            "envelope",
            "envelope with arrow",
            "outgoing"
        ]
    },
    {
        "codepoints": "📤",
        "name": "outbox tray",
        "shortcodes": [
            ":outbox_tray:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "box",
            "letter",
            "mail",
            "out tray",
            "outbox",
            "sent",
            "tray"
        ]
    },
    {
        "codepoints": "📥",
        "name": "inbox tray",
        "shortcodes": [
            ":inbox_tray:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "box",
            "in tray",
            "inbox",
            "letter",
            "mail",
            "receive",
            "tray"
        ]
    },
    {
        "codepoints": "📦",
        "name": "package",
        "shortcodes": [
            ":package:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "box",
            "package",
            "parcel"
        ]
    },
    {
        "codepoints": "📫",
        "name": "closed mailbox with raised flag",
        "shortcodes": [
            ":closed_mailbox_with_raised_flag:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "closed",
            "closed letterbox with raised flag",
            "mail",
            "mailbox",
            "postbox",
            "closed mailbox with raised flag",
            "closed postbox with raised flag",
            "letterbox",
            "post",
            "post box"
        ]
    },
    {
        "codepoints": "📪",
        "name": "closed mailbox with lowered flag",
        "shortcodes": [
            ":closed_mailbox_with_lowered_flag:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "closed",
            "closed letterbox with lowered flag",
            "lowered",
            "mail",
            "mailbox",
            "postbox",
            "closed mailbox with lowered flag",
            "closed postbox with lowered flag",
            "letterbox",
            "post box",
            "post"
        ]
    },
    {
        "codepoints": "📬",
        "name": "open mailbox with raised flag",
        "shortcodes": [
            ":open_mailbox_with_raised_flag:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "mail",
            "mailbox",
            "open",
            "open letterbox with raised flag",
            "postbox",
            "open mailbox with raised flag",
            "open postbox with raised flag",
            "post",
            "post box"
        ]
    },
    {
        "codepoints": "📭",
        "name": "open mailbox with lowered flag",
        "shortcodes": [
            ":open_mailbox_with_lowered_flag:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "lowered",
            "mail",
            "mailbox",
            "open",
            "open letterbox with lowered flag",
            "postbox",
            "open mailbox with lowered flag",
            "open postbox with lowered flag",
            "post",
            "post box"
        ]
    },
    {
        "codepoints": "📮",
        "name": "postbox",
        "shortcodes": [
            ":postbox:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "mail",
            "mailbox",
            "postbox",
            "post",
            "post box"
        ]
    },
    {
        "codepoints": "🗳️",
        "name": "ballot box with ballot",
        "shortcodes": [
            ":ballot_box_with_ballot:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ballot",
            "ballot box with ballot",
            "box"
        ]
    },
    {
        "codepoints": "✏️",
        "name": "pencil",
        "shortcodes": [
            ":pencil:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "pencil"
        ]
    },
    {
        "codepoints": "✒️",
        "name": "black nib",
        "shortcodes": [
            ":black_nib:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "black nib",
            "nib",
            "pen"
        ]
    },
    {
        "codepoints": "🖋️",
        "name": "fountain pen",
        "shortcodes": [
            ":fountain_pen:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "fountain",
            "pen"
        ]
    },
    {
        "codepoints": "🖊️",
        "name": "pen",
        "shortcodes": [
            ":pen:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ballpoint",
            "pen"
        ]
    },
    {
        "codepoints": "🖌️",
        "name": "paintbrush",
        "shortcodes": [
            ":paintbrush:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "paintbrush",
            "painting"
        ]
    },
    {
        "codepoints": "🖍️",
        "name": "crayon",
        "shortcodes": [
            ":crayon:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "crayon"
        ]
    },
    {
        "codepoints": "📝",
        "name": "memo",
        "shortcodes": [
            ":memo:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "memo",
            "pencil"
        ]
    },
    {
        "codepoints": "💼",
        "name": "briefcase",
        "shortcodes": [
            ":briefcase:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "briefcase"
        ]
    },
    {
        "codepoints": "📁",
        "name": "file folder",
        "shortcodes": [
            ":file_folder:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "file",
            "folder"
        ]
    },
    {
        "codepoints": "📂",
        "name": "open file folder",
        "shortcodes": [
            ":open_file_folder:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "file",
            "folder",
            "open"
        ]
    },
    {
        "codepoints": "🗂️",
        "name": "card index dividers",
        "shortcodes": [
            ":card_index_dividers:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "card",
            "dividers",
            "index"
        ]
    },
    {
        "codepoints": "📅",
        "name": "calendar",
        "shortcodes": [
            ":calendar:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "calendar",
            "date"
        ]
    },
    {
        "codepoints": "📆",
        "name": "tear-off calendar",
        "shortcodes": [
            ":tear-off_calendar:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "calendar",
            "tear-off calendar"
        ]
    },
    {
        "codepoints": "🗒️",
        "name": "spiral notepad",
        "shortcodes": [
            ":spiral_notepad:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "note",
            "pad",
            "spiral",
            "spiral notepad"
        ]
    },
    {
        "codepoints": "🗓️",
        "name": "spiral calendar",
        "shortcodes": [
            ":spiral_calendar:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "calendar",
            "pad",
            "spiral"
        ]
    },
    {
        "codepoints": "📇",
        "name": "card index",
        "shortcodes": [
            ":card_index:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "card",
            "index",
            "rolodex"
        ]
    },
    {
        "codepoints": "📈",
        "name": "chart increasing",
        "shortcodes": [
            ":chart_increasing:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "chart",
            "chart increasing",
            "graph",
            "graph increasing",
            "growth",
            "trend",
            "upward"
        ]
    },
    {
        "codepoints": "📉",
        "name": "chart decreasing",
        "shortcodes": [
            ":chart_decreasing:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "chart",
            "chart decreasing",
            "down",
            "graph",
            "graph decreasing",
            "trend"
        ]
    },
    {
        "codepoints": "📊",
        "name": "bar chart",
        "shortcodes": [
            ":bar_chart:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bar",
            "chart",
            "graph"
        ]
    },
    {
        "codepoints": "📋",
        "name": "clipboard",
        "shortcodes": [
            ":clipboard:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clipboard"
        ]
    },
    {
        "codepoints": "📌",
        "name": "pushpin",
        "shortcodes": [
            ":pushpin:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "drawing-pin",
            "pin",
            "pushpin"
        ]
    },
    {
        "codepoints": "📍",
        "name": "round pushpin",
        "shortcodes": [
            ":round_pushpin:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "pin",
            "pushpin",
            "round drawing-pin",
            "round pushpin"
        ]
    },
    {
        "codepoints": "📎",
        "name": "paperclip",
        "shortcodes": [
            ":paperclip:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "paperclip"
        ]
    },
    {
        "codepoints": "🖇️",
        "name": "linked paperclips",
        "shortcodes": [
            ":linked_paperclips:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "link",
            "linked paperclips",
            "paperclip"
        ]
    },
    {
        "codepoints": "📏",
        "name": "straight ruler",
        "shortcodes": [
            ":straight_ruler:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ruler",
            "straight edge",
            "straight ruler"
        ]
    },
    {
        "codepoints": "📐",
        "name": "triangular ruler",
        "shortcodes": [
            ":triangular_ruler:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ruler",
            "set",
            "triangle",
            "triangular ruler",
            "set square"
        ]
    },
    {
        "codepoints": "✂️",
        "name": "scissors",
        "shortcodes": [
            ":scissors:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cutting",
            "scissors",
            "tool"
        ]
    },
    {
        "codepoints": "🗃️",
        "name": "card file box",
        "shortcodes": [
            ":card_file_box:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "box",
            "card",
            "file"
        ]
    },
    {
        "codepoints": "🗄️",
        "name": "file cabinet",
        "shortcodes": [
            ":file_cabinet:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cabinet",
            "file",
            "filing"
        ]
    },
    {
        "codepoints": "🗑️",
        "name": "wastebasket",
        "shortcodes": [
            ":wastebasket:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "wastebasket"
        ]
    },
    {
        "codepoints": "🔒",
        "name": "locked",
        "shortcodes": [
            ":locked:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "closed",
            "locked",
            "padlock"
        ]
    },
    {
        "codepoints": "🔓",
        "name": "unlocked",
        "shortcodes": [
            ":unlocked:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "lock",
            "open",
            "unlock",
            "unlocked",
            "padlock"
        ]
    },
    {
        "codepoints": "🔏",
        "name": "locked with pen",
        "shortcodes": [
            ":locked_with_pen:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ink",
            "lock",
            "locked with pen",
            "nib",
            "pen",
            "privacy"
        ]
    },
    {
        "codepoints": "🔐",
        "name": "locked with key",
        "shortcodes": [
            ":locked_with_key:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "closed",
            "key",
            "lock",
            "locked with key",
            "secure"
        ]
    },
    {
        "codepoints": "🔑",
        "name": "key",
        "shortcodes": [
            ":key:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "key",
            "lock",
            "password"
        ]
    },
    {
        "codepoints": "🗝️",
        "name": "old key",
        "shortcodes": [
            ":old_key:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clue",
            "key",
            "lock",
            "old"
        ]
    },
    {
        "codepoints": "🔨",
        "name": "hammer",
        "shortcodes": [
            ":hammer:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "hammer",
            "tool"
        ]
    },
    {
        "codepoints": "🪓",
        "name": "axe",
        "shortcodes": [
            ":axe:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "axe",
            "chop",
            "hatchet",
            "split",
            "wood"
        ]
    },
    {
        "codepoints": "⛏️",
        "name": "pick",
        "shortcodes": [
            ":pick:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "mining",
            "pick",
            "tool"
        ]
    },
    {
        "codepoints": "⚒️",
        "name": "hammer and pick",
        "shortcodes": [
            ":hammer_and_pick:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "hammer",
            "hammer and pick",
            "pick",
            "tool"
        ]
    },
    {
        "codepoints": "🛠️",
        "name": "hammer and wrench",
        "shortcodes": [
            ":hammer_and_wrench:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "hammer",
            "hammer and spanner",
            "hammer and wrench",
            "spanner",
            "tool",
            "wrench"
        ]
    },
    {
        "codepoints": "🗡️",
        "name": "dagger",
        "shortcodes": [
            ":dagger:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "dagger",
            "knife",
            "weapon"
        ]
    },
    {
        "codepoints": "⚔️",
        "name": "crossed swords",
        "shortcodes": [
            ":crossed_swords:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "crossed",
            "swords",
            "weapon"
        ]
    },
    {
        "codepoints": "🔫",
        "name": "water pistol",
        "shortcodes": [
            ":water_pistol:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "toy",
            "water pistol",
            "gun",
            "handgun",
            "pistol",
            "revolver",
            "tool",
            "water",
            "weapon"
        ]
    },
    {
        "codepoints": "🪃",
        "name": "boomerang",
        "shortcodes": [
            ":boomerang:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "australia",
            "boomerang",
            "rebound",
            "repercussion"
        ]
    },
    {
        "codepoints": "🏹",
        "name": "bow and arrow",
        "shortcodes": [
            ":bow_and_arrow:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "archer",
            "arrow",
            "bow",
            "bow and arrow",
            "Sagittarius",
            "zodiac"
        ]
    },
    {
        "codepoints": "🛡️",
        "name": "shield",
        "shortcodes": [
            ":shield:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "shield",
            "weapon"
        ]
    },
    {
        "codepoints": "🪚",
        "name": "carpentry saw",
        "shortcodes": [
            ":carpentry_saw:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "carpenter",
            "carpentry saw",
            "lumber",
            "saw",
            "tool"
        ]
    },
    {
        "codepoints": "🔧",
        "name": "wrench",
        "shortcodes": [
            ":wrench:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "spanner",
            "tool",
            "wrench"
        ]
    },
    {
        "codepoints": "🪛",
        "name": "screwdriver",
        "shortcodes": [
            ":screwdriver:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "screw",
            "screwdriver",
            "tool"
        ]
    },
    {
        "codepoints": "🔩",
        "name": "nut and bolt",
        "shortcodes": [
            ":nut_and_bolt:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bolt",
            "nut",
            "nut and bolt",
            "tool"
        ]
    },
    {
        "codepoints": "⚙️",
        "name": "gear",
        "shortcodes": [
            ":gear:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cog",
            "cogwheel",
            "gear",
            "tool"
        ]
    },
    {
        "codepoints": "🗜️",
        "name": "clamp",
        "shortcodes": [
            ":clamp:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "clamp",
            "compress",
            "tool",
            "vice"
        ]
    },
    {
        "codepoints": "⚖️",
        "name": "balance scale",
        "shortcodes": [
            ":balance_scale:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "balance",
            "justice",
            "Libra",
            "scale",
            "zodiac"
        ]
    },
    {
        "codepoints": "🦯",
        "name": "white cane",
        "shortcodes": [
            ":white_cane:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "accessibility",
            "long mobility cane",
            "white cane",
            "blind",
            "guide cane"
        ]
    },
    {
        "codepoints": "🔗",
        "name": "link",
        "shortcodes": [
            ":link:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "link"
        ]
    },
    {
        "codepoints": "⛓️",
        "name": "chains",
        "shortcodes": [
            ":chains:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "chain",
            "chains"
        ]
    },
    {
        "codepoints": "🪝",
        "name": "hook",
        "shortcodes": [
            ":hook:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "catch",
            "crook",
            "curve",
            "ensnare",
            "fishing",
            "hook",
            "selling point"
        ]
    },
    {
        "codepoints": "🧰",
        "name": "toolbox",
        "shortcodes": [
            ":toolbox:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "chest",
            "mechanic",
            "tool",
            "toolbox"
        ]
    },
    {
        "codepoints": "🧲",
        "name": "magnet",
        "shortcodes": [
            ":magnet:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "attraction",
            "horseshoe",
            "magnet",
            "magnetic"
        ]
    },
    {
        "codepoints": "🪜",
        "name": "ladder",
        "shortcodes": [
            ":ladder:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "climb",
            "ladder",
            "rung",
            "step"
        ]
    },
    {
        "codepoints": "⚗️",
        "name": "alembic",
        "shortcodes": [
            ":alembic:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "alembic",
            "chemistry",
            "tool"
        ]
    },
    {
        "codepoints": "🧪",
        "name": "test tube",
        "shortcodes": [
            ":test_tube:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "chemist",
            "chemistry",
            "experiment",
            "lab",
            "science",
            "test tube"
        ]
    },
    {
        "codepoints": "🧫",
        "name": "petri dish",
        "shortcodes": [
            ":petri_dish:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bacteria",
            "biologist",
            "biology",
            "culture",
            "lab",
            "petri dish"
        ]
    },
    {
        "codepoints": "🧬",
        "name": "dna",
        "shortcodes": [
            ":dna:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "biologist",
            "dna",
            "DNA",
            "evolution",
            "gene",
            "genetics",
            "life"
        ]
    },
    {
        "codepoints": "🔬",
        "name": "microscope",
        "shortcodes": [
            ":microscope:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "microscope",
            "science",
            "tool"
        ]
    },
    {
        "codepoints": "🔭",
        "name": "telescope",
        "shortcodes": [
            ":telescope:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "science",
            "telescope",
            "tool"
        ]
    },
    {
        "codepoints": "📡",
        "name": "satellite antenna",
        "shortcodes": [
            ":satellite_antenna:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "antenna",
            "dish",
            "satellite"
        ]
    },
    {
        "codepoints": "💉",
        "name": "syringe",
        "shortcodes": [
            ":syringe:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "medicine",
            "needle",
            "shot",
            "sick",
            "syringe",
            "ill",
            "injection"
        ]
    },
    {
        "codepoints": "🩸",
        "name": "drop of blood",
        "shortcodes": [
            ":drop_of_blood:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bleed",
            "blood donation",
            "drop of blood",
            "injury",
            "medicine",
            "menstruation"
        ]
    },
    {
        "codepoints": "💊",
        "name": "pill",
        "shortcodes": [
            ":pill:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "doctor",
            "medicine",
            "pill",
            "sick"
        ]
    },
    {
        "codepoints": "🩹",
        "name": "adhesive bandage",
        "shortcodes": [
            ":adhesive_bandage:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "adhesive bandage",
            "bandage",
            "bandaid",
            "dressing",
            "injury",
            "plaster",
            "sticking plaster"
        ]
    },
    {
        "codepoints": "🩼",
        "name": "crutch",
        "shortcodes": [
            ":crutch:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cane",
            "crutch",
            "disability",
            "hurt",
            "mobility aid",
            "stick"
        ]
    },
    {
        "codepoints": "🩺",
        "name": "stethoscope",
        "shortcodes": [
            ":stethoscope:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "doctor",
            "heart",
            "medicine",
            "stethoscope"
        ]
    },
    {
        "codepoints": "🩻",
        "name": "x-ray",
        "shortcodes": [
            ":x-ray:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bones",
            "doctor",
            "medical",
            "skeleton",
            "x-ray"
        ]
    },
    {
        "codepoints": "🚪",
        "name": "door",
        "shortcodes": [
            ":door:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "door"
        ]
    },
    {
        "codepoints": "🛗",
        "name": "elevator",
        "shortcodes": [
            ":elevator:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "accessibility",
            "elevator",
            "hoist",
            "lift"
        ]
    },
    {
        "codepoints": "🪞",
        "name": "mirror",
        "shortcodes": [
            ":mirror:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "looking glass",
            "mirror",
            "reflection",
            "reflector",
            "speculum"
        ]
    },
    {
        "codepoints": "🪟",
        "name": "window",
        "shortcodes": [
            ":window:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "frame",
            "fresh air",
            "opening",
            "transparent",
            "view",
            "window"
        ]
    },
    {
        "codepoints": "🛏️",
        "name": "bed",
        "shortcodes": [
            ":bed:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bed",
            "hotel",
            "sleep"
        ]
    },
    {
        "codepoints": "🛋️",
        "name": "couch and lamp",
        "shortcodes": [
            ":couch_and_lamp:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "couch",
            "couch and lamp",
            "hotel",
            "lamp",
            "sofa",
            "sofa and lamp"
        ]
    },
    {
        "codepoints": "🪑",
        "name": "chair",
        "shortcodes": [
            ":chair:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "chair",
            "seat",
            "sit"
        ]
    },
    {
        "codepoints": "🚽",
        "name": "toilet",
        "shortcodes": [
            ":toilet:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "facilities",
            "loo",
            "toilet",
            "WC",
            "lavatory"
        ]
    },
    {
        "codepoints": "🪠",
        "name": "plunger",
        "shortcodes": [
            ":plunger:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "force cup",
            "plumber",
            "plunger",
            "suction",
            "toilet"
        ]
    },
    {
        "codepoints": "🚿",
        "name": "shower",
        "shortcodes": [
            ":shower:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "shower",
            "water"
        ]
    },
    {
        "codepoints": "🛁",
        "name": "bathtub",
        "shortcodes": [
            ":bathtub:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bath",
            "bathtub"
        ]
    },
    {
        "codepoints": "🪤",
        "name": "mouse trap",
        "shortcodes": [
            ":mouse_trap:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bait",
            "mouse trap",
            "mousetrap",
            "snare",
            "trap",
            "mouse"
        ]
    },
    {
        "codepoints": "🪒",
        "name": "razor",
        "shortcodes": [
            ":razor:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "razor",
            "sharp",
            "shave",
            "cut-throat"
        ]
    },
    {
        "codepoints": "🧴",
        "name": "lotion bottle",
        "shortcodes": [
            ":lotion_bottle:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "lotion",
            "lotion bottle",
            "moisturizer",
            "shampoo",
            "sunscreen",
            "moisturiser"
        ]
    },
    {
        "codepoints": "🧷",
        "name": "safety pin",
        "shortcodes": [
            ":safety_pin:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "nappy",
            "punk rock",
            "safety pin",
            "diaper"
        ]
    },
    {
        "codepoints": "🧹",
        "name": "broom",
        "shortcodes": [
            ":broom:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "broom",
            "cleaning",
            "sweeping",
            "witch"
        ]
    },
    {
        "codepoints": "🧺",
        "name": "basket",
        "shortcodes": [
            ":basket:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "basket",
            "farming",
            "laundry",
            "picnic"
        ]
    },
    {
        "codepoints": "🧻",
        "name": "roll of paper",
        "shortcodes": [
            ":roll_of_paper:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "paper towels",
            "roll of paper",
            "toilet paper",
            "toilet roll"
        ]
    },
    {
        "codepoints": "🪣",
        "name": "bucket",
        "shortcodes": [
            ":bucket:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bucket",
            "cask",
            "pail",
            "vat"
        ]
    },
    {
        "codepoints": "🧼",
        "name": "soap",
        "shortcodes": [
            ":soap:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bar",
            "bathing",
            "cleaning",
            "lather",
            "soap",
            "soapdish"
        ]
    },
    {
        "codepoints": "🫧",
        "name": "bubbles",
        "shortcodes": [
            ":bubbles:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bubbles",
            "burp",
            "clean",
            "soap",
            "underwater"
        ]
    },
    {
        "codepoints": "🪥",
        "name": "toothbrush",
        "shortcodes": [
            ":toothbrush:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "bathroom",
            "brush",
            "clean",
            "dental",
            "hygiene",
            "teeth",
            "toothbrush"
        ]
    },
    {
        "codepoints": "🧽",
        "name": "sponge",
        "shortcodes": [
            ":sponge:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "absorbing",
            "cleaning",
            "porous",
            "sponge"
        ]
    },
    {
        "codepoints": "🧯",
        "name": "fire extinguisher",
        "shortcodes": [
            ":fire_extinguisher:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "extinguish",
            "fire",
            "fire extinguisher",
            "quench"
        ]
    },
    {
        "codepoints": "🛒",
        "name": "shopping cart",
        "shortcodes": [
            ":shopping_cart:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cart",
            "shopping",
            "trolley",
            "basket"
        ]
    },
    {
        "codepoints": "🚬",
        "name": "cigarette",
        "shortcodes": [
            ":cigarette:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cigarette",
            "smoking"
        ]
    },
    {
        "codepoints": "⚰️",
        "name": "coffin",
        "shortcodes": [
            ":coffin:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "coffin",
            "death"
        ]
    },
    {
        "codepoints": "🪦",
        "name": "headstone",
        "shortcodes": [
            ":headstone:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "cemetery",
            "grave",
            "graveyard",
            "headstone",
            "tombstone"
        ]
    },
    {
        "codepoints": "⚱️",
        "name": "funeral urn",
        "shortcodes": [
            ":funeral_urn:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "ashes",
            "death",
            "funeral",
            "urn"
        ]
    },
    {
        "codepoints": "🗿",
        "name": "moai",
        "shortcodes": [
            ":moai:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "face",
            "moai",
            "moyai",
            "statue"
        ]
    },
    {
        "codepoints": "🪧",
        "name": "placard",
        "shortcodes": [
            ":placard:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "demonstration",
            "picket",
            "placard",
            "protest",
            "sign"
        ]
    },
    {
        "codepoints": "🪪",
        "name": "identification card",
        "shortcodes": [
            ":identification_card:"
        ],
        "emoticons": [],
        "category": "Objects",
        "keywords": [
            "credentials",
            "ID",
            "identification card",
            "license",
            "security",
            "driving",
            "licence"
        ]
    },
    {
        "codepoints": "🏧",
        "name": "ATM sign",
        "shortcodes": [
            ":ATM_sign:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "ATM",
            "ATM sign",
            "automated",
            "bank",
            "teller"
        ]
    },
    {
        "codepoints": "🚮",
        "name": "litter in bin sign",
        "shortcodes": [
            ":litter_in_bin_sign:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "litter",
            "litter bin",
            "litter in bin sign",
            "garbage",
            "trash"
        ]
    },
    {
        "codepoints": "🚰",
        "name": "potable water",
        "shortcodes": [
            ":potable_water:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "drinking",
            "potable",
            "water"
        ]
    },
    {
        "codepoints": "♿",
        "name": "wheelchair symbol",
        "shortcodes": [
            ":wheelchair_symbol:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "access",
            "disabled access",
            "wheelchair symbol"
        ]
    },
    {
        "codepoints": "🚹",
        "name": "men’s room",
        "shortcodes": [
            ":men’s_room:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "bathroom",
            "lavatory",
            "man",
            "men’s room",
            "restroom",
            "toilet",
            "WC",
            "men’s",
            "washroom",
            "wc"
        ]
    },
    {
        "codepoints": "🚺",
        "name": "women’s room",
        "shortcodes": [
            ":women’s_room:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "ladies room",
            "lavatory",
            "restroom",
            "wc",
            "woman",
            "women’s room",
            "women’s toilet",
            "bathroom",
            "toilet",
            "WC",
            "ladies’ room",
            "washroom",
            "women’s"
        ]
    },
    {
        "codepoints": "🚻",
        "name": "restroom",
        "shortcodes": [
            ":restroom:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "bathroom",
            "lavatory",
            "restroom",
            "toilet",
            "WC",
            "washroom"
        ]
    },
    {
        "codepoints": "🚼",
        "name": "baby symbol",
        "shortcodes": [
            ":baby_symbol:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "baby",
            "baby symbol",
            "change room",
            "changing"
        ]
    },
    {
        "codepoints": "🚾",
        "name": "water closet",
        "shortcodes": [
            ":water_closet:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "amenities",
            "bathroom",
            "restroom",
            "toilet",
            "water closet",
            "wc",
            "WC",
            "closet",
            "lavatory",
            "water"
        ]
    },
    {
        "codepoints": "🛂",
        "name": "passport control",
        "shortcodes": [
            ":passport_control:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "border",
            "control",
            "passport",
            "security"
        ]
    },
    {
        "codepoints": "🛃",
        "name": "customs",
        "shortcodes": [
            ":customs:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "customs"
        ]
    },
    {
        "codepoints": "🛄",
        "name": "baggage claim",
        "shortcodes": [
            ":baggage_claim:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "baggage",
            "claim"
        ]
    },
    {
        "codepoints": "🛅",
        "name": "left luggage",
        "shortcodes": [
            ":left_luggage:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "baggage",
            "left luggage",
            "locker",
            "luggage"
        ]
    },
    {
        "codepoints": "⚠️",
        "name": "warning",
        "shortcodes": [
            ":warning:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "warning"
        ]
    },
    {
        "codepoints": "🚸",
        "name": "children crossing",
        "shortcodes": [
            ":children_crossing:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "child",
            "children crossing",
            "crossing",
            "pedestrian",
            "traffic"
        ]
    },
    {
        "codepoints": "⛔",
        "name": "no entry",
        "shortcodes": [
            ":no_entry:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "denied",
            "entry",
            "forbidden",
            "no",
            "prohibited",
            "traffic",
            "not"
        ]
    },
    {
        "codepoints": "🚫",
        "name": "prohibited",
        "shortcodes": [
            ":prohibited:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "denied",
            "entry",
            "forbidden",
            "no",
            "prohibited",
            "not"
        ]
    },
    {
        "codepoints": "🚳",
        "name": "no bicycles",
        "shortcodes": [
            ":no_bicycles:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "bicycle",
            "bike",
            "forbidden",
            "no",
            "no bicycles",
            "prohibited"
        ]
    },
    {
        "codepoints": "🚭",
        "name": "no smoking",
        "shortcodes": [
            ":no_smoking:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "denied",
            "forbidden",
            "no",
            "prohibited",
            "smoking",
            "not"
        ]
    },
    {
        "codepoints": "🚯",
        "name": "no littering",
        "shortcodes": [
            ":no_littering:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "denied",
            "forbidden",
            "litter",
            "no",
            "no littering",
            "prohibited",
            "not"
        ]
    },
    {
        "codepoints": "🚱",
        "name": "non-potable water",
        "shortcodes": [
            ":non-potable_water:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "non-drinkable water",
            "non-drinking",
            "non-potable",
            "water"
        ]
    },
    {
        "codepoints": "🚷",
        "name": "no pedestrians",
        "shortcodes": [
            ":no_pedestrians:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "denied",
            "forbidden",
            "no",
            "no pedestrians",
            "pedestrian",
            "prohibited",
            "not"
        ]
    },
    {
        "codepoints": "📵",
        "name": "no mobile phones",
        "shortcodes": [
            ":no_mobile_phones:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "cell",
            "forbidden",
            "mobile",
            "no",
            "no mobile phones",
            "phone"
        ]
    },
    {
        "codepoints": "🔞",
        "name": "no one under eighteen",
        "shortcodes": [
            ":no_one_under_eighteen:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "18",
            "age restriction",
            "eighteen",
            "no one under eighteen",
            "prohibited",
            "underage"
        ]
    },
    {
        "codepoints": "☢️",
        "name": "radioactive",
        "shortcodes": [
            ":radioactive:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "radioactive",
            "sign"
        ]
    },
    {
        "codepoints": "☣️",
        "name": "biohazard",
        "shortcodes": [
            ":biohazard:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "biohazard",
            "sign"
        ]
    },
    {
        "codepoints": "⬆️",
        "name": "up arrow",
        "shortcodes": [
            ":up_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "cardinal",
            "direction",
            "north",
            "up",
            "up arrow"
        ]
    },
    {
        "codepoints": "↗️",
        "name": "up-right arrow",
        "shortcodes": [
            ":up-right_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "direction",
            "intercardinal",
            "northeast",
            "up-right arrow"
        ]
    },
    {
        "codepoints": "➡️",
        "name": "right arrow",
        "shortcodes": [
            ":right_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "cardinal",
            "direction",
            "east",
            "right arrow"
        ]
    },
    {
        "codepoints": "↘️",
        "name": "down-right arrow",
        "shortcodes": [
            ":down-right_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "direction",
            "down-right arrow",
            "intercardinal",
            "southeast"
        ]
    },
    {
        "codepoints": "⬇️",
        "name": "down arrow",
        "shortcodes": [
            ":down_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "cardinal",
            "direction",
            "down",
            "south"
        ]
    },
    {
        "codepoints": "↙️",
        "name": "down-left arrow",
        "shortcodes": [
            ":down-left_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "direction",
            "down-left arrow",
            "intercardinal",
            "southwest"
        ]
    },
    {
        "codepoints": "⬅️",
        "name": "left arrow",
        "shortcodes": [
            ":left_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "cardinal",
            "direction",
            "left arrow",
            "west"
        ]
    },
    {
        "codepoints": "↖️",
        "name": "up-left arrow",
        "shortcodes": [
            ":up-left_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "direction",
            "intercardinal",
            "northwest",
            "up-left arrow"
        ]
    },
    {
        "codepoints": "↕️",
        "name": "up-down arrow",
        "shortcodes": [
            ":up-down_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "up-down arrow"
        ]
    },
    {
        "codepoints": "↔️",
        "name": "left-right arrow",
        "shortcodes": [
            ":left-right_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "left-right arrow"
        ]
    },
    {
        "codepoints": "↩️",
        "name": "right arrow curving left",
        "shortcodes": [
            ":right_arrow_curving_left:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "right arrow curving left"
        ]
    },
    {
        "codepoints": "↪️",
        "name": "left arrow curving right",
        "shortcodes": [
            ":left_arrow_curving_right:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "left arrow curving right"
        ]
    },
    {
        "codepoints": "⤴️",
        "name": "right arrow curving up",
        "shortcodes": [
            ":right_arrow_curving_up:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "right arrow curving up"
        ]
    },
    {
        "codepoints": "⤵️",
        "name": "right arrow curving down",
        "shortcodes": [
            ":right_arrow_curving_down:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "down",
            "right arrow curving down"
        ]
    },
    {
        "codepoints": "🔃",
        "name": "clockwise vertical arrows",
        "shortcodes": [
            ":clockwise_vertical_arrows:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "clockwise",
            "clockwise vertical arrows",
            "reload"
        ]
    },
    {
        "codepoints": "🔄",
        "name": "counterclockwise arrows button",
        "shortcodes": [
            ":counterclockwise_arrows_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "anticlockwise",
            "arrow",
            "counterclockwise",
            "counterclockwise arrows button",
            "withershins",
            "anticlockwise arrows button"
        ]
    },
    {
        "codepoints": "🔙",
        "name": "BACK arrow",
        "shortcodes": [
            ":BACK_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "BACK"
        ]
    },
    {
        "codepoints": "🔚",
        "name": "END arrow",
        "shortcodes": [
            ":END_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "END"
        ]
    },
    {
        "codepoints": "🔛",
        "name": "ON! arrow",
        "shortcodes": [
            ":ON!_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "mark",
            "ON",
            "ON!"
        ]
    },
    {
        "codepoints": "🔜",
        "name": "SOON arrow",
        "shortcodes": [
            ":SOON_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "SOON"
        ]
    },
    {
        "codepoints": "🔝",
        "name": "TOP arrow",
        "shortcodes": [
            ":TOP_arrow:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "TOP",
            "up"
        ]
    },
    {
        "codepoints": "🛐",
        "name": "place of worship",
        "shortcodes": [
            ":place_of_worship:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "place of worship",
            "religion",
            "worship"
        ]
    },
    {
        "codepoints": "⚛️",
        "name": "atom symbol",
        "shortcodes": [
            ":atom_symbol:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "atheist",
            "atom",
            "atom symbol"
        ]
    },
    {
        "codepoints": "🕉️",
        "name": "om",
        "shortcodes": [
            ":om:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Hindu",
            "om",
            "religion"
        ]
    },
    {
        "codepoints": "✡️",
        "name": "star of David",
        "shortcodes": [
            ":star_of_David:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "David",
            "Jew",
            "Jewish",
            "religion",
            "star",
            "star of David",
            "Judaism",
            "Star of David"
        ]
    },
    {
        "codepoints": "☸️",
        "name": "wheel of dharma",
        "shortcodes": [
            ":wheel_of_dharma:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Buddhist",
            "dharma",
            "religion",
            "wheel",
            "wheel of dharma"
        ]
    },
    {
        "codepoints": "☯️",
        "name": "yin yang",
        "shortcodes": [
            ":yin_yang:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "religion",
            "tao",
            "taoist",
            "yang",
            "yin",
            "Tao",
            "Taoist"
        ]
    },
    {
        "codepoints": "✝️",
        "name": "latin cross",
        "shortcodes": [
            ":latin_cross:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Christian",
            "cross",
            "religion",
            "latin cross",
            "Latin cross"
        ]
    },
    {
        "codepoints": "☦️",
        "name": "orthodox cross",
        "shortcodes": [
            ":orthodox_cross:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Christian",
            "cross",
            "orthodox cross",
            "religion",
            "Orthodox cross"
        ]
    },
    {
        "codepoints": "☪️",
        "name": "star and crescent",
        "shortcodes": [
            ":star_and_crescent:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "islam",
            "Muslim",
            "religion",
            "star and crescent",
            "Islam"
        ]
    },
    {
        "codepoints": "☮️",
        "name": "peace symbol",
        "shortcodes": [
            ":peace_symbol:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "peace",
            "peace symbol"
        ]
    },
    {
        "codepoints": "🕎",
        "name": "menorah",
        "shortcodes": [
            ":menorah:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "candelabrum",
            "candlestick",
            "menorah",
            "religion"
        ]
    },
    {
        "codepoints": "🔯",
        "name": "dotted six-pointed star",
        "shortcodes": [
            ":dotted_six-pointed_star:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "dotted six-pointed star",
            "fortune",
            "star"
        ]
    },
    {
        "codepoints": "♈",
        "name": "Aries",
        "shortcodes": [
            ":Aries:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Aries",
            "ram",
            "zodiac"
        ]
    },
    {
        "codepoints": "♉",
        "name": "Taurus",
        "shortcodes": [
            ":Taurus:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "bull",
            "ox",
            "Taurus",
            "zodiac"
        ]
    },
    {
        "codepoints": "♊",
        "name": "Gemini",
        "shortcodes": [
            ":Gemini:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Gemini",
            "twins",
            "zodiac"
        ]
    },
    {
        "codepoints": "♋",
        "name": "Cancer",
        "shortcodes": [
            ":Cancer:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Cancer",
            "crab",
            "zodiac"
        ]
    },
    {
        "codepoints": "♌",
        "name": "Leo",
        "shortcodes": [
            ":Leo:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Leo",
            "lion",
            "zodiac"
        ]
    },
    {
        "codepoints": "♍",
        "name": "Virgo",
        "shortcodes": [
            ":Virgo:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "virgin",
            "Virgo",
            "zodiac"
        ]
    },
    {
        "codepoints": "♎",
        "name": "Libra",
        "shortcodes": [
            ":Libra:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "balance",
            "justice",
            "Libra",
            "scales",
            "zodiac"
        ]
    },
    {
        "codepoints": "♏",
        "name": "Scorpio",
        "shortcodes": [
            ":Scorpio:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Scorpio",
            "scorpion",
            "scorpius",
            "zodiac",
            "Scorpius"
        ]
    },
    {
        "codepoints": "♐",
        "name": "Sagittarius",
        "shortcodes": [
            ":Sagittarius:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "archer",
            "centaur",
            "Sagittarius",
            "zodiac"
        ]
    },
    {
        "codepoints": "♑",
        "name": "Capricorn",
        "shortcodes": [
            ":Capricorn:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Capricorn",
            "goat",
            "zodiac"
        ]
    },
    {
        "codepoints": "♒",
        "name": "Aquarius",
        "shortcodes": [
            ":Aquarius:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "Aquarius",
            "water bearer",
            "zodiac",
            "bearer",
            "water"
        ]
    },
    {
        "codepoints": "♓",
        "name": "Pisces",
        "shortcodes": [
            ":Pisces:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "fish",
            "Pisces",
            "zodiac"
        ]
    },
    {
        "codepoints": "⛎",
        "name": "Ophiuchus",
        "shortcodes": [
            ":Ophiuchus:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "bearer",
            "Ophiuchus",
            "serpent",
            "snake",
            "zodiac"
        ]
    },
    {
        "codepoints": "🔀",
        "name": "shuffle tracks button",
        "shortcodes": [
            ":shuffle_tracks_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "crossed",
            "shuffle tracks button"
        ]
    },
    {
        "codepoints": "🔁",
        "name": "repeat button",
        "shortcodes": [
            ":repeat_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "clockwise",
            "repeat",
            "repeat button"
        ]
    },
    {
        "codepoints": "🔂",
        "name": "repeat single button",
        "shortcodes": [
            ":repeat_single_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "clockwise",
            "once",
            "repeat single button"
        ]
    },
    {
        "codepoints": "▶️",
        "name": "play button",
        "shortcodes": [
            ":play_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "play",
            "play button",
            "right",
            "triangle"
        ]
    },
    {
        "codepoints": "⏩",
        "name": "fast-forward button",
        "shortcodes": [
            ":fast-forward_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "fast forward button",
            "arrow",
            "double",
            "fast",
            "fast-forward button",
            "forward"
        ]
    },
    {
        "codepoints": "⏭️",
        "name": "next track button",
        "shortcodes": [
            ":next_track_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "next scene",
            "next track",
            "next track button",
            "triangle"
        ]
    },
    {
        "codepoints": "⏯️",
        "name": "play or pause button",
        "shortcodes": [
            ":play_or_pause_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "pause",
            "play",
            "play or pause button",
            "right",
            "triangle"
        ]
    },
    {
        "codepoints": "◀️",
        "name": "reverse button",
        "shortcodes": [
            ":reverse_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "left",
            "reverse",
            "reverse button",
            "triangle"
        ]
    },
    {
        "codepoints": "⏪",
        "name": "fast reverse button",
        "shortcodes": [
            ":fast_reverse_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "double",
            "fast reverse button",
            "rewind"
        ]
    },
    {
        "codepoints": "⏮️",
        "name": "last track button",
        "shortcodes": [
            ":last_track_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "last track button",
            "previous scene",
            "previous track",
            "triangle"
        ]
    },
    {
        "codepoints": "🔼",
        "name": "upwards button",
        "shortcodes": [
            ":upwards_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "button",
            "red",
            "upwards button",
            "upward button"
        ]
    },
    {
        "codepoints": "⏫",
        "name": "fast up button",
        "shortcodes": [
            ":fast_up_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "double",
            "fast up button"
        ]
    },
    {
        "codepoints": "🔽",
        "name": "downwards button",
        "shortcodes": [
            ":downwards_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "button",
            "down",
            "downwards button",
            "red",
            "downward button"
        ]
    },
    {
        "codepoints": "⏬",
        "name": "fast down button",
        "shortcodes": [
            ":fast_down_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "arrow",
            "double",
            "down",
            "fast down button"
        ]
    },
    {
        "codepoints": "⏸️",
        "name": "pause button",
        "shortcodes": [
            ":pause_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "bar",
            "double",
            "pause",
            "pause button",
            "vertical"
        ]
    },
    {
        "codepoints": "⏹️",
        "name": "stop button",
        "shortcodes": [
            ":stop_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "square",
            "stop",
            "stop button"
        ]
    },
    {
        "codepoints": "⏺️",
        "name": "record button",
        "shortcodes": [
            ":record_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "record",
            "record button"
        ]
    },
    {
        "codepoints": "⏏️",
        "name": "eject button",
        "shortcodes": [
            ":eject_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "eject",
            "eject button"
        ]
    },
    {
        "codepoints": "🎦",
        "name": "cinema",
        "shortcodes": [
            ":cinema:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "camera",
            "cinema",
            "film",
            "movie"
        ]
    },
    {
        "codepoints": "🔅",
        "name": "dim button",
        "shortcodes": [
            ":dim_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "brightness",
            "dim",
            "dim button",
            "low"
        ]
    },
    {
        "codepoints": "🔆",
        "name": "bright button",
        "shortcodes": [
            ":bright_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "bright button",
            "brightness",
            "brightness button",
            "bright"
        ]
    },
    {
        "codepoints": "📶",
        "name": "antenna bars",
        "shortcodes": [
            ":antenna_bars:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "antenna",
            "antenna bars",
            "bar",
            "cell",
            "mobile",
            "phone"
        ]
    },
    {
        "codepoints": "📳",
        "name": "vibration mode",
        "shortcodes": [
            ":vibration_mode:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "cell",
            "mobile",
            "mode",
            "phone",
            "telephone",
            "vibration",
            "vibrate"
        ]
    },
    {
        "codepoints": "📴",
        "name": "mobile phone off",
        "shortcodes": [
            ":mobile_phone_off:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "cell",
            "mobile",
            "off",
            "phone",
            "telephone"
        ]
    },
    {
        "codepoints": "♀️",
        "name": "female sign",
        "shortcodes": [
            ":female_sign:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "female sign",
            "woman"
        ]
    },
    {
        "codepoints": "♂️",
        "name": "male sign",
        "shortcodes": [
            ":male_sign:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "male sign",
            "man"
        ]
    },
    {
        "codepoints": "⚧️",
        "name": "transgender symbol",
        "shortcodes": [
            ":transgender_symbol:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "transgender",
            "transgender symbol",
            "trans"
        ]
    },
    {
        "codepoints": "✖️",
        "name": "multiply",
        "shortcodes": [
            ":multiply:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "×",
            "cancel",
            "multiplication",
            "multiply",
            "sign",
            "x",
            "heavy multiplication sign"
        ]
    },
    {
        "codepoints": "➕",
        "name": "plus",
        "shortcodes": [
            ":plus:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "+",
            "add",
            "addition",
            "math",
            "maths",
            "plus",
            "sign"
        ]
    },
    {
        "codepoints": "➖",
        "name": "minus",
        "shortcodes": [
            ":minus:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "-",
            "–",
            "math",
            "maths",
            "minus",
            "sign",
            "subtraction",
            "−",
            "heavy minus sign"
        ]
    },
    {
        "codepoints": "➗",
        "name": "divide",
        "shortcodes": [
            ":divide:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "÷",
            "divide",
            "division",
            "math",
            "sign"
        ]
    },
    {
        "codepoints": "🟰",
        "name": "heavy equals sign",
        "shortcodes": [
            ":heavy_equals_sign:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "equality",
            "heavy equals sign",
            "maths",
            "math"
        ]
    },
    {
        "codepoints": "♾️",
        "name": "infinity",
        "shortcodes": [
            ":infinity:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "eternal",
            "forever",
            "infinity",
            "unbound",
            "universal",
            "unbounded"
        ]
    },
    {
        "codepoints": "‼️",
        "name": "double exclamation mark",
        "shortcodes": [
            ":double_exclamation_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "double exclamation mark",
            "exclamation",
            "mark",
            "punctuation",
            "!",
            "!!",
            "bangbang"
        ]
    },
    {
        "codepoints": "⁉️",
        "name": "exclamation question mark",
        "shortcodes": [
            ":exclamation_question_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "exclamation",
            "mark",
            "punctuation",
            "question",
            "!",
            "!?",
            "?",
            "interrobang",
            "exclamation question mark"
        ]
    },
    {
        "codepoints": "❓",
        "name": "red question mark",
        "shortcodes": [
            ":red_question_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "?",
            "mark",
            "punctuation",
            "question",
            "red question mark"
        ]
    },
    {
        "codepoints": "❔",
        "name": "white question mark",
        "shortcodes": [
            ":white_question_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "?",
            "mark",
            "outlined",
            "punctuation",
            "question",
            "white question mark"
        ]
    },
    {
        "codepoints": "❕",
        "name": "white exclamation mark",
        "shortcodes": [
            ":white_exclamation_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "!",
            "exclamation",
            "mark",
            "outlined",
            "punctuation",
            "white exclamation mark"
        ]
    },
    {
        "codepoints": "❗",
        "name": "red exclamation mark",
        "shortcodes": [
            ":red_exclamation_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "!",
            "exclamation",
            "mark",
            "punctuation",
            "red exclamation mark"
        ]
    },
    {
        "codepoints": "〰️",
        "name": "wavy dash",
        "shortcodes": [
            ":wavy_dash:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "dash",
            "punctuation",
            "wavy"
        ]
    },
    {
        "codepoints": "💱",
        "name": "currency exchange",
        "shortcodes": [
            ":currency_exchange:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "bank",
            "currency",
            "exchange",
            "money"
        ]
    },
    {
        "codepoints": "💲",
        "name": "heavy dollar sign",
        "shortcodes": [
            ":heavy_dollar_sign:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "currency",
            "dollar",
            "heavy dollar sign",
            "money"
        ]
    },
    {
        "codepoints": "⚕️",
        "name": "medical symbol",
        "shortcodes": [
            ":medical_symbol:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "aesculapius",
            "medical symbol",
            "medicine",
            "staff"
        ]
    },
    {
        "codepoints": "♻️",
        "name": "recycling symbol",
        "shortcodes": [
            ":recycling_symbol:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "recycle",
            "recycling symbol"
        ]
    },
    {
        "codepoints": "⚜️",
        "name": "fleur-de-lis",
        "shortcodes": [
            ":fleur-de-lis:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "fleur-de-lis"
        ]
    },
    {
        "codepoints": "🔱",
        "name": "trident emblem",
        "shortcodes": [
            ":trident_emblem:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "anchor",
            "emblem",
            "ship",
            "tool",
            "trident"
        ]
    },
    {
        "codepoints": "📛",
        "name": "name badge",
        "shortcodes": [
            ":name_badge:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "badge",
            "name"
        ]
    },
    {
        "codepoints": "🔰",
        "name": "Japanese symbol for beginner",
        "shortcodes": [
            ":Japanese_symbol_for_beginner:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "beginner",
            "chevron",
            "Japanese",
            "Japanese symbol for beginner",
            "leaf"
        ]
    },
    {
        "codepoints": "⭕",
        "name": "hollow red circle",
        "shortcodes": [
            ":hollow_red_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "hollow red circle",
            "large",
            "o",
            "red"
        ]
    },
    {
        "codepoints": "✅",
        "name": "check mark button",
        "shortcodes": [
            ":check_mark_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "✓",
            "button",
            "check",
            "mark",
            "tick"
        ]
    },
    {
        "codepoints": "☑️",
        "name": "check box with check",
        "shortcodes": [
            ":check_box_with_check:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "ballot",
            "box",
            "check box with check",
            "tick",
            "tick box with tick",
            "✓",
            "check"
        ]
    },
    {
        "codepoints": "✔️",
        "name": "check mark",
        "shortcodes": [
            ":check_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "check mark",
            "heavy tick mark",
            "mark",
            "tick",
            "✓",
            "check"
        ]
    },
    {
        "codepoints": "❌",
        "name": "cross mark",
        "shortcodes": [
            ":cross_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "×",
            "cancel",
            "cross",
            "mark",
            "multiplication",
            "multiply",
            "x"
        ]
    },
    {
        "codepoints": "❎",
        "name": "cross mark button",
        "shortcodes": [
            ":cross_mark_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "×",
            "cross mark button",
            "mark",
            "square",
            "x"
        ]
    },
    {
        "codepoints": "➰",
        "name": "curly loop",
        "shortcodes": [
            ":curly_loop:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "curl",
            "curly loop",
            "loop"
        ]
    },
    {
        "codepoints": "➿",
        "name": "double curly loop",
        "shortcodes": [
            ":double_curly_loop:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "curl",
            "double",
            "double curly loop",
            "loop"
        ]
    },
    {
        "codepoints": "〽️",
        "name": "part alternation mark",
        "shortcodes": [
            ":part_alternation_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "mark",
            "part",
            "part alternation mark"
        ]
    },
    {
        "codepoints": "✳️",
        "name": "eight-spoked asterisk",
        "shortcodes": [
            ":eight-spoked_asterisk:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "*",
            "asterisk",
            "eight-spoked asterisk"
        ]
    },
    {
        "codepoints": "✴️",
        "name": "eight-pointed star",
        "shortcodes": [
            ":eight-pointed_star:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "*",
            "eight-pointed star",
            "star"
        ]
    },
    {
        "codepoints": "❇️",
        "name": "sparkle",
        "shortcodes": [
            ":sparkle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "*",
            "sparkle"
        ]
    },
    {
        "codepoints": "©️",
        "name": "copyright",
        "shortcodes": [
            ":copyright:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "C",
            "copyright"
        ]
    },
    {
        "codepoints": "®️",
        "name": "registered",
        "shortcodes": [
            ":registered:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "R",
            "registered",
            "r",
            "trademark"
        ]
    },
    {
        "codepoints": "™️",
        "name": "trade mark",
        "shortcodes": [
            ":trade_mark:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "mark",
            "TM",
            "trade mark",
            "trademark"
        ]
    },
    {
        "codepoints": "#️⃣",
        "name": "keycap: #",
        "shortcodes": [
            ":keycap:_#:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "*️⃣",
        "name": "keycap: *",
        "shortcodes": [
            ":keycap:_*:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "0️⃣",
        "name": "keycap: 0",
        "shortcodes": [
            ":keycap:_0:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "1️⃣",
        "name": "keycap: 1",
        "shortcodes": [
            ":keycap:_1:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "2️⃣",
        "name": "keycap: 2",
        "shortcodes": [
            ":keycap:_2:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "3️⃣",
        "name": "keycap: 3",
        "shortcodes": [
            ":keycap:_3:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "4️⃣",
        "name": "keycap: 4",
        "shortcodes": [
            ":keycap:_4:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "5️⃣",
        "name": "keycap: 5",
        "shortcodes": [
            ":keycap:_5:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "6️⃣",
        "name": "keycap: 6",
        "shortcodes": [
            ":keycap:_6:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "7️⃣",
        "name": "keycap: 7",
        "shortcodes": [
            ":keycap:_7:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "8️⃣",
        "name": "keycap: 8",
        "shortcodes": [
            ":keycap:_8:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "9️⃣",
        "name": "keycap: 9",
        "shortcodes": [
            ":keycap:_9:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "🔟",
        "name": "keycap: 10",
        "shortcodes": [
            ":keycap:_10:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "keycap"
        ]
    },
    {
        "codepoints": "🔠",
        "name": "input latin uppercase",
        "shortcodes": [
            ":input_latin_uppercase:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "input Latin uppercase",
            "ABCD",
            "input",
            "latin",
            "letters",
            "uppercase",
            "Latin"
        ]
    },
    {
        "codepoints": "🔡",
        "name": "input latin lowercase",
        "shortcodes": [
            ":input_latin_lowercase:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "input Latin lowercase",
            "abcd",
            "input",
            "latin",
            "letters",
            "lowercase",
            "Latin"
        ]
    },
    {
        "codepoints": "🔢",
        "name": "input numbers",
        "shortcodes": [
            ":input_numbers:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "1234",
            "input",
            "numbers"
        ]
    },
    {
        "codepoints": "🔣",
        "name": "input symbols",
        "shortcodes": [
            ":input_symbols:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "〒♪&%",
            "input",
            "input symbols"
        ]
    },
    {
        "codepoints": "🔤",
        "name": "input latin letters",
        "shortcodes": [
            ":input_latin_letters:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "input Latin letters",
            "abc",
            "alphabet",
            "input",
            "latin",
            "letters",
            "Latin"
        ]
    },
    {
        "codepoints": "🅰️",
        "name": "A button (blood type)",
        "shortcodes": [
            ":A_button_(blood_type):"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "A",
            "A button (blood type)",
            "blood type"
        ]
    },
    {
        "codepoints": "🆎",
        "name": "AB button (blood type)",
        "shortcodes": [
            ":AB_button_(blood_type):"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "AB",
            "AB button (blood type)",
            "blood type"
        ]
    },
    {
        "codepoints": "🅱️",
        "name": "B button (blood type)",
        "shortcodes": [
            ":B_button_(blood_type):"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "B",
            "B button (blood type)",
            "blood type"
        ]
    },
    {
        "codepoints": "🆑",
        "name": "CL button",
        "shortcodes": [
            ":CL_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "CL",
            "CL button"
        ]
    },
    {
        "codepoints": "🆒",
        "name": "COOL button",
        "shortcodes": [
            ":COOL_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "COOL",
            "COOL button"
        ]
    },
    {
        "codepoints": "🆓",
        "name": "FREE button",
        "shortcodes": [
            ":FREE_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "FREE",
            "FREE button"
        ]
    },
    {
        "codepoints": "ℹ️",
        "name": "information",
        "shortcodes": [
            ":information:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "i",
            "information"
        ]
    },
    {
        "codepoints": "🆔",
        "name": "ID button",
        "shortcodes": [
            ":ID_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "ID",
            "ID button",
            "identity"
        ]
    },
    {
        "codepoints": "Ⓜ️",
        "name": "circled M",
        "shortcodes": [
            ":circled_M:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "circled M",
            "M"
        ]
    },
    {
        "codepoints": "🆕",
        "name": "NEW button",
        "shortcodes": [
            ":NEW_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "NEW",
            "NEW button"
        ]
    },
    {
        "codepoints": "🆖",
        "name": "NG button",
        "shortcodes": [
            ":NG_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "NG",
            "NG button"
        ]
    },
    {
        "codepoints": "🅾️",
        "name": "O button (blood type)",
        "shortcodes": [
            ":O_button_(blood_type):"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "blood type",
            "O",
            "O button (blood type)"
        ]
    },
    {
        "codepoints": "🆗",
        "name": "OK button",
        "shortcodes": [
            ":OK_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "OK",
            "OK button"
        ]
    },
    {
        "codepoints": "🅿️",
        "name": "P button",
        "shortcodes": [
            ":P_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "P",
            "P button",
            "parking"
        ]
    },
    {
        "codepoints": "🆘",
        "name": "SOS button",
        "shortcodes": [
            ":SOS_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "help",
            "SOS",
            "SOS button"
        ]
    },
    {
        "codepoints": "🆙",
        "name": "UP! button",
        "shortcodes": [
            ":UP!_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "mark",
            "UP",
            "UP!",
            "UP! button"
        ]
    },
    {
        "codepoints": "🆚",
        "name": "VS button",
        "shortcodes": [
            ":VS_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "versus",
            "VS",
            "VS button"
        ]
    },
    {
        "codepoints": "🈁",
        "name": "Japanese “here” button",
        "shortcodes": [
            ":Japanese_“here”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“here”",
            "Japanese",
            "Japanese “here” button",
            "katakana",
            "ココ"
        ]
    },
    {
        "codepoints": "🈂️",
        "name": "Japanese “service charge” button",
        "shortcodes": [
            ":Japanese_“service_charge”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“service charge”",
            "Japanese",
            "Japanese “service charge” button",
            "katakana",
            "サ"
        ]
    },
    {
        "codepoints": "🈷️",
        "name": "Japanese “monthly amount” button",
        "shortcodes": [
            ":Japanese_“monthly_amount”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“monthly amount”",
            "ideograph",
            "Japanese",
            "Japanese “monthly amount” button",
            "月"
        ]
    },
    {
        "codepoints": "🈶",
        "name": "Japanese “not free of charge” button",
        "shortcodes": [
            ":Japanese_“not_free_of_charge”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“not free of charge”",
            "ideograph",
            "Japanese",
            "Japanese “not free of charge” button",
            "有"
        ]
    },
    {
        "codepoints": "🈯",
        "name": "Japanese “reserved” button",
        "shortcodes": [
            ":Japanese_“reserved”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“reserved”",
            "ideograph",
            "Japanese",
            "Japanese “reserved” button",
            "指"
        ]
    },
    {
        "codepoints": "🉐",
        "name": "Japanese “bargain” button",
        "shortcodes": [
            ":Japanese_“bargain”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“bargain”",
            "ideograph",
            "Japanese",
            "Japanese “bargain” button",
            "得"
        ]
    },
    {
        "codepoints": "🈹",
        "name": "Japanese “discount” button",
        "shortcodes": [
            ":Japanese_“discount”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“discount”",
            "ideograph",
            "Japanese",
            "Japanese “discount” button",
            "割"
        ]
    },
    {
        "codepoints": "🈚",
        "name": "Japanese “free of charge” button",
        "shortcodes": [
            ":Japanese_“free_of_charge”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“free of charge”",
            "ideograph",
            "Japanese",
            "Japanese “free of charge” button",
            "無"
        ]
    },
    {
        "codepoints": "🈲",
        "name": "Japanese “prohibited” button",
        "shortcodes": [
            ":Japanese_“prohibited”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“prohibited”",
            "ideograph",
            "Japanese",
            "Japanese “prohibited” button",
            "禁"
        ]
    },
    {
        "codepoints": "🉑",
        "name": "Japanese “acceptable” button",
        "shortcodes": [
            ":Japanese_“acceptable”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“acceptable”",
            "ideograph",
            "Japanese",
            "Japanese “acceptable” button",
            "可"
        ]
    },
    {
        "codepoints": "🈸",
        "name": "Japanese “application” button",
        "shortcodes": [
            ":Japanese_“application”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“application”",
            "ideograph",
            "Japanese",
            "Japanese “application” button",
            "申"
        ]
    },
    {
        "codepoints": "🈴",
        "name": "Japanese “passing grade” button",
        "shortcodes": [
            ":Japanese_“passing_grade”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“passing grade”",
            "ideograph",
            "Japanese",
            "Japanese “passing grade” button",
            "合"
        ]
    },
    {
        "codepoints": "🈳",
        "name": "Japanese “vacancy” button",
        "shortcodes": [
            ":Japanese_“vacancy”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“vacancy”",
            "ideograph",
            "Japanese",
            "Japanese “vacancy” button",
            "空"
        ]
    },
    {
        "codepoints": "㊗️",
        "name": "Japanese “congratulations” button",
        "shortcodes": [
            ":Japanese_“congratulations”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“congratulations”",
            "ideograph",
            "Japanese",
            "Japanese “congratulations” button",
            "祝"
        ]
    },
    {
        "codepoints": "㊙️",
        "name": "Japanese “secret” button",
        "shortcodes": [
            ":Japanese_“secret”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“secret”",
            "ideograph",
            "Japanese",
            "Japanese “secret” button",
            "秘"
        ]
    },
    {
        "codepoints": "🈺",
        "name": "Japanese “open for business” button",
        "shortcodes": [
            ":Japanese_“open_for_business”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“open for business”",
            "ideograph",
            "Japanese",
            "Japanese “open for business” button",
            "営"
        ]
    },
    {
        "codepoints": "🈵",
        "name": "Japanese “no vacancy” button",
        "shortcodes": [
            ":Japanese_“no_vacancy”_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "“no vacancy”",
            "ideograph",
            "Japanese",
            "Japanese “no vacancy” button",
            "満"
        ]
    },
    {
        "codepoints": "🔴",
        "name": "red circle",
        "shortcodes": [
            ":red_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "geometric",
            "red"
        ]
    },
    {
        "codepoints": "🟠",
        "name": "orange circle",
        "shortcodes": [
            ":orange_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "orange"
        ]
    },
    {
        "codepoints": "🟡",
        "name": "yellow circle",
        "shortcodes": [
            ":yellow_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "yellow"
        ]
    },
    {
        "codepoints": "🟢",
        "name": "green circle",
        "shortcodes": [
            ":green_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "green"
        ]
    },
    {
        "codepoints": "🔵",
        "name": "blue circle",
        "shortcodes": [
            ":blue_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "blue",
            "circle",
            "geometric"
        ]
    },
    {
        "codepoints": "🟣",
        "name": "purple circle",
        "shortcodes": [
            ":purple_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "purple"
        ]
    },
    {
        "codepoints": "🟤",
        "name": "brown circle",
        "shortcodes": [
            ":brown_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "brown",
            "circle"
        ]
    },
    {
        "codepoints": "⚫",
        "name": "black circle",
        "shortcodes": [
            ":black_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "black circle",
            "circle",
            "geometric"
        ]
    },
    {
        "codepoints": "⚪",
        "name": "white circle",
        "shortcodes": [
            ":white_circle:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "circle",
            "geometric",
            "white circle"
        ]
    },
    {
        "codepoints": "🟥",
        "name": "red square",
        "shortcodes": [
            ":red_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "red",
            "square"
        ]
    },
    {
        "codepoints": "🟧",
        "name": "orange square",
        "shortcodes": [
            ":orange_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "orange",
            "square"
        ]
    },
    {
        "codepoints": "🟨",
        "name": "yellow square",
        "shortcodes": [
            ":yellow_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "square",
            "yellow"
        ]
    },
    {
        "codepoints": "🟩",
        "name": "green square",
        "shortcodes": [
            ":green_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "green",
            "square"
        ]
    },
    {
        "codepoints": "🟦",
        "name": "blue square",
        "shortcodes": [
            ":blue_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "blue",
            "square"
        ]
    },
    {
        "codepoints": "🟪",
        "name": "purple square",
        "shortcodes": [
            ":purple_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "purple",
            "square"
        ]
    },
    {
        "codepoints": "🟫",
        "name": "brown square",
        "shortcodes": [
            ":brown_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "brown",
            "square"
        ]
    },
    {
        "codepoints": "⬛",
        "name": "black large square",
        "shortcodes": [
            ":black_large_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "black large square",
            "geometric",
            "square"
        ]
    },
    {
        "codepoints": "⬜",
        "name": "white large square",
        "shortcodes": [
            ":white_large_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "geometric",
            "square",
            "white large square"
        ]
    },
    {
        "codepoints": "◼️",
        "name": "black medium square",
        "shortcodes": [
            ":black_medium_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "black medium square",
            "geometric",
            "square"
        ]
    },
    {
        "codepoints": "◻️",
        "name": "white medium square",
        "shortcodes": [
            ":white_medium_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "geometric",
            "square",
            "white medium square"
        ]
    },
    {
        "codepoints": "◾",
        "name": "black medium-small square",
        "shortcodes": [
            ":black_medium-small_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "black medium-small square",
            "geometric",
            "square"
        ]
    },
    {
        "codepoints": "◽",
        "name": "white medium-small square",
        "shortcodes": [
            ":white_medium-small_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "geometric",
            "square",
            "white medium-small square"
        ]
    },
    {
        "codepoints": "▪️",
        "name": "black small square",
        "shortcodes": [
            ":black_small_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "black small square",
            "geometric",
            "square"
        ]
    },
    {
        "codepoints": "▫️",
        "name": "white small square",
        "shortcodes": [
            ":white_small_square:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "geometric",
            "square",
            "white small square"
        ]
    },
    {
        "codepoints": "🔶",
        "name": "large orange diamond",
        "shortcodes": [
            ":large_orange_diamond:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "diamond",
            "geometric",
            "large orange diamond",
            "orange"
        ]
    },
    {
        "codepoints": "🔷",
        "name": "large blue diamond",
        "shortcodes": [
            ":large_blue_diamond:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "blue",
            "diamond",
            "geometric",
            "large blue diamond"
        ]
    },
    {
        "codepoints": "🔸",
        "name": "small orange diamond",
        "shortcodes": [
            ":small_orange_diamond:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "diamond",
            "geometric",
            "orange",
            "small orange diamond"
        ]
    },
    {
        "codepoints": "🔹",
        "name": "small blue diamond",
        "shortcodes": [
            ":small_blue_diamond:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "blue",
            "diamond",
            "geometric",
            "small blue diamond"
        ]
    },
    {
        "codepoints": "🔺",
        "name": "red triangle pointed up",
        "shortcodes": [
            ":red_triangle_pointed_up:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "geometric",
            "red",
            "red triangle pointed up"
        ]
    },
    {
        "codepoints": "🔻",
        "name": "red triangle pointed down",
        "shortcodes": [
            ":red_triangle_pointed_down:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "down",
            "geometric",
            "red",
            "red triangle pointed down"
        ]
    },
    {
        "codepoints": "💠",
        "name": "diamond with a dot",
        "shortcodes": [
            ":diamond_with_a_dot:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "comic",
            "diamond",
            "diamond with a dot",
            "geometric",
            "inside"
        ]
    },
    {
        "codepoints": "🔘",
        "name": "radio button",
        "shortcodes": [
            ":radio_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "button",
            "geometric",
            "radio"
        ]
    },
    {
        "codepoints": "🔳",
        "name": "white square button",
        "shortcodes": [
            ":white_square_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "button",
            "geometric",
            "outlined",
            "square",
            "white square button"
        ]
    },
    {
        "codepoints": "🔲",
        "name": "black square button",
        "shortcodes": [
            ":black_square_button:"
        ],
        "emoticons": [],
        "category": "Symbols",
        "keywords": [
            "black square button",
            "button",
            "geometric",
            "square"
        ]
    },
    {
        "codepoints": "🏁",
        "name": "chequered flag",
        "shortcodes": [
            ":chequered_flag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "checkered",
            "chequered",
            "chequered flag",
            "racing",
            "checkered flag"
        ]
    },
    {
        "codepoints": "🚩",
        "name": "triangular flag",
        "shortcodes": [
            ":triangular_flag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "post",
            "triangular flag",
            "red flag"
        ]
    },
    {
        "codepoints": "🎌",
        "name": "crossed flags",
        "shortcodes": [
            ":crossed_flags:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "celebration",
            "cross",
            "crossed",
            "crossed flags",
            "Japanese"
        ]
    },
    {
        "codepoints": "🏴",
        "name": "black flag",
        "shortcodes": [
            ":black_flag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "black flag",
            "waving"
        ]
    },
    {
        "codepoints": "🏳️",
        "name": "white flag",
        "shortcodes": [
            ":white_flag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "waving",
            "white flag",
            "surrender"
        ]
    },
    {
        "codepoints": "🏳️‍🌈",
        "name": "rainbow flag",
        "shortcodes": [
            ":rainbow_flag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "pride",
            "rainbow",
            "rainbow flag"
        ]
    },
    {
        "codepoints": "🏳️‍⚧️",
        "name": "transgender flag",
        "shortcodes": [
            ":transgender_flag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": []
    },
    {
        "codepoints": "🏴‍☠️",
        "name": "pirate flag",
        "shortcodes": [
            ":pirate_flag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "Jolly Roger",
            "pirate",
            "pirate flag",
            "plunder",
            "treasure"
        ]
    },
    {
        "codepoints": "🇦🇨",
        "name": "flag: Ascension Island",
        "shortcodes": [
            ":flag_ac:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇩",
        "name": "flag: Andorra",
        "shortcodes": [
            ":flag_ad:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇪",
        "name": "flag: United Arab Emirates",
        "shortcodes": [
            ":flag_ae:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇫",
        "name": "flag: Afghanistan",
        "shortcodes": [
            ":flag_af:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇬",
        "name": "flag: Antigua & Barbuda",
        "shortcodes": [
            ":flag_ag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇮",
        "name": "flag: Anguilla",
        "shortcodes": [
            ":flag_ai:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇱",
        "name": "flag: Albania",
        "shortcodes": [
            ":flag_al:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇲",
        "name": "flag: Armenia",
        "shortcodes": [
            ":flag_am:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇴",
        "name": "flag: Angola",
        "shortcodes": [
            ":flag_ao:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇶",
        "name": "flag: Antarctica",
        "shortcodes": [
            ":flag_aq:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇷",
        "name": "flag: Argentina",
        "shortcodes": [
            ":flag_ar:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇸",
        "name": "flag: American Samoa",
        "shortcodes": [
            ":flag_as:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇹",
        "name": "flag: Austria",
        "shortcodes": [
            ":flag_at:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇺",
        "name": "flag: Australia",
        "shortcodes": [
            ":flag_au:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇼",
        "name": "flag: Aruba",
        "shortcodes": [
            ":flag_aw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇽",
        "name": "flag: Åland Islands",
        "shortcodes": [
            ":flag_ax:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇦🇿",
        "name": "flag: Azerbaijan",
        "shortcodes": [
            ":flag_az:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇦",
        "name": "flag: Bosnia & Herzegovina",
        "shortcodes": [
            ":flag_ba:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇧",
        "name": "flag: Barbados",
        "shortcodes": [
            ":flag_bb:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇩",
        "name": "flag: Bangladesh",
        "shortcodes": [
            ":flag_bd:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇪",
        "name": "flag: Belgium",
        "shortcodes": [
            ":flag_be:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇫",
        "name": "flag: Burkina Faso",
        "shortcodes": [
            ":flag_bf:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇬",
        "name": "flag: Bulgaria",
        "shortcodes": [
            ":flag_bg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇭",
        "name": "flag: Bahrain",
        "shortcodes": [
            ":flag_bh:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇮",
        "name": "flag: Burundi",
        "shortcodes": [
            ":flag_bi:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇯",
        "name": "flag: Benin",
        "shortcodes": [
            ":flag_bj:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇱",
        "name": "flag: St. Barthélemy",
        "shortcodes": [
            ":flag_bl:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇲",
        "name": "flag: Bermuda",
        "shortcodes": [
            ":flag_bm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇳",
        "name": "flag: Brunei",
        "shortcodes": [
            ":flag_bn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇴",
        "name": "flag: Bolivia",
        "shortcodes": [
            ":flag_bo:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇶",
        "name": "flag: Caribbean Netherlands",
        "shortcodes": [
            ":flag_bq:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇷",
        "name": "flag: Brazil",
        "shortcodes": [
            ":flag_br:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇸",
        "name": "flag: Bahamas",
        "shortcodes": [
            ":flag_bs:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇹",
        "name": "flag: Bhutan",
        "shortcodes": [
            ":flag_bt:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇻",
        "name": "flag: Bouvet Island",
        "shortcodes": [
            ":flag_bv:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇼",
        "name": "flag: Botswana",
        "shortcodes": [
            ":flag_bw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇾",
        "name": "flag: Belarus",
        "shortcodes": [
            ":flag_by:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇧🇿",
        "name": "flag: Belize",
        "shortcodes": [
            ":flag_bz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇦",
        "name": "flag: Canada",
        "shortcodes": [
            ":flag_ca:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇨",
        "name": "flag: Cocos (Keeling) Islands",
        "shortcodes": [
            ":flag_cc:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇩",
        "name": "flag: Congo - Kinshasa",
        "shortcodes": [
            ":flag_cd:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇫",
        "name": "flag: Central African Republic",
        "shortcodes": [
            ":flag_cf:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇬",
        "name": "flag: Congo - Brazzaville",
        "shortcodes": [
            ":flag_cg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇭",
        "name": "flag: Switzerland",
        "shortcodes": [
            ":flag_ch:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇮",
        "name": "flag: Côte d’Ivoire",
        "shortcodes": [
            ":flag_ci:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇰",
        "name": "flag: Cook Islands",
        "shortcodes": [
            ":flag_ck:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇱",
        "name": "flag: Chile",
        "shortcodes": [
            ":flag_cl:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇲",
        "name": "flag: Cameroon",
        "shortcodes": [
            ":flag_cm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇳",
        "name": "flag: China",
        "shortcodes": [
            ":flag_cn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇴",
        "name": "flag: Colombia",
        "shortcodes": [
            ":flag_co:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇵",
        "name": "flag: Clipperton Island",
        "shortcodes": [
            ":flag_cp:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇷",
        "name": "flag: Costa Rica",
        "shortcodes": [
            ":flag_cr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇺",
        "name": "flag: Cuba",
        "shortcodes": [
            ":flag_cu:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇻",
        "name": "flag: Cape Verde",
        "shortcodes": [
            ":flag_cv:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇼",
        "name": "flag: Curaçao",
        "shortcodes": [
            ":flag_cw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇽",
        "name": "flag: Christmas Island",
        "shortcodes": [
            ":flag_cx:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇾",
        "name": "flag: Cyprus",
        "shortcodes": [
            ":flag_cy:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇨🇿",
        "name": "flag: Czechia",
        "shortcodes": [
            ":flag_cz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇩🇪",
        "name": "flag: Germany",
        "shortcodes": [
            ":flag_de:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇩🇬",
        "name": "flag: Diego Garcia",
        "shortcodes": [
            ":flag_dg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇩🇯",
        "name": "flag: Djibouti",
        "shortcodes": [
            ":flag_dj:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇩🇰",
        "name": "flag: Denmark",
        "shortcodes": [
            ":flag_dk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇩🇲",
        "name": "flag: Dominica",
        "shortcodes": [
            ":flag_dm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇩🇴",
        "name": "flag: Dominican Republic",
        "shortcodes": [
            ":flag_do:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇩🇿",
        "name": "flag: Algeria",
        "shortcodes": [
            ":flag_dz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇦",
        "name": "flag: Ceuta & Melilla",
        "shortcodes": [
            ":flag_ea:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇨",
        "name": "flag: Ecuador",
        "shortcodes": [
            ":flag_ec:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇪",
        "name": "flag: Estonia",
        "shortcodes": [
            ":flag_ee:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇬",
        "name": "flag: Egypt",
        "shortcodes": [
            ":flag_eg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇭",
        "name": "flag: Western Sahara",
        "shortcodes": [
            ":flag_eh:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇷",
        "name": "flag: Eritrea",
        "shortcodes": [
            ":flag_er:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇸",
        "name": "flag: Spain",
        "shortcodes": [
            ":flag_es:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇹",
        "name": "flag: Ethiopia",
        "shortcodes": [
            ":flag_et:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇪🇺",
        "name": "flag: European Union",
        "shortcodes": [
            ":flag_eu:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇫🇮",
        "name": "flag: Finland",
        "shortcodes": [
            ":flag_fi:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇫🇯",
        "name": "flag: Fiji",
        "shortcodes": [
            ":flag_fj:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇫🇰",
        "name": "flag: Falkland Islands",
        "shortcodes": [
            ":flag_fk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇫🇲",
        "name": "flag: Micronesia",
        "shortcodes": [
            ":flag_fm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇫🇴",
        "name": "flag: Faroe Islands",
        "shortcodes": [
            ":flag_fo:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇫🇷",
        "name": "flag: France",
        "shortcodes": [
            ":flag_fr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇦",
        "name": "flag: Gabon",
        "shortcodes": [
            ":flag_ga:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇧",
        "name": "flag: United Kingdom",
        "shortcodes": [
            ":flag_gb:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇩",
        "name": "flag: Grenada",
        "shortcodes": [
            ":flag_gd:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇪",
        "name": "flag: Georgia",
        "shortcodes": [
            ":flag_ge:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇫",
        "name": "flag: French Guiana",
        "shortcodes": [
            ":flag_gf:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇬",
        "name": "flag: Guernsey",
        "shortcodes": [
            ":flag_gg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇭",
        "name": "flag: Ghana",
        "shortcodes": [
            ":flag_gh:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇮",
        "name": "flag: Gibraltar",
        "shortcodes": [
            ":flag_gi:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇱",
        "name": "flag: Greenland",
        "shortcodes": [
            ":flag_gl:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇲",
        "name": "flag: Gambia",
        "shortcodes": [
            ":flag_gm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇳",
        "name": "flag: Guinea",
        "shortcodes": [
            ":flag_gn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇵",
        "name": "flag: Guadeloupe",
        "shortcodes": [
            ":flag_gp:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇶",
        "name": "flag: Equatorial Guinea",
        "shortcodes": [
            ":flag_gq:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇷",
        "name": "flag: Greece",
        "shortcodes": [
            ":flag_gr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇸",
        "name": "flag: South Georgia & South Sandwich Islands",
        "shortcodes": [
            ":flag_gs:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇹",
        "name": "flag: Guatemala",
        "shortcodes": [
            ":flag_gt:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇺",
        "name": "flag: Guam",
        "shortcodes": [
            ":flag_gu:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇼",
        "name": "flag: Guinea-Bissau",
        "shortcodes": [
            ":flag_gw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇬🇾",
        "name": "flag: Guyana",
        "shortcodes": [
            ":flag_gy:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇭🇰",
        "name": "flag: Hong Kong SAR China",
        "shortcodes": [
            ":flag_hk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇭🇲",
        "name": "flag: Heard & McDonald Islands",
        "shortcodes": [
            ":flag_hm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇭🇳",
        "name": "flag: Honduras",
        "shortcodes": [
            ":flag_hn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇭🇷",
        "name": "flag: Croatia",
        "shortcodes": [
            ":flag_hr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇭🇹",
        "name": "flag: Haiti",
        "shortcodes": [
            ":flag_ht:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇭🇺",
        "name": "flag: Hungary",
        "shortcodes": [
            ":flag_hu:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇨",
        "name": "flag: Canary Islands",
        "shortcodes": [
            ":flag_ic:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇩",
        "name": "flag: Indonesia",
        "shortcodes": [
            ":flag_id:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇪",
        "name": "flag: Ireland",
        "shortcodes": [
            ":flag_ie:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇱",
        "name": "flag: Israel",
        "shortcodes": [
            ":flag_il:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇲",
        "name": "flag: Isle of Man",
        "shortcodes": [
            ":flag_im:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇳",
        "name": "flag: India",
        "shortcodes": [
            ":flag_in:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇴",
        "name": "flag: British Indian Ocean Territory",
        "shortcodes": [
            ":flag_io:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇶",
        "name": "flag: Iraq",
        "shortcodes": [
            ":flag_iq:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇷",
        "name": "flag: Iran",
        "shortcodes": [
            ":flag_ir:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇸",
        "name": "flag: Iceland",
        "shortcodes": [
            ":flag_is:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇮🇹",
        "name": "flag: Italy",
        "shortcodes": [
            ":flag_it:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇯🇪",
        "name": "flag: Jersey",
        "shortcodes": [
            ":flag_je:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇯🇲",
        "name": "flag: Jamaica",
        "shortcodes": [
            ":flag_jm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇯🇴",
        "name": "flag: Jordan",
        "shortcodes": [
            ":flag_jo:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇯🇵",
        "name": "flag: Japan",
        "shortcodes": [
            ":flag_jp:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇪",
        "name": "flag: Kenya",
        "shortcodes": [
            ":flag_ke:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇬",
        "name": "flag: Kyrgyzstan",
        "shortcodes": [
            ":flag_kg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇭",
        "name": "flag: Cambodia",
        "shortcodes": [
            ":flag_kh:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇮",
        "name": "flag: Kiribati",
        "shortcodes": [
            ":flag_ki:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇲",
        "name": "flag: Comoros",
        "shortcodes": [
            ":flag_km:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇳",
        "name": "flag: St. Kitts & Nevis",
        "shortcodes": [
            ":flag_kn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇵",
        "name": "flag: North Korea",
        "shortcodes": [
            ":flag_kp:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇷",
        "name": "flag: South Korea",
        "shortcodes": [
            ":flag_kr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇼",
        "name": "flag: Kuwait",
        "shortcodes": [
            ":flag_kw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇾",
        "name": "flag: Cayman Islands",
        "shortcodes": [
            ":flag_ky:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇰🇿",
        "name": "flag: Kazakhstan",
        "shortcodes": [
            ":flag_kz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇦",
        "name": "flag: Laos",
        "shortcodes": [
            ":flag_la:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇧",
        "name": "flag: Lebanon",
        "shortcodes": [
            ":flag_lb:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇨",
        "name": "flag: St. Lucia",
        "shortcodes": [
            ":flag_lc:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇮",
        "name": "flag: Liechtenstein",
        "shortcodes": [
            ":flag_li:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇰",
        "name": "flag: Sri Lanka",
        "shortcodes": [
            ":flag_lk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇷",
        "name": "flag: Liberia",
        "shortcodes": [
            ":flag_lr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇸",
        "name": "flag: Lesotho",
        "shortcodes": [
            ":flag_ls:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇹",
        "name": "flag: Lithuania",
        "shortcodes": [
            ":flag_lt:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇺",
        "name": "flag: Luxembourg",
        "shortcodes": [
            ":flag_lu:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇻",
        "name": "flag: Latvia",
        "shortcodes": [
            ":flag_lv:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇱🇾",
        "name": "flag: Libya",
        "shortcodes": [
            ":flag_ly:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇦",
        "name": "flag: Morocco",
        "shortcodes": [
            ":flag_ma:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇨",
        "name": "flag: Monaco",
        "shortcodes": [
            ":flag_mc:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇩",
        "name": "flag: Moldova",
        "shortcodes": [
            ":flag_md:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇪",
        "name": "flag: Montenegro",
        "shortcodes": [
            ":flag_me:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇫",
        "name": "flag: St. Martin",
        "shortcodes": [
            ":flag_mf:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇬",
        "name": "flag: Madagascar",
        "shortcodes": [
            ":flag_mg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇭",
        "name": "flag: Marshall Islands",
        "shortcodes": [
            ":flag_mh:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇰",
        "name": "flag: North Macedonia",
        "shortcodes": [
            ":flag_mk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇱",
        "name": "flag: Mali",
        "shortcodes": [
            ":flag_ml:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇲",
        "name": "flag: Myanmar (Burma)",
        "shortcodes": [
            ":flag_mm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇳",
        "name": "flag: Mongolia",
        "shortcodes": [
            ":flag_mn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇴",
        "name": "flag: Macao SAR China",
        "shortcodes": [
            ":flag_mo:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇵",
        "name": "flag: Northern Mariana Islands",
        "shortcodes": [
            ":flag_mp:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇶",
        "name": "flag: Martinique",
        "shortcodes": [
            ":flag_mq:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇷",
        "name": "flag: Mauritania",
        "shortcodes": [
            ":flag_mr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇸",
        "name": "flag: Montserrat",
        "shortcodes": [
            ":flag_ms:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇹",
        "name": "flag: Malta",
        "shortcodes": [
            ":flag_mt:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇺",
        "name": "flag: Mauritius",
        "shortcodes": [
            ":flag_mu:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇻",
        "name": "flag: Maldives",
        "shortcodes": [
            ":flag_mv:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇼",
        "name": "flag: Malawi",
        "shortcodes": [
            ":flag_mw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇽",
        "name": "flag: Mexico",
        "shortcodes": [
            ":flag_mx:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇾",
        "name": "flag: Malaysia",
        "shortcodes": [
            ":flag_my:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇲🇿",
        "name": "flag: Mozambique",
        "shortcodes": [
            ":flag_mz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇦",
        "name": "flag: Namibia",
        "shortcodes": [
            ":flag_na:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇨",
        "name": "flag: New Caledonia",
        "shortcodes": [
            ":flag_nc:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇪",
        "name": "flag: Niger",
        "shortcodes": [
            ":flag_ne:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇫",
        "name": "flag: Norfolk Island",
        "shortcodes": [
            ":flag_nf:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇬",
        "name": "flag: Nigeria",
        "shortcodes": [
            ":flag_ng:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇮",
        "name": "flag: Nicaragua",
        "shortcodes": [
            ":flag_ni:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇱",
        "name": "flag: Netherlands",
        "shortcodes": [
            ":flag_nl:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇴",
        "name": "flag: Norway",
        "shortcodes": [
            ":flag_no:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇵",
        "name": "flag: Nepal",
        "shortcodes": [
            ":flag_np:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇷",
        "name": "flag: Nauru",
        "shortcodes": [
            ":flag_nr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇺",
        "name": "flag: Niue",
        "shortcodes": [
            ":flag_nu:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇳🇿",
        "name": "flag: New Zealand",
        "shortcodes": [
            ":flag_nz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇴🇲",
        "name": "flag: Oman",
        "shortcodes": [
            ":flag_om:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇦",
        "name": "flag: Panama",
        "shortcodes": [
            ":flag_pa:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇪",
        "name": "flag: Peru",
        "shortcodes": [
            ":flag_pe:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇫",
        "name": "flag: French Polynesia",
        "shortcodes": [
            ":flag_pf:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇬",
        "name": "flag: Papua New Guinea",
        "shortcodes": [
            ":flag_pg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇭",
        "name": "flag: Philippines",
        "shortcodes": [
            ":flag_ph:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇰",
        "name": "flag: Pakistan",
        "shortcodes": [
            ":flag_pk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇱",
        "name": "flag: Poland",
        "shortcodes": [
            ":flag_pl:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇲",
        "name": "flag: St. Pierre & Miquelon",
        "shortcodes": [
            ":flag_pm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇳",
        "name": "flag: Pitcairn Islands",
        "shortcodes": [
            ":flag_pn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇷",
        "name": "flag: Puerto Rico",
        "shortcodes": [
            ":flag_pr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇸",
        "name": "flag: Palestinian Territories",
        "shortcodes": [
            ":flag_ps:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇹",
        "name": "flag: Portugal",
        "shortcodes": [
            ":flag_pt:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇼",
        "name": "flag: Palau",
        "shortcodes": [
            ":flag_pw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇵🇾",
        "name": "flag: Paraguay",
        "shortcodes": [
            ":flag_py:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇶🇦",
        "name": "flag: Qatar",
        "shortcodes": [
            ":flag_qa:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇷🇪",
        "name": "flag: Réunion",
        "shortcodes": [
            ":flag_re:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇷🇴",
        "name": "flag: Romania",
        "shortcodes": [
            ":flag_ro:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇷🇸",
        "name": "flag: Serbia",
        "shortcodes": [
            ":flag_rs:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇷🇺",
        "name": "flag: Russia",
        "shortcodes": [
            ":flag_ru:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇷🇼",
        "name": "flag: Rwanda",
        "shortcodes": [
            ":flag_rw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇦",
        "name": "flag: Saudi Arabia",
        "shortcodes": [
            ":flag_sa:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇧",
        "name": "flag: Solomon Islands",
        "shortcodes": [
            ":flag_sb:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇨",
        "name": "flag: Seychelles",
        "shortcodes": [
            ":flag_sc:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇩",
        "name": "flag: Sudan",
        "shortcodes": [
            ":flag_sd:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇪",
        "name": "flag: Sweden",
        "shortcodes": [
            ":flag_se:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇬",
        "name": "flag: Singapore",
        "shortcodes": [
            ":flag_sg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇭",
        "name": "flag: St. Helena",
        "shortcodes": [
            ":flag_sh:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇮",
        "name": "flag: Slovenia",
        "shortcodes": [
            ":flag_si:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇯",
        "name": "flag: Svalbard & Jan Mayen",
        "shortcodes": [
            ":flag_sj:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇰",
        "name": "flag: Slovakia",
        "shortcodes": [
            ":flag_sk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇱",
        "name": "flag: Sierra Leone",
        "shortcodes": [
            ":flag_sl:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇲",
        "name": "flag: San Marino",
        "shortcodes": [
            ":flag_sm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇳",
        "name": "flag: Senegal",
        "shortcodes": [
            ":flag_sn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇴",
        "name": "flag: Somalia",
        "shortcodes": [
            ":flag_so:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇷",
        "name": "flag: Suriname",
        "shortcodes": [
            ":flag_sr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇸",
        "name": "flag: South Sudan",
        "shortcodes": [
            ":flag_ss:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇹",
        "name": "flag: São Tomé & Príncipe",
        "shortcodes": [
            ":flag_st:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇻",
        "name": "flag: El Salvador",
        "shortcodes": [
            ":flag_sv:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇽",
        "name": "flag: Sint Maarten",
        "shortcodes": [
            ":flag_sx:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇾",
        "name": "flag: Syria",
        "shortcodes": [
            ":flag_sy:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇸🇿",
        "name": "flag: Eswatini",
        "shortcodes": [
            ":flag_sz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇦",
        "name": "flag: Tristan da Cunha",
        "shortcodes": [
            ":flag_ta:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇨",
        "name": "flag: Turks & Caicos Islands",
        "shortcodes": [
            ":flag_tc:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇩",
        "name": "flag: Chad",
        "shortcodes": [
            ":flag_td:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇫",
        "name": "flag: French Southern Territories",
        "shortcodes": [
            ":flag_tf:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇬",
        "name": "flag: Togo",
        "shortcodes": [
            ":flag_tg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇭",
        "name": "flag: Thailand",
        "shortcodes": [
            ":flag_th:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇯",
        "name": "flag: Tajikistan",
        "shortcodes": [
            ":flag_tj:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇰",
        "name": "flag: Tokelau",
        "shortcodes": [
            ":flag_tk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇱",
        "name": "flag: Timor-Leste",
        "shortcodes": [
            ":flag_tl:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇲",
        "name": "flag: Turkmenistan",
        "shortcodes": [
            ":flag_tm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇳",
        "name": "flag: Tunisia",
        "shortcodes": [
            ":flag_tn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇴",
        "name": "flag: Tonga",
        "shortcodes": [
            ":flag_to:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇷",
        "name": "flag: Turkey",
        "shortcodes": [
            ":flag_tr:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇹",
        "name": "flag: Trinidad & Tobago",
        "shortcodes": [
            ":flag_tt:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇻",
        "name": "flag: Tuvalu",
        "shortcodes": [
            ":flag_tv:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇼",
        "name": "flag: Taiwan",
        "shortcodes": [
            ":flag_tw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇹🇿",
        "name": "flag: Tanzania",
        "shortcodes": [
            ":flag_tz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇺🇦",
        "name": "flag: Ukraine",
        "shortcodes": [
            ":flag_ua:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇺🇬",
        "name": "flag: Uganda",
        "shortcodes": [
            ":flag_ug:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇺🇲",
        "name": "flag: U.S. Outlying Islands",
        "shortcodes": [
            ":flag_um:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇺🇳",
        "name": "flag: United Nations",
        "shortcodes": [
            ":flag_un:",
            ":united_nations:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇺🇸",
        "name": "flag: United States",
        "shortcodes": [
            ":flag_us:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇺🇾",
        "name": "flag: Uruguay",
        "shortcodes": [
            ":flag_uy:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇺🇿",
        "name": "flag: Uzbekistan",
        "shortcodes": [
            ":flag_uz:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇻🇦",
        "name": "flag: Vatican City",
        "shortcodes": [
            ":flag_va:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇻🇨",
        "name": "flag: St. Vincent & Grenadines",
        "shortcodes": [
            ":flag_vc:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇻🇪",
        "name": "flag: Venezuela",
        "shortcodes": [
            ":flag_ve:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇻🇬",
        "name": "flag: British Virgin Islands",
        "shortcodes": [
            ":flag_vg:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇻🇮",
        "name": "flag: U.S. Virgin Islands",
        "shortcodes": [
            ":flag_vi:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇻🇳",
        "name": "flag: Vietnam",
        "shortcodes": [
            ":flag_vn:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇻🇺",
        "name": "flag: Vanuatu",
        "shortcodes": [
            ":flag_vu:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇼🇫",
        "name": "flag: Wallis & Futuna",
        "shortcodes": [
            ":flag_wf:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇼🇸",
        "name": "flag: Samoa",
        "shortcodes": [
            ":flag_ws:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇽🇰",
        "name": "flag: Kosovo",
        "shortcodes": [
            ":flag_xk:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇾🇪",
        "name": "flag: Yemen",
        "shortcodes": [
            ":flag_ye:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇾🇹",
        "name": "flag: Mayotte",
        "shortcodes": [
            ":flag_yt:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇿🇦",
        "name": "flag: South Africa",
        "shortcodes": [
            ":flag_za:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇿🇲",
        "name": "flag: Zambia",
        "shortcodes": [
            ":flag_zm:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🇿🇼",
        "name": "flag: Zimbabwe",
        "shortcodes": [
            ":flag_zw:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "name": "flag: England",
        "shortcodes": [
            ":england:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        "name": "flag: Scotland",
        "shortcodes": [
            ":scotland:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    },
    {
        "codepoints": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
        "name": "flag: Wales",
        "shortcodes": [
            ":wales:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [
            "flag"
        ]
    }
]`);
