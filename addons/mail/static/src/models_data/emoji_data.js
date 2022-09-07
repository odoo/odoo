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
    }
]`);

export const emojisData = JSON.parse(`[
    {
        "category": "Smileys & Emotion",
        "codepoints": "😀",
        "emoticons": [],
        "keywords": [
            "face",
            "grin",
            "grinning face"
        ],
        "name": "grinning face",
        "shortcodes": [
            ":grinning:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😃",
        "emoticons": [],
        "keywords": [
            "face",
            "grinning face with big eyes",
            "mouth",
            "open",
            "smile"
        ],
        "name": "grinning face with big eyes",
        "shortcodes": [
            ":smiley:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😄",
        "emoticons": [],
        "keywords": [
            "eye",
            "face",
            "grinning face with smiling eyes",
            "mouth",
            "open",
            "smile"
        ],
        "name": "grinning face with smiling eyes",
        "shortcodes": [
            ":smile:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😁",
        "emoticons": [],
        "keywords": [
            "beaming face with smiling eyes",
            "eye",
            "face",
            "grin",
            "smile"
        ],
        "name": "beaming face with smiling eyes",
        "shortcodes": [
            ":grin:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😆",
        "emoticons": [],
        "keywords": [
            "face",
            "grinning squinting face",
            "laugh",
            "mouth",
            "satisfied",
            "smile"
        ],
        "name": "grinning squinting face",
        "shortcodes": [
            ":laughing:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😅",
        "emoticons": [],
        "keywords": [
            "cold",
            "face",
            "grinning face with sweat",
            "open",
            "smile",
            "sweat"
        ],
        "name": "grinning face with sweat",
        "shortcodes": [
            ":sweat_smile:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤣",
        "emoticons": [],
        "keywords": [
            "face",
            "floor",
            "laugh",
            "rofl",
            "rolling",
            "rolling on the floor laughing",
            "rotfl"
        ],
        "name": "rolling on the floor laughing",
        "shortcodes": [
            ":rofl:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😂",
        "emoticons": [],
        "keywords": [
            "face",
            "face with tears of joy",
            "joy",
            "laugh",
            "tear"
        ],
        "name": "face with tears of joy",
        "shortcodes": [
            ":joy:",
            ":jpp:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🙂",
        "emoticons": [],
        "keywords": [
            "face",
            "slightly smiling face",
            "smile"
        ],
        "name": "slightly smiling face",
        "shortcodes": [
            ":slight_smile:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🙃",
        "emoticons": [],
        "keywords": [
            "face",
            "upside-down",
            "upside down",
            "upside-down face"
        ],
        "name": "upside-down face",
        "shortcodes": [
            ":upside_down:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😉",
        "emoticons": [],
        "keywords": [
            "face",
            "wink",
            "winking face"
        ],
        "name": "winking face",
        "shortcodes": [
            ":wink:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😊",
        "emoticons": [],
        "keywords": [
            "blush",
            "eye",
            "face",
            "smile",
            "smiling face with smiling eyes"
        ],
        "name": "smiling face with smiling eyes",
        "shortcodes": [
            ":smiling_face_with_smiling_eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😇",
        "emoticons": [],
        "keywords": [
            "angel",
            "face",
            "fantasy",
            "halo",
            "innocent",
            "smiling face with halo"
        ],
        "name": "smiling face with halo",
        "shortcodes": [
            ":innocent:",
            ":halo:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🥰",
        "emoticons": [],
        "keywords": [
            "adore",
            "crush",
            "hearts",
            "in love",
            "smiling face with hearts"
        ],
        "name": "smiling face with hearts",
        "shortcodes": [
            ":smiling_face_with_hearts:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😍",
        "emoticons": [],
        "keywords": [
            "eye",
            "face",
            "love",
            "smile",
            "smiling face with heart-eyes",
            "smiling face with heart eyes"
        ],
        "name": "smiling face with heart-eyes",
        "shortcodes": [
            ":heart_eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤩",
        "emoticons": [],
        "keywords": [
            "eyes",
            "face",
            "grinning",
            "star",
            "star-struck"
        ],
        "name": "star-struck",
        "shortcodes": [
            ":star_struck:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😘",
        "emoticons": [],
        "keywords": [
            "face",
            "face blowing a kiss",
            "kiss"
        ],
        "name": "face blowing a kiss",
        "shortcodes": [
            ":kissing_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😗",
        "emoticons": [],
        "keywords": [
            "face",
            "kiss",
            "kissing face"
        ],
        "name": "kissing face",
        "shortcodes": [
            ":kissing:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😚",
        "emoticons": [],
        "keywords": [
            "closed",
            "eye",
            "face",
            "kiss",
            "kissing face with closed eyes"
        ],
        "name": "kissing face with closed eyes",
        "shortcodes": [
            ":kissing_closed_eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😙",
        "emoticons": [],
        "keywords": [
            "eye",
            "face",
            "kiss",
            "kissing face with smiling eyes",
            "smile"
        ],
        "name": "kissing face with smiling eyes",
        "shortcodes": [
            ":kissing_smiling_eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😋",
        "emoticons": [],
        "keywords": [
            "delicious",
            "face",
            "face savoring food",
            "savouring",
            "smile",
            "yum",
            "face savouring food",
            "savoring"
        ],
        "name": "face savoring food",
        "shortcodes": [
            ":yum:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😛",
        "emoticons": [
            ":P"
        ],
        "keywords": [
            "face",
            "face with tongue",
            "tongue"
        ],
        "name": "face with tongue",
        "shortcodes": [
            ":stuck_out_tongue:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😜",
        "emoticons": [],
        "keywords": [
            "eye",
            "face",
            "joke",
            "tongue",
            "wink",
            "winking face with tongue"
        ],
        "name": "winking face with tongue",
        "shortcodes": [
            ":stuck_out_tongue_winking_eye:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤪",
        "emoticons": [],
        "keywords": [
            "eye",
            "goofy",
            "large",
            "small",
            "zany face"
        ],
        "name": "zany face",
        "shortcodes": [
            ":zany:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😝",
        "emoticons": [],
        "keywords": [
            "eye",
            "face",
            "horrible",
            "squinting face with tongue",
            "taste",
            "tongue"
        ],
        "name": "squinting face with tongue",
        "shortcodes": [
            ":stuck_out_tongue_closed_eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤑",
        "emoticons": [],
        "keywords": [
            "face",
            "money",
            "money-mouth face",
            "mouth"
        ],
        "name": "money-mouth face",
        "shortcodes": [
            ":money_mouth:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤗",
        "emoticons": [],
        "keywords": [
            "face",
            "hug",
            "hugging",
            "open hands",
            "smiling face",
            "smiling face with open hands"
        ],
        "name": "smiling face with open hands",
        "shortcodes": [
            ":hugging_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤭",
        "emoticons": [],
        "keywords": [
            "face with hand over mouth",
            "whoops",
            "oops",
            "embarrassed"
        ],
        "name": "face with hand over mouth",
        "shortcodes": [
            ":hand_over_mouth:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤫",
        "emoticons": [],
        "keywords": [
            "quiet",
            "shooshing face",
            "shush",
            "shushing face"
        ],
        "name": "shushing face",
        "shortcodes": [
            ":shush:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤔",
        "emoticons": [],
        "keywords": [
            "face",
            "thinking"
        ],
        "name": "thinking face",
        "shortcodes": [
            ":thinking:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤐",
        "emoticons": [],
        "keywords": [
            "face",
            "mouth",
            "zipper",
            "zipper-mouth face"
        ],
        "name": "zipper-mouth face",
        "shortcodes": [
            ":zipper_mouth:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤨",
        "emoticons": [],
        "keywords": [
            "distrust",
            "face with raised eyebrow",
            "skeptic"
        ],
        "name": "face with raised eyebrow",
        "shortcodes": [
            ":raised_eyebrow:",
            ":skeptic:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😐",
        "emoticons": [
            ":|",
            ":-|"
        ],
        "keywords": [
            "deadpan",
            "face",
            "meh",
            "neutral"
        ],
        "name": "neutral face",
        "shortcodes": [
            ":neutral:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😑",
        "emoticons": [],
        "keywords": [
            "expressionless",
            "face",
            "inexpressive",
            "meh",
            "unexpressive"
        ],
        "name": "expressionless face",
        "shortcodes": [
            ":expressionless:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😶",
        "emoticons": [],
        "keywords": [
            "face",
            "face without mouth",
            "mouth",
            "quiet",
            "silent"
        ],
        "name": "face without mouth",
        "shortcodes": [
            ":no_mouth:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😏",
        "emoticons": [],
        "keywords": [
            "face",
            "smirk",
            "smirking face"
        ],
        "name": "smirking face",
        "shortcodes": [
            ":smirk:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😒",
        "emoticons": [],
        "keywords": [
            "face",
            "unamused",
            "unhappy"
        ],
        "name": "unamused face",
        "shortcodes": [
            ":unamused_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🙄",
        "emoticons": [],
        "keywords": [
            "eyeroll",
            "eyes",
            "face",
            "face with rolling eyes",
            "rolling"
        ],
        "name": "face with rolling eyes",
        "shortcodes": [
            ":face_with_rolling_eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😬",
        "emoticons": [],
        "keywords": [
            "face",
            "grimace",
            "grimacing face"
        ],
        "name": "grimacing face",
        "shortcodes": [
            ":grimacing_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤥",
        "emoticons": [],
        "keywords": [
            "face",
            "lie",
            "lying face",
            "pinocchio"
        ],
        "name": "lying face",
        "shortcodes": [
            ":lying_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😌",
        "emoticons": [],
        "keywords": [
            "face",
            "relieved"
        ],
        "name": "relieved face",
        "shortcodes": [
            ":relieved_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😔",
        "emoticons": [],
        "keywords": [
            "dejected",
            "face",
            "pensive"
        ],
        "name": "pensive face",
        "shortcodes": [
            ":pensive_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😪",
        "emoticons": [],
        "keywords": [
            "face",
            "good night",
            "sleep",
            "sleepy face"
        ],
        "name": "sleepy face",
        "shortcodes": [
            ":sleepy_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤤",
        "emoticons": [],
        "keywords": [
            "drooling",
            "face"
        ],
        "name": "drooling face",
        "shortcodes": [
            ":drooling_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😴",
        "emoticons": [],
        "keywords": [
            "face",
            "good night",
            "sleep",
            "sleeping face",
            "ZZZ"
        ],
        "name": "sleeping face",
        "shortcodes": [
            ":sleeping_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😷",
        "emoticons": [],
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
        ],
        "name": "face with medical mask",
        "shortcodes": [
            ":face_with_medical_mask:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤒",
        "emoticons": [],
        "keywords": [
            "face",
            "face with thermometer",
            "ill",
            "sick",
            "thermometer"
        ],
        "name": "face with thermometer",
        "shortcodes": [
            ":face_with_thermometer:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤕",
        "emoticons": [],
        "keywords": [
            "bandage",
            "face",
            "face with head-bandage",
            "hurt",
            "injury",
            "face with head bandage"
        ],
        "name": "face with head-bandage",
        "shortcodes": [
            ":face_with_head-bandage:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤢",
        "emoticons": [],
        "keywords": [
            "face",
            "nauseated",
            "vomit"
        ],
        "name": "nauseated face",
        "shortcodes": [
            ":nauseated_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤮",
        "emoticons": [],
        "keywords": [
            "face vomiting",
            "puke",
            "sick",
            "vomit"
        ],
        "name": "face vomiting",
        "shortcodes": [
            ":face_vomiting:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤧",
        "emoticons": [],
        "keywords": [
            "face",
            "gesundheit",
            "sneeze",
            "sneezing face",
            "bless you"
        ],
        "name": "sneezing face",
        "shortcodes": [
            ":sneezing_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🥵",
        "emoticons": [],
        "keywords": [
            "feverish",
            "flushed",
            "heat stroke",
            "hot",
            "hot face",
            "red-faced",
            "sweating"
        ],
        "name": "hot face",
        "shortcodes": [
            ":hot_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🥶",
        "emoticons": [],
        "keywords": [
            "blue-faced",
            "cold",
            "cold face",
            "freezing",
            "frostbite",
            "icicles"
        ],
        "name": "cold face",
        "shortcodes": [
            ":cold_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🥴",
        "emoticons": [],
        "keywords": [
            "dizzy",
            "intoxicated",
            "tipsy",
            "uneven eyes",
            "wavy mouth",
            "woozy face"
        ],
        "name": "woozy face",
        "shortcodes": [
            ":woozy_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😵",
        "emoticons": [],
        "keywords": [
            "crossed-out eyes",
            "dead",
            "face",
            "face with crossed-out eyes",
            "knocked out"
        ],
        "name": "face with crossed-out eyes",
        "shortcodes": [
            ":face_with_crossed-out_eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤯",
        "emoticons": [],
        "keywords": [
            "exploding head",
            "mind blown",
            "shocked"
        ],
        "name": "exploding head",
        "shortcodes": [
            ":exploding_head:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤠",
        "emoticons": [],
        "keywords": [
            "cowboy",
            "cowgirl",
            "face",
            "hat"
        ],
        "name": "cowboy hat face",
        "shortcodes": [
            ":cowboy_hat_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🥳",
        "emoticons": [],
        "keywords": [
            "celebration",
            "hat",
            "horn",
            "party",
            "partying face"
        ],
        "name": "partying face",
        "shortcodes": [
            ":partying_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😎",
        "emoticons": [],
        "keywords": [
            "bright",
            "cool",
            "face",
            "smiling face with sunglasses",
            "sun",
            "sunglasses"
        ],
        "name": "smiling face with sunglasses",
        "shortcodes": [
            ":smiling_face_with_sunglasses:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤓",
        "emoticons": [],
        "keywords": [
            "face",
            "geek",
            "nerd"
        ],
        "name": "nerd face",
        "shortcodes": [
            ":nerd_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🧐",
        "emoticons": [],
        "keywords": [
            "face",
            "face with monocle",
            "monocle",
            "stuffy"
        ],
        "name": "face with monocle",
        "shortcodes": [
            ":face_with_monocle:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😕",
        "emoticons": [],
        "keywords": [
            "confused",
            "face",
            "meh"
        ],
        "name": "confused face",
        "shortcodes": [
            ":confused_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😟",
        "emoticons": [],
        "keywords": [
            "face",
            "worried"
        ],
        "name": "worried face",
        "shortcodes": [
            ":worried_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🙁",
        "emoticons": [],
        "keywords": [
            "face",
            "frown",
            "slightly frowning face"
        ],
        "name": "slightly frowning face",
        "shortcodes": [
            ":slightly_frowning_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😮",
        "emoticons": [],
        "keywords": [
            "face",
            "face with open mouth",
            "mouth",
            "open",
            "sympathy"
        ],
        "name": "face with open mouth",
        "shortcodes": [
            ":face_with_open_mouth:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😯",
        "emoticons": [],
        "keywords": [
            "face",
            "hushed",
            "stunned",
            "surprised"
        ],
        "name": "hushed face",
        "shortcodes": [
            ":hushed_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😲",
        "emoticons": [],
        "keywords": [
            "astonished",
            "face",
            "shocked",
            "totally"
        ],
        "name": "astonished face",
        "shortcodes": [
            ":astonished_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😳",
        "emoticons": [],
        "keywords": [
            "dazed",
            "face",
            "flushed"
        ],
        "name": "flushed face",
        "shortcodes": [
            ":flushed_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🥺",
        "emoticons": [],
        "keywords": [
            "begging",
            "mercy",
            "pleading face",
            "puppy eyes"
        ],
        "name": "pleading face",
        "shortcodes": [
            ":pleading_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😦",
        "emoticons": [],
        "keywords": [
            "face",
            "frown",
            "frowning face with open mouth",
            "mouth",
            "open"
        ],
        "name": "frowning face with open mouth",
        "shortcodes": [
            ":frowning_face_with_open_mouth:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😧",
        "emoticons": [],
        "keywords": [
            "anguished",
            "face"
        ],
        "name": "anguished face",
        "shortcodes": [
            ":anguished_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😨",
        "emoticons": [],
        "keywords": [
            "face",
            "fear",
            "fearful",
            "scared"
        ],
        "name": "fearful face",
        "shortcodes": [
            ":fearful_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😰",
        "emoticons": [],
        "keywords": [
            "anxious face with sweat",
            "blue",
            "cold",
            "face",
            "rushed",
            "sweat"
        ],
        "name": "anxious face with sweat",
        "shortcodes": [
            ":anxious_face_with_sweat:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😥",
        "emoticons": [],
        "keywords": [
            "disappointed",
            "face",
            "relieved",
            "sad but relieved face",
            "whew"
        ],
        "name": "sad but relieved face",
        "shortcodes": [
            ":sad_but_relieved_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😢",
        "emoticons": [],
        "keywords": [
            "cry",
            "crying face",
            "face",
            "sad",
            "tear"
        ],
        "name": "crying face",
        "shortcodes": [
            ":crying_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😭",
        "emoticons": [],
        "keywords": [
            "cry",
            "face",
            "loudly crying face",
            "sad",
            "sob",
            "tear"
        ],
        "name": "loudly crying face",
        "shortcodes": [
            ":loudly_crying_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😱",
        "emoticons": [],
        "keywords": [
            "face",
            "face screaming in fear",
            "fear",
            "Munch",
            "scared",
            "scream",
            "munch"
        ],
        "name": "face screaming in fear",
        "shortcodes": [
            ":face_screaming_in_fear:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😖",
        "emoticons": [],
        "keywords": [
            "confounded",
            "face"
        ],
        "name": "confounded face",
        "shortcodes": [
            ":confounded_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😣",
        "emoticons": [],
        "keywords": [
            "face",
            "persevere",
            "persevering face"
        ],
        "name": "persevering face",
        "shortcodes": [
            ":persevering_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😞",
        "emoticons": [],
        "keywords": [
            "disappointed",
            "face"
        ],
        "name": "disappointed face",
        "shortcodes": [
            ":disappointed_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😓",
        "emoticons": [],
        "keywords": [
            "cold",
            "downcast face with sweat",
            "face",
            "sweat"
        ],
        "name": "downcast face with sweat",
        "shortcodes": [
            ":downcast_face_with_sweat:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😩",
        "emoticons": [],
        "keywords": [
            "face",
            "tired",
            "weary"
        ],
        "name": "weary face",
        "shortcodes": [
            ":weary_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😫",
        "emoticons": [],
        "keywords": [
            "face",
            "tired"
        ],
        "name": "tired face",
        "shortcodes": [
            ":tired_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🥱",
        "emoticons": [],
        "keywords": [
            "bored",
            "tired",
            "yawn",
            "yawning face"
        ],
        "name": "yawning face",
        "shortcodes": [
            ":yawning_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😤",
        "emoticons": [],
        "keywords": [
            "face",
            "face with steam from nose",
            "triumph",
            "won",
            "angry",
            "frustration"
        ],
        "name": "face with steam from nose",
        "shortcodes": [
            ":face_with_steam_from_nose:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😡",
        "emoticons": [],
        "keywords": [
            "angry",
            "enraged",
            "face",
            "mad",
            "pouting",
            "rage",
            "red"
        ],
        "name": "enraged face",
        "shortcodes": [
            ":enraged_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😠",
        "emoticons": [],
        "keywords": [
            "anger",
            "angry",
            "face",
            "mad"
        ],
        "name": "angry face",
        "shortcodes": [
            ":angry_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤬",
        "emoticons": [],
        "keywords": [
            "face with symbols on mouth",
            "swearing"
        ],
        "name": "face with symbols on mouth",
        "shortcodes": [
            ":face_with_symbols_on_mouth:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😈",
        "emoticons": [],
        "keywords": [
            "devil",
            "face",
            "fantasy",
            "horns",
            "smile",
            "smiling face with horns",
            "fairy tale"
        ],
        "name": "smiling face with horns",
        "shortcodes": [
            ":smiling_face_with_horns:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "👿",
        "emoticons": [],
        "keywords": [
            "angry face with horns",
            "demon",
            "devil",
            "face",
            "fantasy",
            "imp"
        ],
        "name": "angry face with horns",
        "shortcodes": [
            ":angry_face_with_horns:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💀",
        "emoticons": [],
        "keywords": [
            "death",
            "face",
            "fairy tale",
            "monster",
            "skull"
        ],
        "name": "skull",
        "shortcodes": [
            ":skull:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "☠️",
        "emoticons": [],
        "keywords": [
            "crossbones",
            "death",
            "face",
            "monster",
            "skull",
            "skull and crossbones"
        ],
        "name": "skull and crossbones",
        "shortcodes": [
            ":skull_and_crossbones:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💩",
        "emoticons": [],
        "keywords": [
            "dung",
            "face",
            "monster",
            "pile of poo",
            "poo",
            "poop"
        ],
        "name": "pile of poo",
        "shortcodes": [
            ":pile_of_poo:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤡",
        "emoticons": [],
        "keywords": [
            "clown",
            "face"
        ],
        "name": "clown face",
        "shortcodes": [
            ":clown_face:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "👹",
        "emoticons": [],
        "keywords": [
            "creature",
            "face",
            "fairy tale",
            "fantasy",
            "monster",
            "ogre"
        ],
        "name": "ogre",
        "shortcodes": [
            ":ogre:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "👺",
        "emoticons": [],
        "keywords": [
            "creature",
            "face",
            "fairy tale",
            "fantasy",
            "goblin",
            "monster"
        ],
        "name": "goblin",
        "shortcodes": [
            ":goblin:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "👻",
        "emoticons": [],
        "keywords": [
            "creature",
            "face",
            "fairy tale",
            "fantasy",
            "ghost",
            "monster"
        ],
        "name": "ghost",
        "shortcodes": [
            ":ghost:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "👽",
        "emoticons": [],
        "keywords": [
            "alien",
            "creature",
            "extraterrestrial",
            "face",
            "fantasy",
            "ufo"
        ],
        "name": "alien",
        "shortcodes": [
            ":alien:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "👾",
        "emoticons": [],
        "keywords": [
            "alien",
            "creature",
            "extraterrestrial",
            "face",
            "monster",
            "ufo"
        ],
        "name": "alien monster",
        "shortcodes": [
            ":alien_monster:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤖",
        "emoticons": [],
        "keywords": [
            "face",
            "monster",
            "robot"
        ],
        "name": "robot",
        "shortcodes": [
            ":robot:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😺",
        "emoticons": [],
        "keywords": [
            "cat",
            "face",
            "grinning",
            "mouth",
            "open",
            "smile"
        ],
        "name": "grinning cat",
        "shortcodes": [
            ":grinning_cat:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😸",
        "emoticons": [],
        "keywords": [
            "cat",
            "eye",
            "face",
            "grin",
            "grinning cat with smiling eyes",
            "smile"
        ],
        "name": "grinning cat with smiling eyes",
        "shortcodes": [
            ":grinning_cat_with_smiling_eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😹",
        "emoticons": [],
        "keywords": [
            "cat",
            "cat with tears of joy",
            "face",
            "joy",
            "tear"
        ],
        "name": "cat with tears of joy",
        "shortcodes": [
            ":cat_with_tears_of_joy:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😻",
        "emoticons": [],
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
        ],
        "name": "smiling cat with heart-eyes",
        "shortcodes": [
            ":smiling_cat_with_heart-eyes:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😼",
        "emoticons": [],
        "keywords": [
            "cat",
            "cat with wry smile",
            "face",
            "ironic",
            "smile",
            "wry"
        ],
        "name": "cat with wry smile",
        "shortcodes": [
            ":cat_with_wry_smile:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😽",
        "emoticons": [],
        "keywords": [
            "cat",
            "eye",
            "face",
            "kiss",
            "kissing cat"
        ],
        "name": "kissing cat",
        "shortcodes": [
            ":kissing_cat:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🙀",
        "emoticons": [],
        "keywords": [
            "cat",
            "face",
            "oh",
            "surprised",
            "weary"
        ],
        "name": "weary cat",
        "shortcodes": [
            ":weary_cat:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😿",
        "emoticons": [],
        "keywords": [
            "cat",
            "cry",
            "crying cat",
            "face",
            "sad",
            "tear"
        ],
        "name": "crying cat",
        "shortcodes": [
            ":crying_cat:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "😾",
        "emoticons": [],
        "keywords": [
            "cat",
            "face",
            "pouting"
        ],
        "name": "pouting cat",
        "shortcodes": [
            ":pouting_cat:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🙈",
        "emoticons": [],
        "keywords": [
            "evil",
            "face",
            "forbidden",
            "monkey",
            "see",
            "see-no-evil monkey"
        ],
        "name": "see-no-evil monkey",
        "shortcodes": [
            ":see-no-evil_monkey:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🙉",
        "emoticons": [],
        "keywords": [
            "evil",
            "face",
            "forbidden",
            "hear",
            "hear-no-evil monkey",
            "monkey"
        ],
        "name": "hear-no-evil monkey",
        "shortcodes": [
            ":hear-no-evil_monkey:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🙊",
        "emoticons": [],
        "keywords": [
            "evil",
            "face",
            "forbidden",
            "monkey",
            "speak",
            "speak-no-evil monkey"
        ],
        "name": "speak-no-evil monkey",
        "shortcodes": [
            ":speak-no-evil_monkey:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💋",
        "emoticons": [],
        "keywords": [
            "kiss",
            "kiss mark",
            "lips"
        ],
        "name": "kiss mark",
        "shortcodes": [
            ":kiss_mark:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💌",
        "emoticons": [],
        "keywords": [
            "heart",
            "letter",
            "love",
            "mail"
        ],
        "name": "love letter",
        "shortcodes": [
            ":love_letter:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💘",
        "emoticons": [],
        "keywords": [
            "arrow",
            "cupid",
            "heart with arrow"
        ],
        "name": "heart with arrow",
        "shortcodes": [
            ":heart_with_arrow:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💝",
        "emoticons": [],
        "keywords": [
            "heart with ribbon",
            "ribbon",
            "valentine"
        ],
        "name": "heart with ribbon",
        "shortcodes": [
            ":heart_with_ribbon:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💖",
        "emoticons": [],
        "keywords": [
            "excited",
            "sparkle",
            "sparkling heart"
        ],
        "name": "sparkling heart",
        "shortcodes": [
            ":sparkling_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💗",
        "emoticons": [],
        "keywords": [
            "excited",
            "growing",
            "growing heart",
            "nervous",
            "pulse"
        ],
        "name": "growing heart",
        "shortcodes": [
            ":growing_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💓",
        "emoticons": [],
        "keywords": [
            "beating",
            "beating heart",
            "heartbeat",
            "pulsating"
        ],
        "name": "beating heart",
        "shortcodes": [
            ":beating_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💞",
        "emoticons": [],
        "keywords": [
            "revolving",
            "revolving hearts"
        ],
        "name": "revolving hearts",
        "shortcodes": [
            ":revolving_hearts:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💕",
        "emoticons": [],
        "keywords": [
            "love",
            "two hearts"
        ],
        "name": "two hearts",
        "shortcodes": [
            ":two_hearts:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💟",
        "emoticons": [],
        "keywords": [
            "heart",
            "heart decoration"
        ],
        "name": "heart decoration",
        "shortcodes": [
            ":heart_decoration:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "❣️",
        "emoticons": [],
        "keywords": [
            "exclamation",
            "heart exclamation",
            "mark",
            "punctuation"
        ],
        "name": "heart exclamation",
        "shortcodes": [
            ":heart_exclamation:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💔",
        "emoticons": [],
        "keywords": [
            "break",
            "broken",
            "broken heart"
        ],
        "name": "broken heart",
        "shortcodes": [
            ":broken_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "❤️",
        "emoticons": [],
        "keywords": [
            "heart",
            "red heart"
        ],
        "name": "red heart",
        "shortcodes": [
            ":red_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🧡",
        "emoticons": [],
        "keywords": [
            "orange",
            "orange heart"
        ],
        "name": "orange heart",
        "shortcodes": [
            ":orange_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💛",
        "emoticons": [],
        "keywords": [
            "yellow",
            "yellow heart"
        ],
        "name": "yellow heart",
        "shortcodes": [
            ":yellow_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💚",
        "emoticons": [],
        "keywords": [
            "green",
            "green heart"
        ],
        "name": "green heart",
        "shortcodes": [
            ":green_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💙",
        "emoticons": [],
        "keywords": [
            "blue",
            "blue heart"
        ],
        "name": "blue heart",
        "shortcodes": [
            ":blue_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💜",
        "emoticons": [],
        "keywords": [
            "purple",
            "purple heart"
        ],
        "name": "purple heart",
        "shortcodes": [
            ":purple_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤎",
        "emoticons": [],
        "keywords": [
            "brown",
            "heart"
        ],
        "name": "brown heart",
        "shortcodes": [
            ":brown_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🖤",
        "emoticons": [],
        "keywords": [
            "black",
            "black heart",
            "evil",
            "wicked"
        ],
        "name": "black heart",
        "shortcodes": [
            ":black_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🤍",
        "emoticons": [],
        "keywords": [
            "heart",
            "white"
        ],
        "name": "white heart",
        "shortcodes": [
            ":white_heart:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💯",
        "emoticons": [],
        "keywords": [
            "100",
            "full",
            "hundred",
            "hundred points",
            "score"
        ],
        "name": "hundred points",
        "shortcodes": [
            ":hundred_points:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💢",
        "emoticons": [],
        "keywords": [
            "anger symbol",
            "angry",
            "comic",
            "mad"
        ],
        "name": "anger symbol",
        "shortcodes": [
            ":anger_symbol:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💥",
        "emoticons": [],
        "keywords": [
            "boom",
            "collision",
            "comic"
        ],
        "name": "collision",
        "shortcodes": [
            ":collision:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💫",
        "emoticons": [],
        "keywords": [
            "comic",
            "dizzy",
            "star"
        ],
        "name": "dizzy",
        "shortcodes": [
            ":dizzy:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💦",
        "emoticons": [],
        "keywords": [
            "comic",
            "splashing",
            "sweat",
            "sweat droplets"
        ],
        "name": "sweat droplets",
        "shortcodes": [
            ":sweat_droplets:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💨",
        "emoticons": [],
        "keywords": [
            "comic",
            "dash",
            "dashing away",
            "running"
        ],
        "name": "dashing away",
        "shortcodes": [
            ":dashing_away:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🕳️",
        "emoticons": [],
        "keywords": [
            "hole"
        ],
        "name": "hole",
        "shortcodes": [
            ":hole:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💣",
        "emoticons": [],
        "keywords": [
            "bomb",
            "comic"
        ],
        "name": "bomb",
        "shortcodes": [
            ":bomb:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💬",
        "emoticons": [],
        "keywords": [
            "balloon",
            "bubble",
            "comic",
            "dialog",
            "speech"
        ],
        "name": "speech balloon",
        "shortcodes": [
            ":speech_balloon:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "👁️‍🗨️",
        "emoticons": [],
        "keywords": [],
        "name": "eye in speech bubble",
        "shortcodes": [
            ":eye_in_speech_bubble:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🗨️",
        "emoticons": [],
        "keywords": [
            "balloon",
            "bubble",
            "dialog",
            "left speech bubble",
            "speech",
            "dialogue"
        ],
        "name": "left speech bubble",
        "shortcodes": [
            ":left_speech_bubble:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "🗯️",
        "emoticons": [],
        "keywords": [
            "angry",
            "balloon",
            "bubble",
            "mad",
            "right anger bubble"
        ],
        "name": "right anger bubble",
        "shortcodes": [
            ":right_anger_bubble:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💭",
        "emoticons": [],
        "keywords": [
            "balloon",
            "bubble",
            "comic",
            "thought"
        ],
        "name": "thought balloon",
        "shortcodes": [
            ":thought_balloon:"
        ]
    },
    {
        "category": "Smileys & Emotion",
        "codepoints": "💤",
        "emoticons": [],
        "keywords": [
            "comic",
            "good night",
            "sleep",
            "ZZZ"
        ],
        "name": "ZZZ",
        "shortcodes": [
            ":ZZZ:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👋",
        "emoticons": [],
        "keywords": [
            "hand",
            "wave",
            "waving"
        ],
        "name": "waving hand",
        "shortcodes": [
            ":waving_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤚",
        "emoticons": [],
        "keywords": [
            "backhand",
            "raised",
            "raised back of hand"
        ],
        "name": "raised back of hand",
        "shortcodes": [
            ":raised_back_of_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🖐️",
        "emoticons": [],
        "keywords": [
            "finger",
            "hand",
            "hand with fingers splayed",
            "splayed"
        ],
        "name": "hand with fingers splayed",
        "shortcodes": [
            ":hand_with_fingers_splayed:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "✋",
        "emoticons": [],
        "keywords": [
            "hand",
            "high 5",
            "high five",
            "raised hand"
        ],
        "name": "raised hand",
        "shortcodes": [
            ":raised_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🖖",
        "emoticons": [],
        "keywords": [
            "finger",
            "hand",
            "spock",
            "vulcan",
            "Vulcan salute",
            "vulcan salute"
        ],
        "name": "vulcan salute",
        "shortcodes": [
            ":vulcan_salute:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👌",
        "emoticons": [],
        "keywords": [
            "hand",
            "OK",
            "perfect"
        ],
        "name": "OK hand",
        "shortcodes": [
            ":OK_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤏",
        "emoticons": [],
        "keywords": [
            "pinching hand",
            "small amount"
        ],
        "name": "pinching hand",
        "shortcodes": [
            ":pinching_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "✌️",
        "emoticons": [],
        "keywords": [
            "hand",
            "v",
            "victory"
        ],
        "name": "victory hand",
        "shortcodes": [
            ":victory_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤞",
        "emoticons": [],
        "keywords": [
            "cross",
            "crossed fingers",
            "finger",
            "hand",
            "luck",
            "good luck"
        ],
        "name": "crossed fingers",
        "shortcodes": [
            ":crossed_fingers:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤟",
        "emoticons": [],
        "keywords": [
            "hand",
            "ILY",
            "love-you gesture",
            "love you gesture"
        ],
        "name": "love-you gesture",
        "shortcodes": [
            ":love-you_gesture:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤘",
        "emoticons": [],
        "keywords": [
            "finger",
            "hand",
            "horns",
            "rock-on",
            "sign of the horns",
            "rock on"
        ],
        "name": "sign of the horns",
        "shortcodes": [
            ":sign_of_the_horns:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤙",
        "emoticons": [],
        "keywords": [
            "call",
            "call me hand",
            "call-me hand",
            "hand",
            "shaka",
            "hang loose",
            "Shaka"
        ],
        "name": "call me hand",
        "shortcodes": [
            ":call_me_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👈",
        "emoticons": [],
        "keywords": [
            "backhand",
            "backhand index pointing left",
            "finger",
            "hand",
            "index",
            "point"
        ],
        "name": "backhand index pointing left",
        "shortcodes": [
            ":backhand_index_pointing_left:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👉",
        "emoticons": [],
        "keywords": [
            "backhand",
            "backhand index pointing right",
            "finger",
            "hand",
            "index",
            "point"
        ],
        "name": "backhand index pointing right",
        "shortcodes": [
            ":backhand_index_pointing_right:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👆",
        "emoticons": [],
        "keywords": [
            "backhand",
            "backhand index pointing up",
            "finger",
            "hand",
            "point",
            "up"
        ],
        "name": "backhand index pointing up",
        "shortcodes": [
            ":backhand_index_pointing_up:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🖕",
        "emoticons": [],
        "keywords": [
            "finger",
            "hand",
            "middle finger"
        ],
        "name": "middle finger",
        "shortcodes": [
            ":middle_finger:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👇",
        "emoticons": [],
        "keywords": [
            "backhand",
            "backhand index pointing down",
            "down",
            "finger",
            "hand",
            "point"
        ],
        "name": "backhand index pointing down",
        "shortcodes": [
            ":backhand_index_pointing_down:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "☝️",
        "emoticons": [],
        "keywords": [
            "finger",
            "hand",
            "index",
            "index pointing up",
            "point",
            "up"
        ],
        "name": "index pointing up",
        "shortcodes": [
            ":index_pointing_up:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👍",
        "emoticons": [],
        "keywords": [
            "+1",
            "hand",
            "thumb",
            "thumbs up",
            "up"
        ],
        "name": "thumbs up",
        "shortcodes": [
            ":thumbs_up:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👎",
        "emoticons": [],
        "keywords": [
            "-1",
            "down",
            "hand",
            "thumb",
            "thumbs down"
        ],
        "name": "thumbs down",
        "shortcodes": [
            ":thumbs_down:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "✊",
        "emoticons": [],
        "keywords": [
            "clenched",
            "fist",
            "hand",
            "punch",
            "raised fist"
        ],
        "name": "raised fist",
        "shortcodes": [
            ":raised_fist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👊",
        "emoticons": [],
        "keywords": [
            "clenched",
            "fist",
            "hand",
            "oncoming fist",
            "punch"
        ],
        "name": "oncoming fist",
        "shortcodes": [
            ":oncoming_fist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤛",
        "emoticons": [],
        "keywords": [
            "fist",
            "left-facing fist",
            "leftwards",
            "leftward"
        ],
        "name": "left-facing fist",
        "shortcodes": [
            ":left-facing_fist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤜",
        "emoticons": [],
        "keywords": [
            "fist",
            "right-facing fist",
            "rightwards",
            "rightward"
        ],
        "name": "right-facing fist",
        "shortcodes": [
            ":right-facing_fist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👏",
        "emoticons": [],
        "keywords": [
            "clap",
            "clapping hands",
            "hand"
        ],
        "name": "clapping hands",
        "shortcodes": [
            ":clapping_hands:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙌",
        "emoticons": [],
        "keywords": [
            "celebration",
            "gesture",
            "hand",
            "hooray",
            "raised",
            "raising hands",
            "woo hoo",
            "yay"
        ],
        "name": "raising hands",
        "shortcodes": [
            ":raising_hands:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👐",
        "emoticons": [],
        "keywords": [
            "hand",
            "open",
            "open hands"
        ],
        "name": "open hands",
        "shortcodes": [
            ":open_hands:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤲",
        "emoticons": [],
        "keywords": [
            "palms up together",
            "prayer"
        ],
        "name": "palms up together",
        "shortcodes": [
            ":palms_up_together:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤝",
        "emoticons": [],
        "keywords": [
            "agreement",
            "hand",
            "handshake",
            "meeting",
            "shake"
        ],
        "name": "handshake",
        "shortcodes": [
            ":handshake:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙏",
        "emoticons": [],
        "keywords": [
            "ask",
            "folded hands",
            "hand",
            "high 5",
            "high five",
            "please",
            "pray",
            "thanks"
        ],
        "name": "folded hands",
        "shortcodes": [
            ":folded_hands:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "✍️",
        "emoticons": [],
        "keywords": [
            "hand",
            "write",
            "writing hand"
        ],
        "name": "writing hand",
        "shortcodes": [
            ":writing_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💅",
        "emoticons": [],
        "keywords": [
            "care",
            "cosmetics",
            "manicure",
            "nail",
            "polish"
        ],
        "name": "nail polish",
        "shortcodes": [
            ":nail_polish:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤳",
        "emoticons": [],
        "keywords": [
            "camera",
            "phone",
            "selfie"
        ],
        "name": "selfie",
        "shortcodes": [
            ":selfie:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💪",
        "emoticons": [],
        "keywords": [
            "biceps",
            "comic",
            "flex",
            "flexed biceps",
            "muscle"
        ],
        "name": "flexed biceps",
        "shortcodes": [
            ":flexed_biceps:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦾",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "mechanical arm",
            "prosthetic"
        ],
        "name": "mechanical arm",
        "shortcodes": [
            ":mechanical_arm:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦿",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "mechanical leg",
            "prosthetic"
        ],
        "name": "mechanical leg",
        "shortcodes": [
            ":mechanical_leg:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦵",
        "emoticons": [],
        "keywords": [
            "kick",
            "leg",
            "limb"
        ],
        "name": "leg",
        "shortcodes": [
            ":leg:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦶",
        "emoticons": [],
        "keywords": [
            "foot",
            "kick",
            "stomp"
        ],
        "name": "foot",
        "shortcodes": [
            ":foot:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👂",
        "emoticons": [],
        "keywords": [
            "body",
            "ear"
        ],
        "name": "ear",
        "shortcodes": [
            ":ear:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦻",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "ear with hearing aid",
            "hard of hearing",
            "hearing impaired"
        ],
        "name": "ear with hearing aid",
        "shortcodes": [
            ":ear_with_hearing_aid:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👃",
        "emoticons": [],
        "keywords": [
            "body",
            "nose"
        ],
        "name": "nose",
        "shortcodes": [
            ":nose:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧠",
        "emoticons": [],
        "keywords": [
            "brain",
            "intelligent"
        ],
        "name": "brain",
        "shortcodes": [
            ":brain:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦷",
        "emoticons": [],
        "keywords": [
            "dentist",
            "tooth"
        ],
        "name": "tooth",
        "shortcodes": [
            ":tooth:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦴",
        "emoticons": [],
        "keywords": [
            "bone",
            "skeleton"
        ],
        "name": "bone",
        "shortcodes": [
            ":bone:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👀",
        "emoticons": [],
        "keywords": [
            "eye",
            "eyes",
            "face"
        ],
        "name": "eyes",
        "shortcodes": [
            ":eyes:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👁️",
        "emoticons": [],
        "keywords": [
            "body",
            "eye"
        ],
        "name": "eye",
        "shortcodes": [
            ":eye:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👅",
        "emoticons": [],
        "keywords": [
            "body",
            "tongue"
        ],
        "name": "tongue",
        "shortcodes": [
            ":tongue:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👄",
        "emoticons": [],
        "keywords": [
            "lips",
            "mouth"
        ],
        "name": "mouth",
        "shortcodes": [
            ":mouth:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👶",
        "emoticons": [],
        "keywords": [
            "baby",
            "young"
        ],
        "name": "baby",
        "shortcodes": [
            ":baby:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧒",
        "emoticons": [],
        "keywords": [
            "child",
            "gender-neutral",
            "unspecified gender",
            "young"
        ],
        "name": "child",
        "shortcodes": [
            ":child:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "young",
            "young person"
        ],
        "name": "boy",
        "shortcodes": [
            ":boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👧",
        "emoticons": [],
        "keywords": [
            "girl",
            "Virgo",
            "young person",
            "zodiac",
            "young"
        ],
        "name": "girl",
        "shortcodes": [
            ":girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑",
        "emoticons": [],
        "keywords": [
            "adult",
            "gender-neutral",
            "person",
            "unspecified gender"
        ],
        "name": "person",
        "shortcodes": [
            ":person:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👱",
        "emoticons": [],
        "keywords": [
            "blond",
            "blond-haired person",
            "hair",
            "person: blond hair"
        ],
        "name": "person: blond hair",
        "shortcodes": [
            ":person:_blond_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨",
        "emoticons": [],
        "keywords": [
            "adult",
            "man"
        ],
        "name": "man",
        "shortcodes": [
            ":man:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧔",
        "emoticons": [],
        "keywords": [
            "beard",
            "person",
            "person: beard"
        ],
        "name": "person: beard",
        "shortcodes": [
            ":person:_beard:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🦰",
        "emoticons": [],
        "keywords": [
            "adult",
            "man",
            "red hair"
        ],
        "name": "man: red hair",
        "shortcodes": [
            ":man:_red_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🦱",
        "emoticons": [],
        "keywords": [
            "adult",
            "curly hair",
            "man"
        ],
        "name": "man: curly hair",
        "shortcodes": [
            ":man:_curly_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🦳",
        "emoticons": [],
        "keywords": [
            "adult",
            "man",
            "white hair"
        ],
        "name": "man: white hair",
        "shortcodes": [
            ":man:_white_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🦲",
        "emoticons": [],
        "keywords": [
            "adult",
            "bald",
            "man"
        ],
        "name": "man: bald",
        "shortcodes": [
            ":man:_bald:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩",
        "emoticons": [],
        "keywords": [
            "adult",
            "woman"
        ],
        "name": "woman",
        "shortcodes": [
            ":woman:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🦰",
        "emoticons": [],
        "keywords": [
            "adult",
            "red hair",
            "woman"
        ],
        "name": "woman: red hair",
        "shortcodes": [
            ":woman:_red_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🦰",
        "emoticons": [],
        "keywords": [
            "adult",
            "gender-neutral",
            "person",
            "red hair",
            "unspecified gender"
        ],
        "name": "person: red hair",
        "shortcodes": [
            ":person:_red_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🦱",
        "emoticons": [],
        "keywords": [
            "adult",
            "curly hair",
            "woman"
        ],
        "name": "woman: curly hair",
        "shortcodes": [
            ":woman:_curly_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🦱",
        "emoticons": [],
        "keywords": [
            "adult",
            "curly hair",
            "gender-neutral",
            "person",
            "unspecified gender"
        ],
        "name": "person: curly hair",
        "shortcodes": [
            ":person:_curly_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🦳",
        "emoticons": [],
        "keywords": [
            "adult",
            "white hair",
            "woman"
        ],
        "name": "woman: white hair",
        "shortcodes": [
            ":woman:_white_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🦳",
        "emoticons": [],
        "keywords": [
            "adult",
            "gender-neutral",
            "person",
            "unspecified gender",
            "white hair"
        ],
        "name": "person: white hair",
        "shortcodes": [
            ":person:_white_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🦲",
        "emoticons": [],
        "keywords": [
            "adult",
            "bald",
            "woman"
        ],
        "name": "woman: bald",
        "shortcodes": [
            ":woman:_bald:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🦲",
        "emoticons": [],
        "keywords": [
            "adult",
            "bald",
            "gender-neutral",
            "person",
            "unspecified gender"
        ],
        "name": "person: bald",
        "shortcodes": [
            ":person:_bald:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👱‍♀️",
        "emoticons": [],
        "keywords": [
            "blond-haired woman",
            "blonde",
            "hair",
            "woman",
            "woman: blond hair"
        ],
        "name": "woman: blond hair",
        "shortcodes": [
            ":woman:_blond_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👱‍♂️",
        "emoticons": [],
        "keywords": [
            "blond",
            "blond-haired man",
            "hair",
            "man",
            "man: blond hair"
        ],
        "name": "man: blond hair",
        "shortcodes": [
            ":man:_blond_hair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧓",
        "emoticons": [],
        "keywords": [
            "adult",
            "gender-neutral",
            "old",
            "older person",
            "unspecified gender"
        ],
        "name": "older person",
        "shortcodes": [
            ":older_person:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👴",
        "emoticons": [],
        "keywords": [
            "adult",
            "man",
            "old"
        ],
        "name": "old man",
        "shortcodes": [
            ":old_man:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👵",
        "emoticons": [],
        "keywords": [
            "adult",
            "old",
            "woman"
        ],
        "name": "old woman",
        "shortcodes": [
            ":old_woman:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙍",
        "emoticons": [],
        "keywords": [
            "frown",
            "gesture",
            "person frowning"
        ],
        "name": "person frowning",
        "shortcodes": [
            ":person_frowning:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙍‍♂️",
        "emoticons": [],
        "keywords": [
            "frowning",
            "gesture",
            "man"
        ],
        "name": "man frowning",
        "shortcodes": [
            ":man_frowning:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙍‍♀️",
        "emoticons": [],
        "keywords": [
            "frowning",
            "gesture",
            "woman"
        ],
        "name": "woman frowning",
        "shortcodes": [
            ":woman_frowning:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙎",
        "emoticons": [],
        "keywords": [
            "gesture",
            "person pouting",
            "pouting"
        ],
        "name": "person pouting",
        "shortcodes": [
            ":person_pouting:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙎‍♂️",
        "emoticons": [],
        "keywords": [
            "gesture",
            "man",
            "pouting"
        ],
        "name": "man pouting",
        "shortcodes": [
            ":man_pouting:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙎‍♀️",
        "emoticons": [],
        "keywords": [
            "gesture",
            "pouting",
            "woman"
        ],
        "name": "woman pouting",
        "shortcodes": [
            ":woman_pouting:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙅",
        "emoticons": [],
        "keywords": [
            "forbidden",
            "gesture",
            "hand",
            "person gesturing NO",
            "prohibited"
        ],
        "name": "person gesturing NO",
        "shortcodes": [
            ":person_gesturing_NO:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙅‍♂️",
        "emoticons": [],
        "keywords": [
            "forbidden",
            "gesture",
            "hand",
            "man",
            "man gesturing NO",
            "prohibited"
        ],
        "name": "man gesturing NO",
        "shortcodes": [
            ":man_gesturing_NO:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙅‍♀️",
        "emoticons": [],
        "keywords": [
            "forbidden",
            "gesture",
            "hand",
            "prohibited",
            "woman",
            "woman gesturing NO"
        ],
        "name": "woman gesturing NO",
        "shortcodes": [
            ":woman_gesturing_NO:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙆",
        "emoticons": [],
        "keywords": [
            "gesture",
            "hand",
            "OK",
            "person gesturing OK"
        ],
        "name": "person gesturing OK",
        "shortcodes": [
            ":person_gesturing_OK:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙆‍♂️",
        "emoticons": [],
        "keywords": [
            "gesture",
            "hand",
            "man",
            "man gesturing OK",
            "OK"
        ],
        "name": "man gesturing OK",
        "shortcodes": [
            ":man_gesturing_OK:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙆‍♀️",
        "emoticons": [],
        "keywords": [
            "gesture",
            "hand",
            "OK",
            "woman",
            "woman gesturing OK"
        ],
        "name": "woman gesturing OK",
        "shortcodes": [
            ":woman_gesturing_OK:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💁",
        "emoticons": [],
        "keywords": [
            "hand",
            "help",
            "information",
            "person tipping hand",
            "sassy",
            "tipping"
        ],
        "name": "person tipping hand",
        "shortcodes": [
            ":person_tipping_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💁‍♂️",
        "emoticons": [],
        "keywords": [
            "man",
            "man tipping hand",
            "sassy",
            "tipping hand"
        ],
        "name": "man tipping hand",
        "shortcodes": [
            ":man_tipping_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💁‍♀️",
        "emoticons": [],
        "keywords": [
            "sassy",
            "tipping hand",
            "woman",
            "woman tipping hand"
        ],
        "name": "woman tipping hand",
        "shortcodes": [
            ":woman_tipping_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙋",
        "emoticons": [],
        "keywords": [
            "gesture",
            "hand",
            "happy",
            "person raising hand",
            "raised"
        ],
        "name": "person raising hand",
        "shortcodes": [
            ":person_raising_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙋‍♂️",
        "emoticons": [],
        "keywords": [
            "gesture",
            "man",
            "man raising hand",
            "raising hand"
        ],
        "name": "man raising hand",
        "shortcodes": [
            ":man_raising_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙋‍♀️",
        "emoticons": [],
        "keywords": [
            "gesture",
            "raising hand",
            "woman",
            "woman raising hand"
        ],
        "name": "woman raising hand",
        "shortcodes": [
            ":woman_raising_hand:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧏",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "deaf",
            "deaf person",
            "ear",
            "hear",
            "hearing impaired"
        ],
        "name": "deaf person",
        "shortcodes": [
            ":deaf_person:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧏‍♂️",
        "emoticons": [],
        "keywords": [
            "deaf",
            "man"
        ],
        "name": "deaf man",
        "shortcodes": [
            ":deaf_man:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧏‍♀️",
        "emoticons": [],
        "keywords": [
            "deaf",
            "woman"
        ],
        "name": "deaf woman",
        "shortcodes": [
            ":deaf_woman:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙇",
        "emoticons": [],
        "keywords": [
            "apology",
            "bow",
            "gesture",
            "person bowing",
            "sorry"
        ],
        "name": "person bowing",
        "shortcodes": [
            ":person_bowing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙇‍♂️",
        "emoticons": [],
        "keywords": [
            "apology",
            "bowing",
            "favor",
            "gesture",
            "man",
            "sorry"
        ],
        "name": "man bowing",
        "shortcodes": [
            ":man_bowing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🙇‍♀️",
        "emoticons": [],
        "keywords": [
            "apology",
            "bowing",
            "favor",
            "gesture",
            "sorry",
            "woman"
        ],
        "name": "woman bowing",
        "shortcodes": [
            ":woman_bowing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤦",
        "emoticons": [],
        "keywords": [
            "disbelief",
            "exasperation",
            "face",
            "palm",
            "person facepalming"
        ],
        "name": "person facepalming",
        "shortcodes": [
            ":person_facepalming:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤦‍♂️",
        "emoticons": [],
        "keywords": [
            "disbelief",
            "exasperation",
            "facepalm",
            "man",
            "man facepalming"
        ],
        "name": "man facepalming",
        "shortcodes": [
            ":man_facepalming:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤦‍♀️",
        "emoticons": [],
        "keywords": [
            "disbelief",
            "exasperation",
            "facepalm",
            "woman",
            "woman facepalming"
        ],
        "name": "woman facepalming",
        "shortcodes": [
            ":woman_facepalming:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤷",
        "emoticons": [],
        "keywords": [
            "doubt",
            "ignorance",
            "indifference",
            "person shrugging",
            "shrug"
        ],
        "name": "person shrugging",
        "shortcodes": [
            ":person_shrugging:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤷‍♂️",
        "emoticons": [],
        "keywords": [
            "doubt",
            "ignorance",
            "indifference",
            "man",
            "man shrugging",
            "shrug"
        ],
        "name": "man shrugging",
        "shortcodes": [
            ":man_shrugging:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤷‍♀️",
        "emoticons": [],
        "keywords": [
            "doubt",
            "ignorance",
            "indifference",
            "shrug",
            "woman",
            "woman shrugging"
        ],
        "name": "woman shrugging",
        "shortcodes": [
            ":woman_shrugging:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍⚕️",
        "emoticons": [],
        "keywords": [
            "doctor",
            "health worker",
            "healthcare",
            "nurse",
            "therapist",
            "care",
            "health"
        ],
        "name": "health worker",
        "shortcodes": [
            ":health_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍⚕️",
        "emoticons": [],
        "keywords": [
            "doctor",
            "healthcare",
            "man",
            "man health worker",
            "nurse",
            "therapist",
            "health care"
        ],
        "name": "man health worker",
        "shortcodes": [
            ":man_health_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍⚕️",
        "emoticons": [],
        "keywords": [
            "doctor",
            "healthcare",
            "nurse",
            "therapist",
            "woman",
            "woman health worker",
            "health care"
        ],
        "name": "woman health worker",
        "shortcodes": [
            ":woman_health_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🎓",
        "emoticons": [],
        "keywords": [
            "graduate",
            "student"
        ],
        "name": "student",
        "shortcodes": [
            ":student:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🎓",
        "emoticons": [],
        "keywords": [
            "graduate",
            "man",
            "student"
        ],
        "name": "man student",
        "shortcodes": [
            ":man_student:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🎓",
        "emoticons": [],
        "keywords": [
            "graduate",
            "student",
            "woman"
        ],
        "name": "woman student",
        "shortcodes": [
            ":woman_student:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🏫",
        "emoticons": [],
        "keywords": [
            "instructor",
            "professor",
            "teacher",
            "lecturer"
        ],
        "name": "teacher",
        "shortcodes": [
            ":teacher:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🏫",
        "emoticons": [],
        "keywords": [
            "instructor",
            "man",
            "professor",
            "teacher"
        ],
        "name": "man teacher",
        "shortcodes": [
            ":man_teacher:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🏫",
        "emoticons": [],
        "keywords": [
            "instructor",
            "professor",
            "teacher",
            "woman"
        ],
        "name": "woman teacher",
        "shortcodes": [
            ":woman_teacher:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍⚖️",
        "emoticons": [],
        "keywords": [
            "judge",
            "justice",
            "scales",
            "law"
        ],
        "name": "judge",
        "shortcodes": [
            ":judge:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍⚖️",
        "emoticons": [],
        "keywords": [
            "judge",
            "justice",
            "man",
            "scales"
        ],
        "name": "man judge",
        "shortcodes": [
            ":man_judge:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍⚖️",
        "emoticons": [],
        "keywords": [
            "judge",
            "justice",
            "scales",
            "woman"
        ],
        "name": "woman judge",
        "shortcodes": [
            ":woman_judge:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🌾",
        "emoticons": [],
        "keywords": [
            "farmer",
            "gardener",
            "rancher"
        ],
        "name": "farmer",
        "shortcodes": [
            ":farmer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🌾",
        "emoticons": [],
        "keywords": [
            "farmer",
            "gardener",
            "man",
            "rancher"
        ],
        "name": "man farmer",
        "shortcodes": [
            ":man_farmer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🌾",
        "emoticons": [],
        "keywords": [
            "farmer",
            "gardener",
            "rancher",
            "woman"
        ],
        "name": "woman farmer",
        "shortcodes": [
            ":woman_farmer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🍳",
        "emoticons": [],
        "keywords": [
            "chef",
            "cook"
        ],
        "name": "cook",
        "shortcodes": [
            ":cook:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🍳",
        "emoticons": [],
        "keywords": [
            "chef",
            "cook",
            "man"
        ],
        "name": "man cook",
        "shortcodes": [
            ":man_cook:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🍳",
        "emoticons": [],
        "keywords": [
            "chef",
            "cook",
            "woman"
        ],
        "name": "woman cook",
        "shortcodes": [
            ":woman_cook:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🔧",
        "emoticons": [],
        "keywords": [
            "electrician",
            "mechanic",
            "plumber",
            "tradesperson",
            "tradie"
        ],
        "name": "mechanic",
        "shortcodes": [
            ":mechanic:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🔧",
        "emoticons": [],
        "keywords": [
            "electrician",
            "man",
            "mechanic",
            "plumber",
            "tradesperson"
        ],
        "name": "man mechanic",
        "shortcodes": [
            ":man_mechanic:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🔧",
        "emoticons": [],
        "keywords": [
            "electrician",
            "mechanic",
            "plumber",
            "tradesperson",
            "woman"
        ],
        "name": "woman mechanic",
        "shortcodes": [
            ":woman_mechanic:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🏭",
        "emoticons": [],
        "keywords": [
            "assembly",
            "factory",
            "industrial",
            "worker"
        ],
        "name": "factory worker",
        "shortcodes": [
            ":factory_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🏭",
        "emoticons": [],
        "keywords": [
            "assembly",
            "factory",
            "industrial",
            "man",
            "worker"
        ],
        "name": "man factory worker",
        "shortcodes": [
            ":man_factory_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🏭",
        "emoticons": [],
        "keywords": [
            "assembly",
            "factory",
            "industrial",
            "woman",
            "worker"
        ],
        "name": "woman factory worker",
        "shortcodes": [
            ":woman_factory_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍💼",
        "emoticons": [],
        "keywords": [
            "architect",
            "business",
            "manager",
            "office worker",
            "white-collar"
        ],
        "name": "office worker",
        "shortcodes": [
            ":office_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍💼",
        "emoticons": [],
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
        ],
        "name": "man office worker",
        "shortcodes": [
            ":man_office_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍💼",
        "emoticons": [],
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
        ],
        "name": "woman office worker",
        "shortcodes": [
            ":woman_office_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🔬",
        "emoticons": [],
        "keywords": [
            "biologist",
            "chemist",
            "engineer",
            "physicist",
            "scientist"
        ],
        "name": "scientist",
        "shortcodes": [
            ":scientist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🔬",
        "emoticons": [],
        "keywords": [
            "biologist",
            "chemist",
            "engineer",
            "man",
            "physicist",
            "scientist"
        ],
        "name": "man scientist",
        "shortcodes": [
            ":man_scientist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🔬",
        "emoticons": [],
        "keywords": [
            "biologist",
            "chemist",
            "engineer",
            "physicist",
            "scientist",
            "woman"
        ],
        "name": "woman scientist",
        "shortcodes": [
            ":woman_scientist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍💻",
        "emoticons": [],
        "keywords": [
            "coder",
            "developer",
            "inventor",
            "software",
            "technologist"
        ],
        "name": "technologist",
        "shortcodes": [
            ":technologist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍💻",
        "emoticons": [],
        "keywords": [
            "coder",
            "developer",
            "inventor",
            "man",
            "software",
            "technologist"
        ],
        "name": "man technologist",
        "shortcodes": [
            ":man_technologist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍💻",
        "emoticons": [],
        "keywords": [
            "coder",
            "developer",
            "inventor",
            "software",
            "technologist",
            "woman"
        ],
        "name": "woman technologist",
        "shortcodes": [
            ":woman_technologist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🎤",
        "emoticons": [],
        "keywords": [
            "actor",
            "entertainer",
            "rock",
            "singer",
            "star"
        ],
        "name": "singer",
        "shortcodes": [
            ":singer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🎤",
        "emoticons": [],
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
        ],
        "name": "man singer",
        "shortcodes": [
            ":man_singer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🎤",
        "emoticons": [],
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
        ],
        "name": "woman singer",
        "shortcodes": [
            ":woman_singer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🎨",
        "emoticons": [],
        "keywords": [
            "artist",
            "palette"
        ],
        "name": "artist",
        "shortcodes": [
            ":artist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🎨",
        "emoticons": [],
        "keywords": [
            "artist",
            "man",
            "painter",
            "palette"
        ],
        "name": "man artist",
        "shortcodes": [
            ":man_artist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🎨",
        "emoticons": [],
        "keywords": [
            "artist",
            "painter",
            "palette",
            "woman"
        ],
        "name": "woman artist",
        "shortcodes": [
            ":woman_artist:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍✈️",
        "emoticons": [],
        "keywords": [
            "pilot",
            "plane"
        ],
        "name": "pilot",
        "shortcodes": [
            ":pilot:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍✈️",
        "emoticons": [],
        "keywords": [
            "man",
            "pilot",
            "plane"
        ],
        "name": "man pilot",
        "shortcodes": [
            ":man_pilot:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍✈️",
        "emoticons": [],
        "keywords": [
            "pilot",
            "plane",
            "woman"
        ],
        "name": "woman pilot",
        "shortcodes": [
            ":woman_pilot:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🚀",
        "emoticons": [],
        "keywords": [
            "astronaut",
            "rocket"
        ],
        "name": "astronaut",
        "shortcodes": [
            ":astronaut:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🚀",
        "emoticons": [],
        "keywords": [
            "astronaut",
            "man",
            "rocket"
        ],
        "name": "man astronaut",
        "shortcodes": [
            ":man_astronaut:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🚀",
        "emoticons": [],
        "keywords": [
            "astronaut",
            "rocket",
            "woman"
        ],
        "name": "woman astronaut",
        "shortcodes": [
            ":woman_astronaut:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🚒",
        "emoticons": [],
        "keywords": [
            "firefighter",
            "firetruck",
            "engine",
            "fire",
            "truck",
            "fire engine",
            "fire truck"
        ],
        "name": "firefighter",
        "shortcodes": [
            ":firefighter:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🚒",
        "emoticons": [],
        "keywords": [
            "fire truck",
            "firefighter",
            "man",
            "firetruck",
            "fireman"
        ],
        "name": "man firefighter",
        "shortcodes": [
            ":man_firefighter:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🚒",
        "emoticons": [],
        "keywords": [
            "fire truck",
            "firefighter",
            "woman",
            "firetruck",
            "engine",
            "fire",
            "firewoman",
            "truck"
        ],
        "name": "woman firefighter",
        "shortcodes": [
            ":woman_firefighter:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👮",
        "emoticons": [],
        "keywords": [
            "cop",
            "officer",
            "police"
        ],
        "name": "police officer",
        "shortcodes": [
            ":police_officer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👮‍♂️",
        "emoticons": [],
        "keywords": [
            "cop",
            "man",
            "officer",
            "police"
        ],
        "name": "man police officer",
        "shortcodes": [
            ":man_police_officer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👮‍♀️",
        "emoticons": [],
        "keywords": [
            "cop",
            "officer",
            "police",
            "woman"
        ],
        "name": "woman police officer",
        "shortcodes": [
            ":woman_police_officer:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🕵️",
        "emoticons": [],
        "keywords": [
            "detective",
            "investigator",
            "sleuth",
            "spy"
        ],
        "name": "detective",
        "shortcodes": [
            ":detective:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🕵️‍♂️",
        "emoticons": [],
        "keywords": [],
        "name": "man detective",
        "shortcodes": [
            ":man_detective:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🕵️‍♀️",
        "emoticons": [],
        "keywords": [],
        "name": "woman detective",
        "shortcodes": [
            ":woman_detective:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💂",
        "emoticons": [],
        "keywords": [
            "guard"
        ],
        "name": "guard",
        "shortcodes": [
            ":guard:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💂‍♂️",
        "emoticons": [],
        "keywords": [
            "guard",
            "man"
        ],
        "name": "man guard",
        "shortcodes": [
            ":man_guard:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💂‍♀️",
        "emoticons": [],
        "keywords": [
            "guard",
            "woman"
        ],
        "name": "woman guard",
        "shortcodes": [
            ":woman_guard:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👷",
        "emoticons": [],
        "keywords": [
            "construction",
            "hat",
            "worker"
        ],
        "name": "construction worker",
        "shortcodes": [
            ":construction_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👷‍♂️",
        "emoticons": [],
        "keywords": [
            "construction",
            "man",
            "worker"
        ],
        "name": "man construction worker",
        "shortcodes": [
            ":man_construction_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👷‍♀️",
        "emoticons": [],
        "keywords": [
            "construction",
            "woman",
            "worker"
        ],
        "name": "woman construction worker",
        "shortcodes": [
            ":woman_construction_worker:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤴",
        "emoticons": [],
        "keywords": [
            "prince"
        ],
        "name": "prince",
        "shortcodes": [
            ":prince:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👸",
        "emoticons": [],
        "keywords": [
            "fairy tale",
            "fantasy",
            "princess"
        ],
        "name": "princess",
        "shortcodes": [
            ":princess:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👳",
        "emoticons": [],
        "keywords": [
            "person wearing turban",
            "turban"
        ],
        "name": "person wearing turban",
        "shortcodes": [
            ":person_wearing_turban:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👳‍♂️",
        "emoticons": [],
        "keywords": [
            "man",
            "man wearing turban",
            "turban"
        ],
        "name": "man wearing turban",
        "shortcodes": [
            ":man_wearing_turban:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👳‍♀️",
        "emoticons": [],
        "keywords": [
            "turban",
            "woman",
            "woman wearing turban"
        ],
        "name": "woman wearing turban",
        "shortcodes": [
            ":woman_wearing_turban:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👲",
        "emoticons": [],
        "keywords": [
            "cap",
            "gua pi mao",
            "hat",
            "person",
            "person with skullcap",
            "skullcap"
        ],
        "name": "person with skullcap",
        "shortcodes": [
            ":person_with_skullcap:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧕",
        "emoticons": [],
        "keywords": [
            "headscarf",
            "hijab",
            "mantilla",
            "tichel",
            "woman with headscarf"
        ],
        "name": "woman with headscarf",
        "shortcodes": [
            ":woman_with_headscarf:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤵",
        "emoticons": [],
        "keywords": [
            "groom",
            "person",
            "person in tux",
            "person in tuxedo",
            "tuxedo"
        ],
        "name": "person in tuxedo",
        "shortcodes": [
            ":person_in_tuxedo:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👰",
        "emoticons": [],
        "keywords": [
            "bride",
            "person",
            "person with veil",
            "veil",
            "wedding"
        ],
        "name": "person with veil",
        "shortcodes": [
            ":person_with_veil:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤰",
        "emoticons": [],
        "keywords": [
            "pregnant",
            "woman"
        ],
        "name": "pregnant woman",
        "shortcodes": [
            ":pregnant_woman:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤱",
        "emoticons": [],
        "keywords": [
            "baby",
            "breast",
            "breast-feeding",
            "nursing"
        ],
        "name": "breast-feeding",
        "shortcodes": [
            ":breast-feeding:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👼",
        "emoticons": [],
        "keywords": [
            "angel",
            "baby",
            "face",
            "fairy tale",
            "fantasy"
        ],
        "name": "baby angel",
        "shortcodes": [
            ":baby_angel:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🎅",
        "emoticons": [],
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
        ],
        "name": "Santa Claus",
        "shortcodes": [
            ":Santa_Claus:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤶",
        "emoticons": [],
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
        ],
        "name": "Mrs. Claus",
        "shortcodes": [
            ":Mrs._Claus:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦸",
        "emoticons": [],
        "keywords": [
            "good",
            "hero",
            "heroine",
            "superhero",
            "superpower"
        ],
        "name": "superhero",
        "shortcodes": [
            ":superhero:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦸‍♂️",
        "emoticons": [],
        "keywords": [
            "good",
            "hero",
            "man",
            "man superhero",
            "superpower"
        ],
        "name": "man superhero",
        "shortcodes": [
            ":man_superhero:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦸‍♀️",
        "emoticons": [],
        "keywords": [
            "good",
            "hero",
            "heroine",
            "superpower",
            "woman",
            "woman superhero"
        ],
        "name": "woman superhero",
        "shortcodes": [
            ":woman_superhero:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦹",
        "emoticons": [],
        "keywords": [
            "criminal",
            "evil",
            "superpower",
            "supervillain",
            "villain"
        ],
        "name": "supervillain",
        "shortcodes": [
            ":supervillain:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦹‍♂️",
        "emoticons": [],
        "keywords": [
            "criminal",
            "evil",
            "man",
            "man supervillain",
            "superpower",
            "villain"
        ],
        "name": "man supervillain",
        "shortcodes": [
            ":man_supervillain:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🦹‍♀️",
        "emoticons": [],
        "keywords": [
            "criminal",
            "evil",
            "superpower",
            "villain",
            "woman",
            "woman supervillain"
        ],
        "name": "woman supervillain",
        "shortcodes": [
            ":woman_supervillain:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧙",
        "emoticons": [],
        "keywords": [
            "mage",
            "sorcerer",
            "sorceress",
            "witch",
            "wizard"
        ],
        "name": "mage",
        "shortcodes": [
            ":mage:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧙‍♂️",
        "emoticons": [],
        "keywords": [
            "man mage",
            "sorcerer",
            "wizard"
        ],
        "name": "man mage",
        "shortcodes": [
            ":man_mage:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧙‍♀️",
        "emoticons": [],
        "keywords": [
            "sorceress",
            "witch",
            "woman mage"
        ],
        "name": "woman mage",
        "shortcodes": [
            ":woman_mage:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧚",
        "emoticons": [],
        "keywords": [
            "fairy",
            "Oberon",
            "Puck",
            "Titania"
        ],
        "name": "fairy",
        "shortcodes": [
            ":fairy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧚‍♂️",
        "emoticons": [],
        "keywords": [
            "man fairy",
            "Oberon",
            "Puck"
        ],
        "name": "man fairy",
        "shortcodes": [
            ":man_fairy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧚‍♀️",
        "emoticons": [],
        "keywords": [
            "Titania",
            "woman fairy"
        ],
        "name": "woman fairy",
        "shortcodes": [
            ":woman_fairy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧛",
        "emoticons": [],
        "keywords": [
            "Dracula",
            "undead",
            "vampire"
        ],
        "name": "vampire",
        "shortcodes": [
            ":vampire:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧛‍♂️",
        "emoticons": [],
        "keywords": [
            "Dracula",
            "man vampire",
            "undead"
        ],
        "name": "man vampire",
        "shortcodes": [
            ":man_vampire:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧛‍♀️",
        "emoticons": [],
        "keywords": [
            "undead",
            "woman vampire"
        ],
        "name": "woman vampire",
        "shortcodes": [
            ":woman_vampire:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧜",
        "emoticons": [],
        "keywords": [
            "mermaid",
            "merman",
            "merperson",
            "merwoman"
        ],
        "name": "merperson",
        "shortcodes": [
            ":merperson:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧜‍♂️",
        "emoticons": [],
        "keywords": [
            "merman",
            "Triton"
        ],
        "name": "merman",
        "shortcodes": [
            ":merman:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧜‍♀️",
        "emoticons": [],
        "keywords": [
            "mermaid",
            "merwoman"
        ],
        "name": "mermaid",
        "shortcodes": [
            ":mermaid:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧝",
        "emoticons": [],
        "keywords": [
            "elf",
            "magical"
        ],
        "name": "elf",
        "shortcodes": [
            ":elf:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧝‍♂️",
        "emoticons": [],
        "keywords": [
            "magical",
            "man elf"
        ],
        "name": "man elf",
        "shortcodes": [
            ":man_elf:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧝‍♀️",
        "emoticons": [],
        "keywords": [
            "magical",
            "woman elf"
        ],
        "name": "woman elf",
        "shortcodes": [
            ":woman_elf:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧞",
        "emoticons": [],
        "keywords": [
            "djinn",
            "genie"
        ],
        "name": "genie",
        "shortcodes": [
            ":genie:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧞‍♂️",
        "emoticons": [],
        "keywords": [
            "djinn",
            "man genie"
        ],
        "name": "man genie",
        "shortcodes": [
            ":man_genie:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧞‍♀️",
        "emoticons": [],
        "keywords": [
            "djinn",
            "woman genie"
        ],
        "name": "woman genie",
        "shortcodes": [
            ":woman_genie:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧟",
        "emoticons": [],
        "keywords": [
            "undead",
            "walking dead",
            "zombie"
        ],
        "name": "zombie",
        "shortcodes": [
            ":zombie:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧟‍♂️",
        "emoticons": [],
        "keywords": [
            "man zombie",
            "undead",
            "walking dead"
        ],
        "name": "man zombie",
        "shortcodes": [
            ":man_zombie:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧟‍♀️",
        "emoticons": [],
        "keywords": [
            "undead",
            "walking dead",
            "woman zombie"
        ],
        "name": "woman zombie",
        "shortcodes": [
            ":woman_zombie:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💆",
        "emoticons": [],
        "keywords": [
            "face",
            "massage",
            "person getting massage",
            "salon"
        ],
        "name": "person getting massage",
        "shortcodes": [
            ":person_getting_massage:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💆‍♂️",
        "emoticons": [],
        "keywords": [
            "face",
            "man",
            "man getting massage",
            "massage"
        ],
        "name": "man getting massage",
        "shortcodes": [
            ":man_getting_massage:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💆‍♀️",
        "emoticons": [],
        "keywords": [
            "face",
            "massage",
            "woman",
            "woman getting massage"
        ],
        "name": "woman getting massage",
        "shortcodes": [
            ":woman_getting_massage:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💇",
        "emoticons": [],
        "keywords": [
            "barber",
            "beauty",
            "haircut",
            "parlor",
            "person getting haircut",
            "parlour"
        ],
        "name": "person getting haircut",
        "shortcodes": [
            ":person_getting_haircut:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💇‍♂️",
        "emoticons": [],
        "keywords": [
            "haircut",
            "hairdresser",
            "man",
            "man getting haircut"
        ],
        "name": "man getting haircut",
        "shortcodes": [
            ":man_getting_haircut:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💇‍♀️",
        "emoticons": [],
        "keywords": [
            "haircut",
            "hairdresser",
            "woman",
            "woman getting haircut"
        ],
        "name": "woman getting haircut",
        "shortcodes": [
            ":woman_getting_haircut:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚶",
        "emoticons": [],
        "keywords": [
            "hike",
            "person walking",
            "walk",
            "walking"
        ],
        "name": "person walking",
        "shortcodes": [
            ":person_walking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚶‍♂️",
        "emoticons": [],
        "keywords": [
            "hike",
            "man",
            "man walking",
            "walk"
        ],
        "name": "man walking",
        "shortcodes": [
            ":man_walking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚶‍♀️",
        "emoticons": [],
        "keywords": [
            "hike",
            "walk",
            "woman",
            "woman walking"
        ],
        "name": "woman walking",
        "shortcodes": [
            ":woman_walking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧍",
        "emoticons": [],
        "keywords": [
            "person standing",
            "stand",
            "standing"
        ],
        "name": "person standing",
        "shortcodes": [
            ":person_standing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧍‍♂️",
        "emoticons": [],
        "keywords": [
            "man",
            "standing"
        ],
        "name": "man standing",
        "shortcodes": [
            ":man_standing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧍‍♀️",
        "emoticons": [],
        "keywords": [
            "standing",
            "woman"
        ],
        "name": "woman standing",
        "shortcodes": [
            ":woman_standing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧎",
        "emoticons": [],
        "keywords": [
            "kneel",
            "kneeling",
            "person kneeling"
        ],
        "name": "person kneeling",
        "shortcodes": [
            ":person_kneeling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧎‍♂️",
        "emoticons": [],
        "keywords": [
            "kneeling",
            "man"
        ],
        "name": "man kneeling",
        "shortcodes": [
            ":man_kneeling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧎‍♀️",
        "emoticons": [],
        "keywords": [
            "kneeling",
            "woman"
        ],
        "name": "woman kneeling",
        "shortcodes": [
            ":woman_kneeling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🦯",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "blind",
            "person with guide cane",
            "person with long mobility cane",
            "person with white cane"
        ],
        "name": "person with white cane",
        "shortcodes": [
            ":person_with_white_cane:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🦯",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "blind",
            "man",
            "man with white cane",
            "man with guide cane"
        ],
        "name": "man with white cane",
        "shortcodes": [
            ":man_with_white_cane:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🦯",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "blind",
            "woman",
            "woman with white cane",
            "woman with guide cane"
        ],
        "name": "woman with white cane",
        "shortcodes": [
            ":woman_with_white_cane:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🦼",
        "emoticons": [],
        "keywords": [
            "person in motorised wheelchair",
            "accessibility",
            "person in motorized wheelchair",
            "wheelchair",
            "person in powered wheelchair"
        ],
        "name": "person in motorized wheelchair",
        "shortcodes": [
            ":person_in_motorized_wheelchair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🦼",
        "emoticons": [],
        "keywords": [
            "man in motorised wheelchair",
            "accessibility",
            "man",
            "man in motorized wheelchair",
            "wheelchair",
            "man in powered wheelchair"
        ],
        "name": "man in motorized wheelchair",
        "shortcodes": [
            ":man_in_motorized_wheelchair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🦼",
        "emoticons": [],
        "keywords": [
            "woman in motorised wheelchair",
            "accessibility",
            "wheelchair",
            "woman",
            "woman in motorized wheelchair",
            "woman in powered wheelchair"
        ],
        "name": "woman in motorized wheelchair",
        "shortcodes": [
            ":woman_in_motorized_wheelchair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🦽",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "person in manual wheelchair",
            "wheelchair"
        ],
        "name": "person in manual wheelchair",
        "shortcodes": [
            ":person_in_manual_wheelchair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍🦽",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "man",
            "man in manual wheelchair",
            "wheelchair"
        ],
        "name": "man in manual wheelchair",
        "shortcodes": [
            ":man_in_manual_wheelchair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍🦽",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "wheelchair",
            "woman",
            "woman in manual wheelchair"
        ],
        "name": "woman in manual wheelchair",
        "shortcodes": [
            ":woman_in_manual_wheelchair:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏃",
        "emoticons": [],
        "keywords": [
            "marathon",
            "person running",
            "running"
        ],
        "name": "person running",
        "shortcodes": [
            ":person_running:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏃‍♂️",
        "emoticons": [],
        "keywords": [
            "man",
            "marathon",
            "racing",
            "running"
        ],
        "name": "man running",
        "shortcodes": [
            ":man_running:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏃‍♀️",
        "emoticons": [],
        "keywords": [
            "marathon",
            "racing",
            "running",
            "woman"
        ],
        "name": "woman running",
        "shortcodes": [
            ":woman_running:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💃",
        "emoticons": [],
        "keywords": [
            "dance",
            "dancing",
            "woman"
        ],
        "name": "woman dancing",
        "shortcodes": [
            ":woman_dancing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🕺",
        "emoticons": [],
        "keywords": [
            "dance",
            "dancing",
            "man"
        ],
        "name": "man dancing",
        "shortcodes": [
            ":man_dancing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🕴️",
        "emoticons": [],
        "keywords": [
            "business",
            "person",
            "person in suit levitating",
            "suit"
        ],
        "name": "person in suit levitating",
        "shortcodes": [
            ":person_in_suit_levitating:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👯",
        "emoticons": [],
        "keywords": [
            "bunny ear",
            "dancer",
            "partying",
            "people with bunny ears"
        ],
        "name": "people with bunny ears",
        "shortcodes": [
            ":people_with_bunny_ears:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👯‍♂️",
        "emoticons": [],
        "keywords": [
            "bunny ear",
            "dancer",
            "men",
            "men with bunny ears",
            "partying"
        ],
        "name": "men with bunny ears",
        "shortcodes": [
            ":men_with_bunny_ears:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👯‍♀️",
        "emoticons": [],
        "keywords": [
            "bunny ear",
            "dancer",
            "partying",
            "women",
            "women with bunny ears"
        ],
        "name": "women with bunny ears",
        "shortcodes": [
            ":women_with_bunny_ears:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧖",
        "emoticons": [],
        "keywords": [
            "person in steamy room",
            "sauna",
            "steam room"
        ],
        "name": "person in steamy room",
        "shortcodes": [
            ":person_in_steamy_room:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧖‍♂️",
        "emoticons": [],
        "keywords": [
            "man in steam room",
            "man in steamy room",
            "sauna",
            "steam room"
        ],
        "name": "man in steamy room",
        "shortcodes": [
            ":man_in_steamy_room:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧖‍♀️",
        "emoticons": [],
        "keywords": [
            "sauna",
            "steam room",
            "woman in steam room",
            "woman in steamy room"
        ],
        "name": "woman in steamy room",
        "shortcodes": [
            ":woman_in_steamy_room:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧗",
        "emoticons": [],
        "keywords": [
            "climber",
            "person climbing"
        ],
        "name": "person climbing",
        "shortcodes": [
            ":person_climbing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧗‍♂️",
        "emoticons": [],
        "keywords": [
            "climber",
            "man climbing"
        ],
        "name": "man climbing",
        "shortcodes": [
            ":man_climbing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧗‍♀️",
        "emoticons": [],
        "keywords": [
            "climber",
            "woman climbing"
        ],
        "name": "woman climbing",
        "shortcodes": [
            ":woman_climbing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤺",
        "emoticons": [],
        "keywords": [
            "fencer",
            "fencing",
            "person fencing",
            "sword"
        ],
        "name": "person fencing",
        "shortcodes": [
            ":person_fencing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏇",
        "emoticons": [],
        "keywords": [
            "horse",
            "jockey",
            "racehorse",
            "racing"
        ],
        "name": "horse racing",
        "shortcodes": [
            ":horse_racing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "⛷️",
        "emoticons": [],
        "keywords": [
            "ski",
            "skier",
            "snow"
        ],
        "name": "skier",
        "shortcodes": [
            ":skier:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏂",
        "emoticons": [],
        "keywords": [
            "ski",
            "snow",
            "snowboard",
            "snowboarder"
        ],
        "name": "snowboarder",
        "shortcodes": [
            ":snowboarder:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏌️",
        "emoticons": [],
        "keywords": [
            "ball",
            "golf",
            "golfer",
            "person golfing"
        ],
        "name": "person golfing",
        "shortcodes": [
            ":person_golfing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏌️‍♂️",
        "emoticons": [],
        "keywords": [],
        "name": "man golfing",
        "shortcodes": [
            ":man_golfing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏌️‍♀️",
        "emoticons": [],
        "keywords": [],
        "name": "woman golfing",
        "shortcodes": [
            ":woman_golfing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏄",
        "emoticons": [],
        "keywords": [
            "person surfing",
            "surfer",
            "surfing"
        ],
        "name": "person surfing",
        "shortcodes": [
            ":person_surfing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏄‍♂️",
        "emoticons": [],
        "keywords": [
            "man",
            "surfer",
            "surfing"
        ],
        "name": "man surfing",
        "shortcodes": [
            ":man_surfing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏄‍♀️",
        "emoticons": [],
        "keywords": [
            "surfer",
            "surfing",
            "woman"
        ],
        "name": "woman surfing",
        "shortcodes": [
            ":woman_surfing:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚣",
        "emoticons": [],
        "keywords": [
            "boat",
            "person",
            "person rowing boat",
            "rowboat"
        ],
        "name": "person rowing boat",
        "shortcodes": [
            ":person_rowing_boat:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚣‍♂️",
        "emoticons": [],
        "keywords": [
            "boat",
            "man",
            "man rowing boat",
            "rowboat"
        ],
        "name": "man rowing boat",
        "shortcodes": [
            ":man_rowing_boat:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚣‍♀️",
        "emoticons": [],
        "keywords": [
            "boat",
            "rowboat",
            "woman",
            "woman rowing boat"
        ],
        "name": "woman rowing boat",
        "shortcodes": [
            ":woman_rowing_boat:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏊",
        "emoticons": [],
        "keywords": [
            "person swimming",
            "swim",
            "swimmer"
        ],
        "name": "person swimming",
        "shortcodes": [
            ":person_swimming:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏊‍♂️",
        "emoticons": [],
        "keywords": [
            "man",
            "man swimming",
            "swim",
            "swimmer"
        ],
        "name": "man swimming",
        "shortcodes": [
            ":man_swimming:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏊‍♀️",
        "emoticons": [],
        "keywords": [
            "swim",
            "swimmer",
            "woman",
            "woman swimming"
        ],
        "name": "woman swimming",
        "shortcodes": [
            ":woman_swimming:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "⛹️",
        "emoticons": [],
        "keywords": [
            "ball",
            "person bouncing ball"
        ],
        "name": "person bouncing ball",
        "shortcodes": [
            ":person_bouncing_ball:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "⛹️‍♂️",
        "emoticons": [],
        "keywords": [],
        "name": "man bouncing ball",
        "shortcodes": [
            ":man_bouncing_ball:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "⛹️‍♀️",
        "emoticons": [],
        "keywords": [],
        "name": "woman bouncing ball",
        "shortcodes": [
            ":woman_bouncing_ball:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏋️",
        "emoticons": [],
        "keywords": [
            "lifter",
            "person lifting weights",
            "weight",
            "weightlifter"
        ],
        "name": "person lifting weights",
        "shortcodes": [
            ":person_lifting_weights:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏋️‍♂️",
        "emoticons": [],
        "keywords": [],
        "name": "man lifting weights",
        "shortcodes": [
            ":man_lifting_weights:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🏋️‍♀️",
        "emoticons": [],
        "keywords": [],
        "name": "woman lifting weights",
        "shortcodes": [
            ":woman_lifting_weights:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚴",
        "emoticons": [],
        "keywords": [
            "bicycle",
            "biking",
            "cyclist",
            "person biking",
            "person riding a bike"
        ],
        "name": "person biking",
        "shortcodes": [
            ":person_biking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚴‍♂️",
        "emoticons": [],
        "keywords": [
            "bicycle",
            "biking",
            "cyclist",
            "man",
            "man riding a bike"
        ],
        "name": "man biking",
        "shortcodes": [
            ":man_biking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚴‍♀️",
        "emoticons": [],
        "keywords": [
            "bicycle",
            "biking",
            "cyclist",
            "woman",
            "woman riding a bike"
        ],
        "name": "woman biking",
        "shortcodes": [
            ":woman_biking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚵",
        "emoticons": [],
        "keywords": [
            "bicycle",
            "bicyclist",
            "bike",
            "cyclist",
            "mountain",
            "person mountain biking"
        ],
        "name": "person mountain biking",
        "shortcodes": [
            ":person_mountain_biking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚵‍♂️",
        "emoticons": [],
        "keywords": [
            "bicycle",
            "bike",
            "cyclist",
            "man",
            "man mountain biking",
            "mountain"
        ],
        "name": "man mountain biking",
        "shortcodes": [
            ":man_mountain_biking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🚵‍♀️",
        "emoticons": [],
        "keywords": [
            "bicycle",
            "bike",
            "biking",
            "cyclist",
            "mountain",
            "woman"
        ],
        "name": "woman mountain biking",
        "shortcodes": [
            ":woman_mountain_biking:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤸",
        "emoticons": [],
        "keywords": [
            "cartwheel",
            "gymnastics",
            "person cartwheeling"
        ],
        "name": "person cartwheeling",
        "shortcodes": [
            ":person_cartwheeling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤸‍♂️",
        "emoticons": [],
        "keywords": [
            "cartwheel",
            "gymnastics",
            "man",
            "man cartwheeling"
        ],
        "name": "man cartwheeling",
        "shortcodes": [
            ":man_cartwheeling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤸‍♀️",
        "emoticons": [],
        "keywords": [
            "cartwheel",
            "gymnastics",
            "woman",
            "woman cartwheeling"
        ],
        "name": "woman cartwheeling",
        "shortcodes": [
            ":woman_cartwheeling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤼",
        "emoticons": [],
        "keywords": [
            "people wrestling",
            "wrestle",
            "wrestler"
        ],
        "name": "people wrestling",
        "shortcodes": [
            ":people_wrestling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤼‍♂️",
        "emoticons": [],
        "keywords": [
            "men",
            "men wrestling",
            "wrestle"
        ],
        "name": "men wrestling",
        "shortcodes": [
            ":men_wrestling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤼‍♀️",
        "emoticons": [],
        "keywords": [
            "women",
            "women wrestling",
            "wrestle"
        ],
        "name": "women wrestling",
        "shortcodes": [
            ":women_wrestling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤽",
        "emoticons": [],
        "keywords": [
            "person playing water polo",
            "polo",
            "water"
        ],
        "name": "person playing water polo",
        "shortcodes": [
            ":person_playing_water_polo:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤽‍♂️",
        "emoticons": [],
        "keywords": [
            "man",
            "man playing water polo",
            "water polo"
        ],
        "name": "man playing water polo",
        "shortcodes": [
            ":man_playing_water_polo:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤽‍♀️",
        "emoticons": [],
        "keywords": [
            "water polo",
            "woman",
            "woman playing water polo"
        ],
        "name": "woman playing water polo",
        "shortcodes": [
            ":woman_playing_water_polo:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤾",
        "emoticons": [],
        "keywords": [
            "ball",
            "handball",
            "person playing handball"
        ],
        "name": "person playing handball",
        "shortcodes": [
            ":person_playing_handball:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤾‍♂️",
        "emoticons": [],
        "keywords": [
            "handball",
            "man",
            "man playing handball"
        ],
        "name": "man playing handball",
        "shortcodes": [
            ":man_playing_handball:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤾‍♀️",
        "emoticons": [],
        "keywords": [
            "handball",
            "woman",
            "woman playing handball"
        ],
        "name": "woman playing handball",
        "shortcodes": [
            ":woman_playing_handball:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤹",
        "emoticons": [],
        "keywords": [
            "balance",
            "juggle",
            "multi-task",
            "person juggling",
            "skill",
            "multitask"
        ],
        "name": "person juggling",
        "shortcodes": [
            ":person_juggling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤹‍♂️",
        "emoticons": [],
        "keywords": [
            "juggling",
            "man",
            "multi-task",
            "multitask"
        ],
        "name": "man juggling",
        "shortcodes": [
            ":man_juggling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🤹‍♀️",
        "emoticons": [],
        "keywords": [
            "juggling",
            "multi-task",
            "woman",
            "multitask"
        ],
        "name": "woman juggling",
        "shortcodes": [
            ":woman_juggling:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧘",
        "emoticons": [],
        "keywords": [
            "meditation",
            "person in lotus position",
            "yoga"
        ],
        "name": "person in lotus position",
        "shortcodes": [
            ":person_in_lotus_position:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧘‍♂️",
        "emoticons": [],
        "keywords": [
            "man in lotus position",
            "meditation",
            "yoga"
        ],
        "name": "man in lotus position",
        "shortcodes": [
            ":man_in_lotus_position:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧘‍♀️",
        "emoticons": [],
        "keywords": [
            "meditation",
            "woman in lotus position",
            "yoga"
        ],
        "name": "woman in lotus position",
        "shortcodes": [
            ":woman_in_lotus_position:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🛀",
        "emoticons": [],
        "keywords": [
            "bath",
            "bathtub",
            "person taking bath",
            "tub"
        ],
        "name": "person taking bath",
        "shortcodes": [
            ":person_taking_bath:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🛌",
        "emoticons": [],
        "keywords": [
            "hotel",
            "person in bed",
            "sleep",
            "sleeping",
            "good night"
        ],
        "name": "person in bed",
        "shortcodes": [
            ":person_in_bed:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🧑‍🤝‍🧑",
        "emoticons": [],
        "keywords": [
            "couple",
            "hand",
            "hold",
            "holding hands",
            "people holding hands",
            "person"
        ],
        "name": "people holding hands",
        "shortcodes": [
            ":people_holding_hands:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👭",
        "emoticons": [],
        "keywords": [
            "couple",
            "hand",
            "holding hands",
            "women",
            "women holding hands",
            "two women holding hands"
        ],
        "name": "women holding hands",
        "shortcodes": [
            ":women_holding_hands:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👫",
        "emoticons": [],
        "keywords": [
            "couple",
            "hand",
            "hold",
            "holding hands",
            "man",
            "woman",
            "woman and man holding hands",
            "man and woman holding hands"
        ],
        "name": "woman and man holding hands",
        "shortcodes": [
            ":woman_and_man_holding_hands:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👬",
        "emoticons": [],
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
        ],
        "name": "men holding hands",
        "shortcodes": [
            ":men_holding_hands:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💏",
        "emoticons": [],
        "keywords": [
            "couple",
            "kiss"
        ],
        "name": "kiss",
        "shortcodes": [
            ":kiss:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍❤️‍💋‍👨",
        "emoticons": [],
        "keywords": [
            "couple",
            "kiss",
            "man",
            "woman"
        ],
        "name": "kiss: woman, man",
        "shortcodes": [
            ":kiss:_woman,_man:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍❤️‍💋‍👨",
        "emoticons": [],
        "keywords": [
            "couple",
            "kiss",
            "man"
        ],
        "name": "kiss: man, man",
        "shortcodes": [
            ":kiss:_man,_man:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍❤️‍💋‍👩",
        "emoticons": [],
        "keywords": [
            "couple",
            "kiss",
            "woman"
        ],
        "name": "kiss: woman, woman",
        "shortcodes": [
            ":kiss:_woman,_woman:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "💑",
        "emoticons": [],
        "keywords": [
            "couple",
            "couple with heart",
            "love"
        ],
        "name": "couple with heart",
        "shortcodes": [
            ":couple_with_heart:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍❤️‍👨",
        "emoticons": [],
        "keywords": [
            "couple",
            "couple with heart",
            "love",
            "man",
            "woman"
        ],
        "name": "couple with heart: woman, man",
        "shortcodes": [
            ":couple_with_heart:_woman,_man:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍❤️‍👨",
        "emoticons": [],
        "keywords": [
            "couple",
            "couple with heart",
            "love",
            "man"
        ],
        "name": "couple with heart: man, man",
        "shortcodes": [
            ":couple_with_heart:_man,_man:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍❤️‍👩",
        "emoticons": [],
        "keywords": [
            "couple",
            "couple with heart",
            "love",
            "woman"
        ],
        "name": "couple with heart: woman, woman",
        "shortcodes": [
            ":couple_with_heart:_woman,_woman:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👪",
        "emoticons": [],
        "keywords": [
            "family"
        ],
        "name": "family",
        "shortcodes": [
            ":family:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👩‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "man",
            "woman"
        ],
        "name": "family: man, woman, boy",
        "shortcodes": [
            ":family:_man,_woman,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👩‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "man",
            "woman"
        ],
        "name": "family: man, woman, girl",
        "shortcodes": [
            ":family:_man,_woman,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👩‍👧‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "girl",
            "man",
            "woman"
        ],
        "name": "family: man, woman, girl, boy",
        "shortcodes": [
            ":family:_man,_woman,_girl,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👩‍👦‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "man",
            "woman"
        ],
        "name": "family: man, woman, boy, boy",
        "shortcodes": [
            ":family:_man,_woman,_boy,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👩‍👧‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "man",
            "woman"
        ],
        "name": "family: man, woman, girl, girl",
        "shortcodes": [
            ":family:_man,_woman,_girl,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👨‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "man"
        ],
        "name": "family: man, man, boy",
        "shortcodes": [
            ":family:_man,_man,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👨‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "man"
        ],
        "name": "family: man, man, girl",
        "shortcodes": [
            ":family:_man,_man,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👨‍👧‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "girl",
            "man"
        ],
        "name": "family: man, man, girl, boy",
        "shortcodes": [
            ":family:_man,_man,_girl,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👨‍👦‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "man"
        ],
        "name": "family: man, man, boy, boy",
        "shortcodes": [
            ":family:_man,_man,_boy,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👨‍👧‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "man"
        ],
        "name": "family: man, man, girl, girl",
        "shortcodes": [
            ":family:_man,_man,_girl,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👩‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "woman"
        ],
        "name": "family: woman, woman, boy",
        "shortcodes": [
            ":family:_woman,_woman,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👩‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "woman"
        ],
        "name": "family: woman, woman, girl",
        "shortcodes": [
            ":family:_woman,_woman,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👩‍👧‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "girl",
            "woman"
        ],
        "name": "family: woman, woman, girl, boy",
        "shortcodes": [
            ":family:_woman,_woman,_girl,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👩‍👦‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "woman"
        ],
        "name": "family: woman, woman, boy, boy",
        "shortcodes": [
            ":family:_woman,_woman,_boy,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👩‍👧‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "woman"
        ],
        "name": "family: woman, woman, girl, girl",
        "shortcodes": [
            ":family:_woman,_woman,_girl,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "man"
        ],
        "name": "family: man, boy",
        "shortcodes": [
            ":family:_man,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👦‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "man"
        ],
        "name": "family: man, boy, boy",
        "shortcodes": [
            ":family:_man,_boy,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "man"
        ],
        "name": "family: man, girl",
        "shortcodes": [
            ":family:_man,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👧‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "girl",
            "man"
        ],
        "name": "family: man, girl, boy",
        "shortcodes": [
            ":family:_man,_girl,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👨‍👧‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "man"
        ],
        "name": "family: man, girl, girl",
        "shortcodes": [
            ":family:_man,_girl,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "woman"
        ],
        "name": "family: woman, boy",
        "shortcodes": [
            ":family:_woman,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👦‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "woman"
        ],
        "name": "family: woman, boy, boy",
        "shortcodes": [
            ":family:_woman,_boy,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "woman"
        ],
        "name": "family: woman, girl",
        "shortcodes": [
            ":family:_woman,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👧‍👦",
        "emoticons": [],
        "keywords": [
            "boy",
            "family",
            "girl",
            "woman"
        ],
        "name": "family: woman, girl, boy",
        "shortcodes": [
            ":family:_woman,_girl,_boy:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👩‍👧‍👧",
        "emoticons": [],
        "keywords": [
            "family",
            "girl",
            "woman"
        ],
        "name": "family: woman, girl, girl",
        "shortcodes": [
            ":family:_woman,_girl,_girl:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "🗣️",
        "emoticons": [],
        "keywords": [
            "face",
            "head",
            "silhouette",
            "speak",
            "speaking"
        ],
        "name": "speaking head",
        "shortcodes": [
            ":speaking_head:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👤",
        "emoticons": [],
        "keywords": [
            "bust",
            "bust in silhouette",
            "silhouette"
        ],
        "name": "bust in silhouette",
        "shortcodes": [
            ":bust_in_silhouette:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👥",
        "emoticons": [],
        "keywords": [
            "bust",
            "busts in silhouette",
            "silhouette"
        ],
        "name": "busts in silhouette",
        "shortcodes": [
            ":busts_in_silhouette:"
        ]
    },
    {
        "category": "People & Body",
        "codepoints": "👣",
        "emoticons": [],
        "keywords": [
            "clothing",
            "footprint",
            "footprints",
            "print"
        ],
        "name": "footprints",
        "shortcodes": [
            ":footprints:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐵",
        "emoticons": [],
        "keywords": [
            "face",
            "monkey"
        ],
        "name": "monkey face",
        "shortcodes": [
            ":monkey_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐒",
        "emoticons": [],
        "keywords": [
            "monkey"
        ],
        "name": "monkey",
        "shortcodes": [
            ":monkey:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦍",
        "emoticons": [],
        "keywords": [
            "gorilla"
        ],
        "name": "gorilla",
        "shortcodes": [
            ":gorilla:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦧",
        "emoticons": [],
        "keywords": [
            "ape",
            "orangutan"
        ],
        "name": "orangutan",
        "shortcodes": [
            ":orangutan:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐶",
        "emoticons": [],
        "keywords": [
            "dog",
            "face",
            "pet"
        ],
        "name": "dog face",
        "shortcodes": [
            ":dog_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐕",
        "emoticons": [],
        "keywords": [
            "dog",
            "pet"
        ],
        "name": "dog",
        "shortcodes": [
            ":dog:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦮",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "blind",
            "guide",
            "guide dog"
        ],
        "name": "guide dog",
        "shortcodes": [
            ":guide_dog:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐕‍🦺",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "assistance",
            "dog",
            "service"
        ],
        "name": "service dog",
        "shortcodes": [
            ":service_dog:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐩",
        "emoticons": [],
        "keywords": [
            "dog",
            "poodle"
        ],
        "name": "poodle",
        "shortcodes": [
            ":poodle:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐺",
        "emoticons": [],
        "keywords": [
            "face",
            "wolf"
        ],
        "name": "wolf",
        "shortcodes": [
            ":wolf:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦊",
        "emoticons": [],
        "keywords": [
            "face",
            "fox"
        ],
        "name": "fox",
        "shortcodes": [
            ":fox:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦝",
        "emoticons": [],
        "keywords": [
            "curious",
            "raccoon",
            "sly"
        ],
        "name": "raccoon",
        "shortcodes": [
            ":raccoon:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐱",
        "emoticons": [],
        "keywords": [
            "cat",
            "face",
            "pet"
        ],
        "name": "cat face",
        "shortcodes": [
            ":cat_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐈",
        "emoticons": [],
        "keywords": [
            "cat",
            "pet"
        ],
        "name": "cat",
        "shortcodes": [
            ":cat:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦁",
        "emoticons": [],
        "keywords": [
            "face",
            "Leo",
            "lion",
            "zodiac"
        ],
        "name": "lion",
        "shortcodes": [
            ":lion:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐯",
        "emoticons": [],
        "keywords": [
            "face",
            "tiger"
        ],
        "name": "tiger face",
        "shortcodes": [
            ":tiger_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐅",
        "emoticons": [],
        "keywords": [
            "tiger"
        ],
        "name": "tiger",
        "shortcodes": [
            ":tiger:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐆",
        "emoticons": [],
        "keywords": [
            "leopard"
        ],
        "name": "leopard",
        "shortcodes": [
            ":leopard:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐴",
        "emoticons": [],
        "keywords": [
            "face",
            "horse"
        ],
        "name": "horse face",
        "shortcodes": [
            ":horse_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐎",
        "emoticons": [],
        "keywords": [
            "equestrian",
            "horse",
            "racehorse",
            "racing"
        ],
        "name": "horse",
        "shortcodes": [
            ":horse:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦄",
        "emoticons": [],
        "keywords": [
            "face",
            "unicorn"
        ],
        "name": "unicorn",
        "shortcodes": [
            ":unicorn:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦓",
        "emoticons": [],
        "keywords": [
            "stripe",
            "zebra"
        ],
        "name": "zebra",
        "shortcodes": [
            ":zebra:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦌",
        "emoticons": [],
        "keywords": [
            "deer",
            "stag"
        ],
        "name": "deer",
        "shortcodes": [
            ":deer:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐮",
        "emoticons": [],
        "keywords": [
            "cow",
            "face"
        ],
        "name": "cow face",
        "shortcodes": [
            ":cow_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐂",
        "emoticons": [],
        "keywords": [
            "bull",
            "ox",
            "Taurus",
            "zodiac"
        ],
        "name": "ox",
        "shortcodes": [
            ":ox:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐃",
        "emoticons": [],
        "keywords": [
            "buffalo",
            "water"
        ],
        "name": "water buffalo",
        "shortcodes": [
            ":water_buffalo:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐄",
        "emoticons": [],
        "keywords": [
            "cow"
        ],
        "name": "cow",
        "shortcodes": [
            ":cow:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐷",
        "emoticons": [],
        "keywords": [
            "face",
            "pig"
        ],
        "name": "pig face",
        "shortcodes": [
            ":pig_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐖",
        "emoticons": [],
        "keywords": [
            "pig",
            "sow"
        ],
        "name": "pig",
        "shortcodes": [
            ":pig:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐗",
        "emoticons": [],
        "keywords": [
            "boar",
            "pig"
        ],
        "name": "boar",
        "shortcodes": [
            ":boar:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐽",
        "emoticons": [],
        "keywords": [
            "face",
            "nose",
            "pig"
        ],
        "name": "pig nose",
        "shortcodes": [
            ":pig_nose:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐏",
        "emoticons": [],
        "keywords": [
            "Aries",
            "male",
            "ram",
            "sheep",
            "zodiac"
        ],
        "name": "ram",
        "shortcodes": [
            ":ram:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐑",
        "emoticons": [],
        "keywords": [
            "ewe",
            "female",
            "sheep"
        ],
        "name": "ewe",
        "shortcodes": [
            ":ewe:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐐",
        "emoticons": [],
        "keywords": [
            "Capricorn",
            "goat",
            "zodiac"
        ],
        "name": "goat",
        "shortcodes": [
            ":goat:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐪",
        "emoticons": [],
        "keywords": [
            "camel",
            "dromedary",
            "hump"
        ],
        "name": "camel",
        "shortcodes": [
            ":camel:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐫",
        "emoticons": [],
        "keywords": [
            "bactrian",
            "camel",
            "hump",
            "two-hump camel",
            "Bactrian"
        ],
        "name": "two-hump camel",
        "shortcodes": [
            ":two-hump_camel:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦙",
        "emoticons": [],
        "keywords": [
            "alpaca",
            "guanaco",
            "llama",
            "vicuña",
            "wool"
        ],
        "name": "llama",
        "shortcodes": [
            ":llama:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦒",
        "emoticons": [],
        "keywords": [
            "giraffe",
            "spots"
        ],
        "name": "giraffe",
        "shortcodes": [
            ":giraffe:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐘",
        "emoticons": [],
        "keywords": [
            "elephant"
        ],
        "name": "elephant",
        "shortcodes": [
            ":elephant:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦏",
        "emoticons": [],
        "keywords": [
            "rhino",
            "rhinoceros"
        ],
        "name": "rhinoceros",
        "shortcodes": [
            ":rhinoceros:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦛",
        "emoticons": [],
        "keywords": [
            "hippo",
            "hippopotamus"
        ],
        "name": "hippopotamus",
        "shortcodes": [
            ":hippopotamus:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐭",
        "emoticons": [],
        "keywords": [
            "face",
            "mouse",
            "pet"
        ],
        "name": "mouse face",
        "shortcodes": [
            ":mouse_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐁",
        "emoticons": [],
        "keywords": [
            "mouse",
            "pet",
            "rodent"
        ],
        "name": "mouse",
        "shortcodes": [
            ":mouse:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐀",
        "emoticons": [],
        "keywords": [
            "pet",
            "rat",
            "rodent"
        ],
        "name": "rat",
        "shortcodes": [
            ":rat:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐹",
        "emoticons": [],
        "keywords": [
            "face",
            "hamster",
            "pet"
        ],
        "name": "hamster",
        "shortcodes": [
            ":hamster:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐰",
        "emoticons": [],
        "keywords": [
            "bunny",
            "face",
            "pet",
            "rabbit"
        ],
        "name": "rabbit face",
        "shortcodes": [
            ":rabbit_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐇",
        "emoticons": [],
        "keywords": [
            "bunny",
            "pet",
            "rabbit"
        ],
        "name": "rabbit",
        "shortcodes": [
            ":rabbit:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐿️",
        "emoticons": [],
        "keywords": [
            "chipmunk",
            "squirrel"
        ],
        "name": "chipmunk",
        "shortcodes": [
            ":chipmunk:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦔",
        "emoticons": [],
        "keywords": [
            "hedgehog",
            "spiny"
        ],
        "name": "hedgehog",
        "shortcodes": [
            ":hedgehog:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦇",
        "emoticons": [],
        "keywords": [
            "bat",
            "vampire"
        ],
        "name": "bat",
        "shortcodes": [
            ":bat:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐻",
        "emoticons": [],
        "keywords": [
            "bear",
            "face"
        ],
        "name": "bear",
        "shortcodes": [
            ":bear:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐨",
        "emoticons": [],
        "keywords": [
            "koala",
            "marsupial",
            "face"
        ],
        "name": "koala",
        "shortcodes": [
            ":koala:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐼",
        "emoticons": [],
        "keywords": [
            "face",
            "panda"
        ],
        "name": "panda",
        "shortcodes": [
            ":panda:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦥",
        "emoticons": [],
        "keywords": [
            "lazy",
            "sloth",
            "slow"
        ],
        "name": "sloth",
        "shortcodes": [
            ":sloth:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦦",
        "emoticons": [],
        "keywords": [
            "fishing",
            "otter",
            "playful"
        ],
        "name": "otter",
        "shortcodes": [
            ":otter:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦨",
        "emoticons": [],
        "keywords": [
            "skunk",
            "stink"
        ],
        "name": "skunk",
        "shortcodes": [
            ":skunk:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦘",
        "emoticons": [],
        "keywords": [
            "Australia",
            "joey",
            "jump",
            "kangaroo",
            "marsupial"
        ],
        "name": "kangaroo",
        "shortcodes": [
            ":kangaroo:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦡",
        "emoticons": [],
        "keywords": [
            "badger",
            "honey badger",
            "pester"
        ],
        "name": "badger",
        "shortcodes": [
            ":badger:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐾",
        "emoticons": [],
        "keywords": [
            "feet",
            "paw",
            "paw prints",
            "print"
        ],
        "name": "paw prints",
        "shortcodes": [
            ":paw_prints:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦃",
        "emoticons": [],
        "keywords": [
            "bird",
            "poultry",
            "turkey"
        ],
        "name": "turkey",
        "shortcodes": [
            ":turkey:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐔",
        "emoticons": [],
        "keywords": [
            "bird",
            "chicken",
            "poultry"
        ],
        "name": "chicken",
        "shortcodes": [
            ":chicken:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐓",
        "emoticons": [],
        "keywords": [
            "bird",
            "rooster"
        ],
        "name": "rooster",
        "shortcodes": [
            ":rooster:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐣",
        "emoticons": [],
        "keywords": [
            "baby",
            "bird",
            "chick",
            "hatching"
        ],
        "name": "hatching chick",
        "shortcodes": [
            ":hatching_chick:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐤",
        "emoticons": [],
        "keywords": [
            "baby",
            "bird",
            "chick"
        ],
        "name": "baby chick",
        "shortcodes": [
            ":baby_chick:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐥",
        "emoticons": [],
        "keywords": [
            "baby",
            "bird",
            "chick",
            "front-facing baby chick"
        ],
        "name": "front-facing baby chick",
        "shortcodes": [
            ":front-facing_baby_chick:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐦",
        "emoticons": [],
        "keywords": [
            "bird"
        ],
        "name": "bird",
        "shortcodes": [
            ":bird:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐧",
        "emoticons": [],
        "keywords": [
            "bird",
            "penguin"
        ],
        "name": "penguin",
        "shortcodes": [
            ":penguin:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🕊️",
        "emoticons": [],
        "keywords": [
            "bird",
            "dove",
            "fly",
            "peace"
        ],
        "name": "dove",
        "shortcodes": [
            ":dove:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦅",
        "emoticons": [],
        "keywords": [
            "bird of prey",
            "eagle",
            "bird"
        ],
        "name": "eagle",
        "shortcodes": [
            ":eagle:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦆",
        "emoticons": [],
        "keywords": [
            "bird",
            "duck"
        ],
        "name": "duck",
        "shortcodes": [
            ":duck:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦢",
        "emoticons": [],
        "keywords": [
            "bird",
            "cygnet",
            "swan",
            "ugly duckling"
        ],
        "name": "swan",
        "shortcodes": [
            ":swan:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦉",
        "emoticons": [],
        "keywords": [
            "bird of prey",
            "owl",
            "wise",
            "bird"
        ],
        "name": "owl",
        "shortcodes": [
            ":owl:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦩",
        "emoticons": [],
        "keywords": [
            "flamboyant",
            "flamingo",
            "tropical"
        ],
        "name": "flamingo",
        "shortcodes": [
            ":flamingo:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦚",
        "emoticons": [],
        "keywords": [
            "bird",
            "ostentatious",
            "peacock",
            "peahen",
            "proud"
        ],
        "name": "peacock",
        "shortcodes": [
            ":peacock:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦜",
        "emoticons": [],
        "keywords": [
            "bird",
            "parrot",
            "pirate",
            "talk"
        ],
        "name": "parrot",
        "shortcodes": [
            ":parrot:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐸",
        "emoticons": [],
        "keywords": [
            "face",
            "frog"
        ],
        "name": "frog",
        "shortcodes": [
            ":frog:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐊",
        "emoticons": [],
        "keywords": [
            "crocodile"
        ],
        "name": "crocodile",
        "shortcodes": [
            ":crocodile:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐢",
        "emoticons": [],
        "keywords": [
            "terrapin",
            "tortoise",
            "turtle"
        ],
        "name": "turtle",
        "shortcodes": [
            ":turtle:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦎",
        "emoticons": [],
        "keywords": [
            "lizard",
            "reptile"
        ],
        "name": "lizard",
        "shortcodes": [
            ":lizard:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐍",
        "emoticons": [],
        "keywords": [
            "bearer",
            "Ophiuchus",
            "serpent",
            "snake",
            "zodiac"
        ],
        "name": "snake",
        "shortcodes": [
            ":snake:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐲",
        "emoticons": [],
        "keywords": [
            "dragon",
            "face",
            "fairy tale"
        ],
        "name": "dragon face",
        "shortcodes": [
            ":dragon_face:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐉",
        "emoticons": [],
        "keywords": [
            "dragon",
            "fairy tale"
        ],
        "name": "dragon",
        "shortcodes": [
            ":dragon:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦕",
        "emoticons": [],
        "keywords": [
            "brachiosaurus",
            "brontosaurus",
            "diplodocus",
            "sauropod"
        ],
        "name": "sauropod",
        "shortcodes": [
            ":sauropod:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦖",
        "emoticons": [],
        "keywords": [
            "T-Rex",
            "Tyrannosaurus Rex"
        ],
        "name": "T-Rex",
        "shortcodes": [
            ":T-Rex:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐳",
        "emoticons": [],
        "keywords": [
            "face",
            "spouting",
            "whale"
        ],
        "name": "spouting whale",
        "shortcodes": [
            ":spouting_whale:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐋",
        "emoticons": [],
        "keywords": [
            "whale"
        ],
        "name": "whale",
        "shortcodes": [
            ":whale:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐬",
        "emoticons": [],
        "keywords": [
            "dolphin",
            "porpoise",
            "flipper"
        ],
        "name": "dolphin",
        "shortcodes": [
            ":dolphin:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐟",
        "emoticons": [],
        "keywords": [
            "fish",
            "Pisces",
            "zodiac"
        ],
        "name": "fish",
        "shortcodes": [
            ":fish:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐠",
        "emoticons": [],
        "keywords": [
            "fish",
            "reef fish",
            "tropical"
        ],
        "name": "tropical fish",
        "shortcodes": [
            ":tropical_fish:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐡",
        "emoticons": [],
        "keywords": [
            "blowfish",
            "fish"
        ],
        "name": "blowfish",
        "shortcodes": [
            ":blowfish:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦈",
        "emoticons": [],
        "keywords": [
            "fish",
            "shark"
        ],
        "name": "shark",
        "shortcodes": [
            ":shark:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐙",
        "emoticons": [],
        "keywords": [
            "octopus"
        ],
        "name": "octopus",
        "shortcodes": [
            ":octopus:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐚",
        "emoticons": [],
        "keywords": [
            "shell",
            "spiral"
        ],
        "name": "spiral shell",
        "shortcodes": [
            ":spiral_shell:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐌",
        "emoticons": [],
        "keywords": [
            "mollusc",
            "snail"
        ],
        "name": "snail",
        "shortcodes": [
            ":snail:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦋",
        "emoticons": [],
        "keywords": [
            "butterfly",
            "insect",
            "moth",
            "pretty"
        ],
        "name": "butterfly",
        "shortcodes": [
            ":butterfly:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐛",
        "emoticons": [],
        "keywords": [
            "bug",
            "caterpillar",
            "insect",
            "worm"
        ],
        "name": "bug",
        "shortcodes": [
            ":bug:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐜",
        "emoticons": [],
        "keywords": [
            "ant",
            "insect"
        ],
        "name": "ant",
        "shortcodes": [
            ":ant:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐝",
        "emoticons": [],
        "keywords": [
            "bee",
            "honeybee",
            "insect"
        ],
        "name": "honeybee",
        "shortcodes": [
            ":honeybee:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🐞",
        "emoticons": [],
        "keywords": [
            "beetle",
            "insect",
            "lady beetle",
            "ladybird",
            "ladybug"
        ],
        "name": "lady beetle",
        "shortcodes": [
            ":lady_beetle:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦗",
        "emoticons": [],
        "keywords": [
            "cricket",
            "grasshopper"
        ],
        "name": "cricket",
        "shortcodes": [
            ":cricket:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🕷️",
        "emoticons": [],
        "keywords": [
            "arachnid",
            "spider",
            "insect"
        ],
        "name": "spider",
        "shortcodes": [
            ":spider:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🕸️",
        "emoticons": [],
        "keywords": [
            "spider",
            "web"
        ],
        "name": "spider web",
        "shortcodes": [
            ":spider_web:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦂",
        "emoticons": [],
        "keywords": [
            "scorpio",
            "Scorpio",
            "scorpion",
            "zodiac"
        ],
        "name": "scorpion",
        "shortcodes": [
            ":scorpion:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦟",
        "emoticons": [],
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
        ],
        "name": "mosquito",
        "shortcodes": [
            ":mosquito:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🦠",
        "emoticons": [],
        "keywords": [
            "amoeba",
            "bacteria",
            "microbe",
            "virus"
        ],
        "name": "microbe",
        "shortcodes": [
            ":microbe:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "💐",
        "emoticons": [],
        "keywords": [
            "bouquet",
            "flower"
        ],
        "name": "bouquet",
        "shortcodes": [
            ":bouquet:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌸",
        "emoticons": [],
        "keywords": [
            "blossom",
            "cherry",
            "flower"
        ],
        "name": "cherry blossom",
        "shortcodes": [
            ":cherry_blossom:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "💮",
        "emoticons": [],
        "keywords": [
            "flower",
            "white flower"
        ],
        "name": "white flower",
        "shortcodes": [
            ":white_flower:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🏵️",
        "emoticons": [],
        "keywords": [
            "plant",
            "rosette"
        ],
        "name": "rosette",
        "shortcodes": [
            ":rosette:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌹",
        "emoticons": [],
        "keywords": [
            "flower",
            "rose"
        ],
        "name": "rose",
        "shortcodes": [
            ":rose:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🥀",
        "emoticons": [],
        "keywords": [
            "flower",
            "wilted"
        ],
        "name": "wilted flower",
        "shortcodes": [
            ":wilted_flower:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌺",
        "emoticons": [],
        "keywords": [
            "flower",
            "hibiscus"
        ],
        "name": "hibiscus",
        "shortcodes": [
            ":hibiscus:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌻",
        "emoticons": [],
        "keywords": [
            "flower",
            "sun",
            "sunflower"
        ],
        "name": "sunflower",
        "shortcodes": [
            ":sunflower:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌼",
        "emoticons": [],
        "keywords": [
            "blossom",
            "flower"
        ],
        "name": "blossom",
        "shortcodes": [
            ":blossom:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌷",
        "emoticons": [],
        "keywords": [
            "flower",
            "tulip"
        ],
        "name": "tulip",
        "shortcodes": [
            ":tulip:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌱",
        "emoticons": [],
        "keywords": [
            "seedling",
            "young"
        ],
        "name": "seedling",
        "shortcodes": [
            ":seedling:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌲",
        "emoticons": [],
        "keywords": [
            "evergreen tree",
            "tree"
        ],
        "name": "evergreen tree",
        "shortcodes": [
            ":evergreen_tree:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌳",
        "emoticons": [],
        "keywords": [
            "deciduous",
            "shedding",
            "tree"
        ],
        "name": "deciduous tree",
        "shortcodes": [
            ":deciduous_tree:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌴",
        "emoticons": [],
        "keywords": [
            "palm",
            "tree"
        ],
        "name": "palm tree",
        "shortcodes": [
            ":palm_tree:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌵",
        "emoticons": [],
        "keywords": [
            "cactus",
            "plant"
        ],
        "name": "cactus",
        "shortcodes": [
            ":cactus:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌾",
        "emoticons": [],
        "keywords": [
            "ear",
            "grain",
            "rice",
            "sheaf of rice",
            "sheaf"
        ],
        "name": "sheaf of rice",
        "shortcodes": [
            ":sheaf_of_rice:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🌿",
        "emoticons": [],
        "keywords": [
            "herb",
            "leaf"
        ],
        "name": "herb",
        "shortcodes": [
            ":herb:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "☘️",
        "emoticons": [],
        "keywords": [
            "plant",
            "shamrock"
        ],
        "name": "shamrock",
        "shortcodes": [
            ":shamrock:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🍀",
        "emoticons": [],
        "keywords": [
            "4",
            "clover",
            "four",
            "four-leaf clover",
            "leaf"
        ],
        "name": "four leaf clover",
        "shortcodes": [
            ":four_leaf_clover:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🍁",
        "emoticons": [],
        "keywords": [
            "falling",
            "leaf",
            "maple"
        ],
        "name": "maple leaf",
        "shortcodes": [
            ":maple_leaf:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🍂",
        "emoticons": [],
        "keywords": [
            "fallen leaf",
            "falling",
            "leaf"
        ],
        "name": "fallen leaf",
        "shortcodes": [
            ":fallen_leaf:"
        ]
    },
    {
        "category": "Animals & Nature",
        "codepoints": "🍃",
        "emoticons": [],
        "keywords": [
            "blow",
            "flutter",
            "leaf",
            "leaf fluttering in wind",
            "wind"
        ],
        "name": "leaf fluttering in wind",
        "shortcodes": [
            ":leaf_fluttering_in_wind:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍇",
        "emoticons": [],
        "keywords": [
            "fruit",
            "grape",
            "grapes"
        ],
        "name": "grapes",
        "shortcodes": [
            ":grapes:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍈",
        "emoticons": [],
        "keywords": [
            "fruit",
            "melon"
        ],
        "name": "melon",
        "shortcodes": [
            ":melon:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍉",
        "emoticons": [],
        "keywords": [
            "fruit",
            "watermelon"
        ],
        "name": "watermelon",
        "shortcodes": [
            ":watermelon:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍊",
        "emoticons": [],
        "keywords": [
            "fruit",
            "mandarin",
            "orange",
            "tangerine"
        ],
        "name": "tangerine",
        "shortcodes": [
            ":tangerine:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍋",
        "emoticons": [],
        "keywords": [
            "citrus",
            "fruit",
            "lemon"
        ],
        "name": "lemon",
        "shortcodes": [
            ":lemon:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍌",
        "emoticons": [],
        "keywords": [
            "banana",
            "fruit"
        ],
        "name": "banana",
        "shortcodes": [
            ":banana:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍍",
        "emoticons": [],
        "keywords": [
            "fruit",
            "pineapple"
        ],
        "name": "pineapple",
        "shortcodes": [
            ":pineapple:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥭",
        "emoticons": [],
        "keywords": [
            "fruit",
            "mango",
            "tropical"
        ],
        "name": "mango",
        "shortcodes": [
            ":mango:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍎",
        "emoticons": [],
        "keywords": [
            "apple",
            "fruit",
            "red"
        ],
        "name": "red apple",
        "shortcodes": [
            ":red_apple:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍏",
        "emoticons": [],
        "keywords": [
            "apple",
            "fruit",
            "green"
        ],
        "name": "green apple",
        "shortcodes": [
            ":green_apple:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍐",
        "emoticons": [],
        "keywords": [
            "fruit",
            "pear"
        ],
        "name": "pear",
        "shortcodes": [
            ":pear:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍑",
        "emoticons": [],
        "keywords": [
            "fruit",
            "peach"
        ],
        "name": "peach",
        "shortcodes": [
            ":peach:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍒",
        "emoticons": [],
        "keywords": [
            "berries",
            "cherries",
            "cherry",
            "fruit",
            "red"
        ],
        "name": "cherries",
        "shortcodes": [
            ":cherries:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍓",
        "emoticons": [],
        "keywords": [
            "berry",
            "fruit",
            "strawberry"
        ],
        "name": "strawberry",
        "shortcodes": [
            ":strawberry:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥝",
        "emoticons": [],
        "keywords": [
            "food",
            "fruit",
            "kiwi fruit",
            "kiwi"
        ],
        "name": "kiwi fruit",
        "shortcodes": [
            ":kiwi_fruit:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍅",
        "emoticons": [],
        "keywords": [
            "fruit",
            "tomato",
            "vegetable"
        ],
        "name": "tomato",
        "shortcodes": [
            ":tomato:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥥",
        "emoticons": [],
        "keywords": [
            "coconut",
            "palm",
            "piña colada"
        ],
        "name": "coconut",
        "shortcodes": [
            ":coconut:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥑",
        "emoticons": [],
        "keywords": [
            "avocado",
            "food",
            "fruit"
        ],
        "name": "avocado",
        "shortcodes": [
            ":avocado:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍆",
        "emoticons": [],
        "keywords": [
            "aubergine",
            "eggplant",
            "vegetable"
        ],
        "name": "eggplant",
        "shortcodes": [
            ":eggplant:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥔",
        "emoticons": [],
        "keywords": [
            "food",
            "potato",
            "vegetable"
        ],
        "name": "potato",
        "shortcodes": [
            ":potato:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥕",
        "emoticons": [],
        "keywords": [
            "carrot",
            "food",
            "vegetable"
        ],
        "name": "carrot",
        "shortcodes": [
            ":carrot:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🌽",
        "emoticons": [],
        "keywords": [
            "corn",
            "corn on the cob",
            "sweetcorn",
            "ear",
            "ear of corn",
            "maize",
            "maze"
        ],
        "name": "ear of corn",
        "shortcodes": [
            ":ear_of_corn:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🌶️",
        "emoticons": [],
        "keywords": [
            "chilli",
            "hot pepper",
            "pepper",
            "hot"
        ],
        "name": "hot pepper",
        "shortcodes": [
            ":hot_pepper:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥒",
        "emoticons": [],
        "keywords": [
            "cucumber",
            "food",
            "pickle",
            "vegetable"
        ],
        "name": "cucumber",
        "shortcodes": [
            ":cucumber:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥬",
        "emoticons": [],
        "keywords": [
            "bok choy",
            "leafy green",
            "pak choi",
            "cabbage",
            "kale",
            "lettuce"
        ],
        "name": "leafy green",
        "shortcodes": [
            ":leafy_green:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥦",
        "emoticons": [],
        "keywords": [
            "broccoli",
            "wild cabbage"
        ],
        "name": "broccoli",
        "shortcodes": [
            ":broccoli:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧄",
        "emoticons": [],
        "keywords": [
            "flavouring",
            "garlic",
            "flavoring"
        ],
        "name": "garlic",
        "shortcodes": [
            ":garlic:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧅",
        "emoticons": [],
        "keywords": [
            "flavouring",
            "onion",
            "flavoring"
        ],
        "name": "onion",
        "shortcodes": [
            ":onion:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍄",
        "emoticons": [],
        "keywords": [
            "mushroom",
            "toadstool"
        ],
        "name": "mushroom",
        "shortcodes": [
            ":mushroom:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥜",
        "emoticons": [],
        "keywords": [
            "food",
            "nut",
            "nuts",
            "peanut",
            "peanuts",
            "vegetable"
        ],
        "name": "peanuts",
        "shortcodes": [
            ":peanuts:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🌰",
        "emoticons": [],
        "keywords": [
            "chestnut",
            "plant",
            "nut"
        ],
        "name": "chestnut",
        "shortcodes": [
            ":chestnut:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍞",
        "emoticons": [],
        "keywords": [
            "bread",
            "loaf"
        ],
        "name": "bread",
        "shortcodes": [
            ":bread:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥐",
        "emoticons": [],
        "keywords": [
            "bread",
            "breakfast",
            "croissant",
            "food",
            "french",
            "roll",
            "crescent roll",
            "French"
        ],
        "name": "croissant",
        "shortcodes": [
            ":croissant:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥖",
        "emoticons": [],
        "keywords": [
            "baguette",
            "bread",
            "food",
            "french",
            "French stick",
            "French"
        ],
        "name": "baguette bread",
        "shortcodes": [
            ":baguette_bread:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥨",
        "emoticons": [],
        "keywords": [
            "pretzel",
            "twisted"
        ],
        "name": "pretzel",
        "shortcodes": [
            ":pretzel:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥯",
        "emoticons": [],
        "keywords": [
            "bagel",
            "bakery",
            "breakfast",
            "schmear"
        ],
        "name": "bagel",
        "shortcodes": [
            ":bagel:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥞",
        "emoticons": [],
        "keywords": [
            "breakfast",
            "crêpe",
            "food",
            "hotcake",
            "pancake",
            "pancakes"
        ],
        "name": "pancakes",
        "shortcodes": [
            ":pancakes:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧇",
        "emoticons": [],
        "keywords": [
            "waffle",
            "waffle with butter",
            "breakfast",
            "indecisive",
            "iron",
            "unclear",
            "vague"
        ],
        "name": "waffle",
        "shortcodes": [
            ":waffle:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧀",
        "emoticons": [],
        "keywords": [
            "cheese",
            "cheese wedge"
        ],
        "name": "cheese wedge",
        "shortcodes": [
            ":cheese_wedge:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍖",
        "emoticons": [],
        "keywords": [
            "bone",
            "meat",
            "meat on bone"
        ],
        "name": "meat on bone",
        "shortcodes": [
            ":meat_on_bone:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍗",
        "emoticons": [],
        "keywords": [
            "bone",
            "chicken",
            "drumstick",
            "leg",
            "poultry"
        ],
        "name": "poultry leg",
        "shortcodes": [
            ":poultry_leg:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥩",
        "emoticons": [],
        "keywords": [
            "chop",
            "cut of meat",
            "lambchop",
            "porkchop",
            "steak",
            "lamb chop",
            "pork chop"
        ],
        "name": "cut of meat",
        "shortcodes": [
            ":cut_of_meat:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥓",
        "emoticons": [],
        "keywords": [
            "bacon",
            "breakfast",
            "food",
            "meat"
        ],
        "name": "bacon",
        "shortcodes": [
            ":bacon:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍔",
        "emoticons": [],
        "keywords": [
            "beefburger",
            "burger",
            "hamburger"
        ],
        "name": "hamburger",
        "shortcodes": [
            ":hamburger:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍟",
        "emoticons": [],
        "keywords": [
            "chips",
            "french fries",
            "fries",
            "french",
            "French"
        ],
        "name": "french fries",
        "shortcodes": [
            ":french_fries:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍕",
        "emoticons": [],
        "keywords": [
            "cheese",
            "pizza",
            "slice"
        ],
        "name": "pizza",
        "shortcodes": [
            ":pizza:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🌭",
        "emoticons": [],
        "keywords": [
            "frankfurter",
            "hot dog",
            "hotdog",
            "sausage"
        ],
        "name": "hot dog",
        "shortcodes": [
            ":hot_dog:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥪",
        "emoticons": [],
        "keywords": [
            "bread",
            "sandwich"
        ],
        "name": "sandwich",
        "shortcodes": [
            ":sandwich:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🌮",
        "emoticons": [],
        "keywords": [
            "mexican",
            "taco",
            "Mexican"
        ],
        "name": "taco",
        "shortcodes": [
            ":taco:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🌯",
        "emoticons": [],
        "keywords": [
            "burrito",
            "mexican",
            "wrap",
            "Mexican"
        ],
        "name": "burrito",
        "shortcodes": [
            ":burrito:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥙",
        "emoticons": [],
        "keywords": [
            "falafel",
            "flatbread",
            "food",
            "gyro",
            "kebab",
            "pita",
            "pita roll",
            "stuffed"
        ],
        "name": "stuffed flatbread",
        "shortcodes": [
            ":stuffed_flatbread:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧆",
        "emoticons": [],
        "keywords": [
            "chickpea",
            "falafel",
            "meatball",
            "chick pea"
        ],
        "name": "falafel",
        "shortcodes": [
            ":falafel:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥚",
        "emoticons": [],
        "keywords": [
            "breakfast",
            "egg",
            "food"
        ],
        "name": "egg",
        "shortcodes": [
            ":egg:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍳",
        "emoticons": [],
        "keywords": [
            "breakfast",
            "cooking",
            "egg",
            "frying",
            "pan"
        ],
        "name": "cooking",
        "shortcodes": [
            ":cooking:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥘",
        "emoticons": [],
        "keywords": [
            "casserole",
            "food",
            "paella",
            "pan",
            "shallow",
            "shallow pan of food"
        ],
        "name": "shallow pan of food",
        "shortcodes": [
            ":shallow_pan_of_food:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍲",
        "emoticons": [],
        "keywords": [
            "pot",
            "pot of food",
            "stew"
        ],
        "name": "pot of food",
        "shortcodes": [
            ":pot_of_food:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥣",
        "emoticons": [],
        "keywords": [
            "bowl with spoon",
            "breakfast",
            "cereal",
            "congee"
        ],
        "name": "bowl with spoon",
        "shortcodes": [
            ":bowl_with_spoon:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥗",
        "emoticons": [],
        "keywords": [
            "food",
            "garden",
            "salad",
            "green"
        ],
        "name": "green salad",
        "shortcodes": [
            ":green_salad:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍿",
        "emoticons": [],
        "keywords": [
            "popcorn"
        ],
        "name": "popcorn",
        "shortcodes": [
            ":popcorn:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧈",
        "emoticons": [],
        "keywords": [
            "butter",
            "dairy"
        ],
        "name": "butter",
        "shortcodes": [
            ":butter:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧂",
        "emoticons": [],
        "keywords": [
            "condiment",
            "salt",
            "shaker"
        ],
        "name": "salt",
        "shortcodes": [
            ":salt:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥫",
        "emoticons": [],
        "keywords": [
            "can",
            "canned food"
        ],
        "name": "canned food",
        "shortcodes": [
            ":canned_food:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍱",
        "emoticons": [],
        "keywords": [
            "bento",
            "box"
        ],
        "name": "bento box",
        "shortcodes": [
            ":bento_box:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍘",
        "emoticons": [],
        "keywords": [
            "cracker",
            "rice"
        ],
        "name": "rice cracker",
        "shortcodes": [
            ":rice_cracker:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍙",
        "emoticons": [],
        "keywords": [
            "ball",
            "Japanese",
            "rice"
        ],
        "name": "rice ball",
        "shortcodes": [
            ":rice_ball:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍚",
        "emoticons": [],
        "keywords": [
            "cooked",
            "rice"
        ],
        "name": "cooked rice",
        "shortcodes": [
            ":cooked_rice:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍛",
        "emoticons": [],
        "keywords": [
            "curry",
            "rice"
        ],
        "name": "curry rice",
        "shortcodes": [
            ":curry_rice:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍜",
        "emoticons": [],
        "keywords": [
            "bowl",
            "noodle",
            "ramen",
            "steaming"
        ],
        "name": "steaming bowl",
        "shortcodes": [
            ":steaming_bowl:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍝",
        "emoticons": [],
        "keywords": [
            "pasta",
            "spaghetti"
        ],
        "name": "spaghetti",
        "shortcodes": [
            ":spaghetti:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍠",
        "emoticons": [],
        "keywords": [
            "potato",
            "roasted",
            "sweet"
        ],
        "name": "roasted sweet potato",
        "shortcodes": [
            ":roasted_sweet_potato:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍢",
        "emoticons": [],
        "keywords": [
            "kebab",
            "oden",
            "seafood",
            "skewer",
            "stick"
        ],
        "name": "oden",
        "shortcodes": [
            ":oden:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍣",
        "emoticons": [],
        "keywords": [
            "sushi"
        ],
        "name": "sushi",
        "shortcodes": [
            ":sushi:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍤",
        "emoticons": [],
        "keywords": [
            "battered",
            "fried",
            "prawn",
            "shrimp",
            "tempura"
        ],
        "name": "fried shrimp",
        "shortcodes": [
            ":fried_shrimp:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍥",
        "emoticons": [],
        "keywords": [
            "cake",
            "fish",
            "fish cake with swirl",
            "pastry",
            "swirl",
            "narutomaki"
        ],
        "name": "fish cake with swirl",
        "shortcodes": [
            ":fish_cake_with_swirl:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥮",
        "emoticons": [],
        "keywords": [
            "autumn",
            "festival",
            "moon cake",
            "yuèbǐng"
        ],
        "name": "moon cake",
        "shortcodes": [
            ":moon_cake:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍡",
        "emoticons": [],
        "keywords": [
            "dango",
            "dessert",
            "Japanese",
            "skewer",
            "stick",
            "sweet"
        ],
        "name": "dango",
        "shortcodes": [
            ":dango:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥟",
        "emoticons": [],
        "keywords": [
            "dumpling",
            "empanada",
            "gyōza",
            "pastie",
            "samosa",
            "jiaozi",
            "pierogi",
            "potsticker"
        ],
        "name": "dumpling",
        "shortcodes": [
            ":dumpling:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥠",
        "emoticons": [],
        "keywords": [
            "fortune cookie",
            "prophecy"
        ],
        "name": "fortune cookie",
        "shortcodes": [
            ":fortune_cookie:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥡",
        "emoticons": [],
        "keywords": [
            "takeaway container",
            "takeout",
            "oyster pail",
            "takeout box",
            "takeaway box"
        ],
        "name": "takeout box",
        "shortcodes": [
            ":takeout_box:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🦀",
        "emoticons": [],
        "keywords": [
            "crab",
            "crustacean",
            "seafood",
            "shellfish",
            "Cancer",
            "zodiac"
        ],
        "name": "crab",
        "shortcodes": [
            ":crab:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🦞",
        "emoticons": [],
        "keywords": [
            "bisque",
            "claws",
            "lobster",
            "seafood",
            "shellfish"
        ],
        "name": "lobster",
        "shortcodes": [
            ":lobster:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🦐",
        "emoticons": [],
        "keywords": [
            "prawn",
            "seafood",
            "shellfish",
            "shrimp",
            "food",
            "small"
        ],
        "name": "shrimp",
        "shortcodes": [
            ":shrimp:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🦑",
        "emoticons": [],
        "keywords": [
            "decapod",
            "seafood",
            "squid",
            "food",
            "molusc"
        ],
        "name": "squid",
        "shortcodes": [
            ":squid:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🦪",
        "emoticons": [],
        "keywords": [
            "diving",
            "oyster",
            "pearl"
        ],
        "name": "oyster",
        "shortcodes": [
            ":oyster:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍦",
        "emoticons": [],
        "keywords": [
            "cream",
            "dessert",
            "ice cream",
            "soft serve",
            "sweet",
            "ice",
            "icecream",
            "soft"
        ],
        "name": "soft ice cream",
        "shortcodes": [
            ":soft_ice_cream:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍧",
        "emoticons": [],
        "keywords": [
            "dessert",
            "granita",
            "ice",
            "sweet",
            "shaved"
        ],
        "name": "shaved ice",
        "shortcodes": [
            ":shaved_ice:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍨",
        "emoticons": [],
        "keywords": [
            "cream",
            "dessert",
            "ice cream",
            "sweet",
            "ice"
        ],
        "name": "ice cream",
        "shortcodes": [
            ":ice_cream:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍩",
        "emoticons": [],
        "keywords": [
            "breakfast",
            "dessert",
            "donut",
            "doughnut",
            "sweet"
        ],
        "name": "doughnut",
        "shortcodes": [
            ":doughnut:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍪",
        "emoticons": [],
        "keywords": [
            "biscuit",
            "cookie",
            "dessert",
            "sweet"
        ],
        "name": "cookie",
        "shortcodes": [
            ":cookie:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🎂",
        "emoticons": [],
        "keywords": [
            "birthday",
            "cake",
            "celebration",
            "dessert",
            "pastry",
            "sweet"
        ],
        "name": "birthday cake",
        "shortcodes": [
            ":birthday_cake:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍰",
        "emoticons": [],
        "keywords": [
            "cake",
            "dessert",
            "pastry",
            "shortcake",
            "slice",
            "sweet"
        ],
        "name": "shortcake",
        "shortcodes": [
            ":shortcake:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧁",
        "emoticons": [],
        "keywords": [
            "bakery",
            "cupcake",
            "sweet"
        ],
        "name": "cupcake",
        "shortcodes": [
            ":cupcake:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥧",
        "emoticons": [],
        "keywords": [
            "filling",
            "pastry",
            "pie"
        ],
        "name": "pie",
        "shortcodes": [
            ":pie:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍫",
        "emoticons": [],
        "keywords": [
            "bar",
            "chocolate",
            "dessert",
            "sweet"
        ],
        "name": "chocolate bar",
        "shortcodes": [
            ":chocolate_bar:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍬",
        "emoticons": [],
        "keywords": [
            "candy",
            "dessert",
            "sweet",
            "sweets"
        ],
        "name": "candy",
        "shortcodes": [
            ":candy:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍭",
        "emoticons": [],
        "keywords": [
            "candy",
            "dessert",
            "lollipop",
            "sweet"
        ],
        "name": "lollipop",
        "shortcodes": [
            ":lollipop:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍮",
        "emoticons": [],
        "keywords": [
            "baked custard",
            "dessert",
            "pudding",
            "sweet",
            "custard"
        ],
        "name": "custard",
        "shortcodes": [
            ":custard:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍯",
        "emoticons": [],
        "keywords": [
            "honey",
            "honeypot",
            "pot",
            "sweet"
        ],
        "name": "honey pot",
        "shortcodes": [
            ":honey_pot:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍼",
        "emoticons": [],
        "keywords": [
            "baby",
            "bottle",
            "drink",
            "milk"
        ],
        "name": "baby bottle",
        "shortcodes": [
            ":baby_bottle:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥛",
        "emoticons": [],
        "keywords": [
            "drink",
            "glass",
            "glass of milk",
            "milk"
        ],
        "name": "glass of milk",
        "shortcodes": [
            ":glass_of_milk:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "☕",
        "emoticons": [],
        "keywords": [
            "beverage",
            "coffee",
            "drink",
            "hot",
            "steaming",
            "tea"
        ],
        "name": "hot beverage",
        "shortcodes": [
            ":hot_beverage:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍵",
        "emoticons": [],
        "keywords": [
            "beverage",
            "cup",
            "drink",
            "tea",
            "teacup",
            "teacup without handle"
        ],
        "name": "teacup without handle",
        "shortcodes": [
            ":teacup_without_handle:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍶",
        "emoticons": [],
        "keywords": [
            "bar",
            "beverage",
            "bottle",
            "cup",
            "drink",
            "sake",
            "saké"
        ],
        "name": "sake",
        "shortcodes": [
            ":sake:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍾",
        "emoticons": [],
        "keywords": [
            "bar",
            "bottle",
            "bottle with popping cork",
            "cork",
            "drink",
            "popping"
        ],
        "name": "bottle with popping cork",
        "shortcodes": [
            ":bottle_with_popping_cork:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍷",
        "emoticons": [],
        "keywords": [
            "bar",
            "beverage",
            "drink",
            "glass",
            "wine"
        ],
        "name": "wine glass",
        "shortcodes": [
            ":wine_glass:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍸",
        "emoticons": [],
        "keywords": [
            "bar",
            "cocktail",
            "drink",
            "glass"
        ],
        "name": "cocktail glass",
        "shortcodes": [
            ":cocktail_glass:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍹",
        "emoticons": [],
        "keywords": [
            "bar",
            "drink",
            "tropical"
        ],
        "name": "tropical drink",
        "shortcodes": [
            ":tropical_drink:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍺",
        "emoticons": [],
        "keywords": [
            "bar",
            "beer",
            "drink",
            "mug"
        ],
        "name": "beer mug",
        "shortcodes": [
            ":beer_mug:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍻",
        "emoticons": [],
        "keywords": [
            "bar",
            "beer",
            "clink",
            "clinking beer mugs",
            "drink",
            "mug"
        ],
        "name": "clinking beer mugs",
        "shortcodes": [
            ":clinking_beer_mugs:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥂",
        "emoticons": [],
        "keywords": [
            "celebrate",
            "clink",
            "clinking glasses",
            "drink",
            "glass"
        ],
        "name": "clinking glasses",
        "shortcodes": [
            ":clinking_glasses:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥃",
        "emoticons": [],
        "keywords": [
            "glass",
            "liquor",
            "shot",
            "tumbler",
            "whisky"
        ],
        "name": "tumbler glass",
        "shortcodes": [
            ":tumbler_glass:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥤",
        "emoticons": [],
        "keywords": [
            "cup with straw",
            "juice",
            "soda"
        ],
        "name": "cup with straw",
        "shortcodes": [
            ":cup_with_straw:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧃",
        "emoticons": [],
        "keywords": [
            "drink carton",
            "juice box",
            "popper",
            "beverage",
            "box",
            "juice",
            "straw",
            "sweet"
        ],
        "name": "beverage box",
        "shortcodes": [
            ":beverage_box:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧉",
        "emoticons": [],
        "keywords": [
            "drink",
            "mate",
            "maté"
        ],
        "name": "mate",
        "shortcodes": [
            ":mate:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🧊",
        "emoticons": [],
        "keywords": [
            "cold",
            "ice",
            "ice cube",
            "iceberg"
        ],
        "name": "ice",
        "shortcodes": [
            ":ice:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥢",
        "emoticons": [],
        "keywords": [
            "chopsticks",
            "pair of chopsticks",
            "hashi"
        ],
        "name": "chopsticks",
        "shortcodes": [
            ":chopsticks:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍽️",
        "emoticons": [],
        "keywords": [
            "cooking",
            "fork",
            "fork and knife with plate",
            "knife",
            "plate"
        ],
        "name": "fork and knife with plate",
        "shortcodes": [
            ":fork_and_knife_with_plate:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🍴",
        "emoticons": [],
        "keywords": [
            "cooking",
            "cutlery",
            "fork",
            "fork and knife",
            "knife",
            "knife and fork"
        ],
        "name": "fork and knife",
        "shortcodes": [
            ":fork_and_knife:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🥄",
        "emoticons": [],
        "keywords": [
            "spoon",
            "tableware"
        ],
        "name": "spoon",
        "shortcodes": [
            ":spoon:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🔪",
        "emoticons": [],
        "keywords": [
            "cooking",
            "hocho",
            "kitchen knife",
            "knife",
            "tool",
            "weapon"
        ],
        "name": "kitchen knife",
        "shortcodes": [
            ":kitchen_knife:"
        ]
    },
    {
        "category": "Food & Drink",
        "codepoints": "🏺",
        "emoticons": [],
        "keywords": [
            "amphora",
            "Aquarius",
            "cooking",
            "drink",
            "jug",
            "zodiac",
            "jar"
        ],
        "name": "amphora",
        "shortcodes": [
            ":amphora:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌍",
        "emoticons": [],
        "keywords": [
            "Africa",
            "earth",
            "Europe",
            "globe",
            "globe showing Europe-Africa",
            "world"
        ],
        "name": "globe showing Europe-Africa",
        "shortcodes": [
            ":globe_showing_Europe-Africa:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌎",
        "emoticons": [],
        "keywords": [
            "Americas",
            "earth",
            "globe",
            "globe showing Americas",
            "world"
        ],
        "name": "globe showing Americas",
        "shortcodes": [
            ":globe_showing_Americas:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌏",
        "emoticons": [],
        "keywords": [
            "Asia",
            "Australia",
            "earth",
            "globe",
            "globe showing Asia-Australia",
            "world"
        ],
        "name": "globe showing Asia-Australia",
        "shortcodes": [
            ":globe_showing_Asia-Australia:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌐",
        "emoticons": [],
        "keywords": [
            "earth",
            "globe",
            "globe with meridians",
            "meridians",
            "world"
        ],
        "name": "globe with meridians",
        "shortcodes": [
            ":globe_with_meridians:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🗺️",
        "emoticons": [],
        "keywords": [
            "map",
            "world"
        ],
        "name": "world map",
        "shortcodes": [
            ":world_map:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🗾",
        "emoticons": [],
        "keywords": [
            "Japan",
            "map",
            "map of Japan"
        ],
        "name": "map of Japan",
        "shortcodes": [
            ":map_of_Japan:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🧭",
        "emoticons": [],
        "keywords": [
            "compass",
            "magnetic",
            "navigation",
            "orienteering"
        ],
        "name": "compass",
        "shortcodes": [
            ":compass:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏔️",
        "emoticons": [],
        "keywords": [
            "cold",
            "mountain",
            "snow",
            "snow-capped mountain"
        ],
        "name": "snow-capped mountain",
        "shortcodes": [
            ":snow-capped_mountain:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛰️",
        "emoticons": [],
        "keywords": [
            "mountain"
        ],
        "name": "mountain",
        "shortcodes": [
            ":mountain:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌋",
        "emoticons": [],
        "keywords": [
            "eruption",
            "mountain",
            "volcano"
        ],
        "name": "volcano",
        "shortcodes": [
            ":volcano:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🗻",
        "emoticons": [],
        "keywords": [
            "Fuji",
            "mount Fuji",
            "mountain",
            "fuji",
            "mount fuji",
            "Mount Fuji"
        ],
        "name": "mount fuji",
        "shortcodes": [
            ":mount_fuji:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏕️",
        "emoticons": [],
        "keywords": [
            "camping"
        ],
        "name": "camping",
        "shortcodes": [
            ":camping:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏖️",
        "emoticons": [],
        "keywords": [
            "beach",
            "beach with umbrella",
            "umbrella"
        ],
        "name": "beach with umbrella",
        "shortcodes": [
            ":beach_with_umbrella:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏜️",
        "emoticons": [],
        "keywords": [
            "desert"
        ],
        "name": "desert",
        "shortcodes": [
            ":desert:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏝️",
        "emoticons": [],
        "keywords": [
            "desert",
            "island"
        ],
        "name": "desert island",
        "shortcodes": [
            ":desert_island:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏞️",
        "emoticons": [],
        "keywords": [
            "national park",
            "park"
        ],
        "name": "national park",
        "shortcodes": [
            ":national_park:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏟️",
        "emoticons": [],
        "keywords": [
            "arena",
            "stadium"
        ],
        "name": "stadium",
        "shortcodes": [
            ":stadium:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏛️",
        "emoticons": [],
        "keywords": [
            "classical",
            "classical building",
            "column"
        ],
        "name": "classical building",
        "shortcodes": [
            ":classical_building:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏗️",
        "emoticons": [],
        "keywords": [
            "building construction",
            "construction"
        ],
        "name": "building construction",
        "shortcodes": [
            ":building_construction:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🧱",
        "emoticons": [],
        "keywords": [
            "brick",
            "bricks",
            "clay",
            "mortar",
            "wall"
        ],
        "name": "brick",
        "shortcodes": [
            ":brick:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏘️",
        "emoticons": [],
        "keywords": [
            "houses"
        ],
        "name": "houses",
        "shortcodes": [
            ":houses:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏚️",
        "emoticons": [],
        "keywords": [
            "derelict",
            "house"
        ],
        "name": "derelict house",
        "shortcodes": [
            ":derelict_house:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏠",
        "emoticons": [],
        "keywords": [
            "home",
            "house"
        ],
        "name": "house",
        "shortcodes": [
            ":house:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏡",
        "emoticons": [],
        "keywords": [
            "garden",
            "home",
            "house",
            "house with garden"
        ],
        "name": "house with garden",
        "shortcodes": [
            ":house_with_garden:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏢",
        "emoticons": [],
        "keywords": [
            "building",
            "office building"
        ],
        "name": "office building",
        "shortcodes": [
            ":office_building:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏣",
        "emoticons": [],
        "keywords": [
            "Japanese",
            "Japanese post office",
            "post"
        ],
        "name": "Japanese post office",
        "shortcodes": [
            ":Japanese_post_office:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏤",
        "emoticons": [],
        "keywords": [
            "European",
            "post",
            "post office"
        ],
        "name": "post office",
        "shortcodes": [
            ":post_office:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏥",
        "emoticons": [],
        "keywords": [
            "doctor",
            "hospital",
            "medicine"
        ],
        "name": "hospital",
        "shortcodes": [
            ":hospital:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏦",
        "emoticons": [],
        "keywords": [
            "bank",
            "building"
        ],
        "name": "bank",
        "shortcodes": [
            ":bank:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏨",
        "emoticons": [],
        "keywords": [
            "building",
            "hotel"
        ],
        "name": "hotel",
        "shortcodes": [
            ":hotel:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏩",
        "emoticons": [],
        "keywords": [
            "hotel",
            "love"
        ],
        "name": "love hotel",
        "shortcodes": [
            ":love_hotel:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏪",
        "emoticons": [],
        "keywords": [
            "convenience",
            "store",
            "dépanneur"
        ],
        "name": "convenience store",
        "shortcodes": [
            ":convenience_store:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏫",
        "emoticons": [],
        "keywords": [
            "building",
            "school"
        ],
        "name": "school",
        "shortcodes": [
            ":school:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏬",
        "emoticons": [],
        "keywords": [
            "department",
            "store"
        ],
        "name": "department store",
        "shortcodes": [
            ":department_store:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏭",
        "emoticons": [],
        "keywords": [
            "building",
            "factory"
        ],
        "name": "factory",
        "shortcodes": [
            ":factory:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏯",
        "emoticons": [],
        "keywords": [
            "castle",
            "Japanese"
        ],
        "name": "Japanese castle",
        "shortcodes": [
            ":Japanese_castle:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏰",
        "emoticons": [],
        "keywords": [
            "castle",
            "European"
        ],
        "name": "castle",
        "shortcodes": [
            ":castle:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "💒",
        "emoticons": [],
        "keywords": [
            "chapel",
            "romance",
            "wedding"
        ],
        "name": "wedding",
        "shortcodes": [
            ":wedding:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🗼",
        "emoticons": [],
        "keywords": [
            "Tokyo",
            "tower",
            "Tower"
        ],
        "name": "Tokyo tower",
        "shortcodes": [
            ":Tokyo_tower:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🗽",
        "emoticons": [],
        "keywords": [
            "liberty",
            "statue",
            "Statue of Liberty",
            "Liberty",
            "Statue"
        ],
        "name": "Statue of Liberty",
        "shortcodes": [
            ":Statue_of_Liberty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛪",
        "emoticons": [],
        "keywords": [
            "Christian",
            "church",
            "cross",
            "religion"
        ],
        "name": "church",
        "shortcodes": [
            ":church:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕌",
        "emoticons": [],
        "keywords": [
            "Islam",
            "mosque",
            "Muslim",
            "religion",
            "islam"
        ],
        "name": "mosque",
        "shortcodes": [
            ":mosque:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛕",
        "emoticons": [],
        "keywords": [
            "hindu",
            "temple",
            "Hindu"
        ],
        "name": "hindu temple",
        "shortcodes": [
            ":hindu_temple:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕍",
        "emoticons": [],
        "keywords": [
            "Jew",
            "Jewish",
            "religion",
            "synagogue",
            "temple",
            "shul"
        ],
        "name": "synagogue",
        "shortcodes": [
            ":synagogue:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛩️",
        "emoticons": [],
        "keywords": [
            "religion",
            "Shinto",
            "shrine",
            "shinto"
        ],
        "name": "shinto shrine",
        "shortcodes": [
            ":shinto_shrine:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕋",
        "emoticons": [],
        "keywords": [
            "Islam",
            "Kaaba",
            "Muslim",
            "religion",
            "islam",
            "kaaba"
        ],
        "name": "kaaba",
        "shortcodes": [
            ":kaaba:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛲",
        "emoticons": [],
        "keywords": [
            "fountain"
        ],
        "name": "fountain",
        "shortcodes": [
            ":fountain:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛺",
        "emoticons": [],
        "keywords": [
            "camping",
            "tent"
        ],
        "name": "tent",
        "shortcodes": [
            ":tent:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌁",
        "emoticons": [],
        "keywords": [
            "fog",
            "foggy"
        ],
        "name": "foggy",
        "shortcodes": [
            ":foggy:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌃",
        "emoticons": [],
        "keywords": [
            "night",
            "night with stars",
            "star"
        ],
        "name": "night with stars",
        "shortcodes": [
            ":night_with_stars:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏙️",
        "emoticons": [],
        "keywords": [
            "city",
            "cityscape"
        ],
        "name": "cityscape",
        "shortcodes": [
            ":cityscape:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌄",
        "emoticons": [],
        "keywords": [
            "morning",
            "mountain",
            "sun",
            "sunrise",
            "sunrise over mountains"
        ],
        "name": "sunrise over mountains",
        "shortcodes": [
            ":sunrise_over_mountains:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌅",
        "emoticons": [],
        "keywords": [
            "morning",
            "sun",
            "sunrise"
        ],
        "name": "sunrise",
        "shortcodes": [
            ":sunrise:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌆",
        "emoticons": [],
        "keywords": [
            "city",
            "cityscape at dusk",
            "dusk",
            "evening",
            "landscape",
            "sunset"
        ],
        "name": "cityscape at dusk",
        "shortcodes": [
            ":cityscape_at_dusk:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌇",
        "emoticons": [],
        "keywords": [
            "dusk",
            "sun",
            "sunset"
        ],
        "name": "sunset",
        "shortcodes": [
            ":sunset:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌉",
        "emoticons": [],
        "keywords": [
            "bridge",
            "bridge at night",
            "night"
        ],
        "name": "bridge at night",
        "shortcodes": [
            ":bridge_at_night:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "♨️",
        "emoticons": [],
        "keywords": [
            "hot",
            "hotsprings",
            "springs",
            "steaming"
        ],
        "name": "hot springs",
        "shortcodes": [
            ":hot_springs:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🎠",
        "emoticons": [],
        "keywords": [
            "carousel",
            "horse",
            "merry-go-round"
        ],
        "name": "carousel horse",
        "shortcodes": [
            ":carousel_horse:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🎡",
        "emoticons": [],
        "keywords": [
            "amusement park",
            "ferris",
            "wheel",
            "Ferris",
            "theme park"
        ],
        "name": "ferris wheel",
        "shortcodes": [
            ":ferris_wheel:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🎢",
        "emoticons": [],
        "keywords": [
            "amusement park",
            "coaster",
            "roller"
        ],
        "name": "roller coaster",
        "shortcodes": [
            ":roller_coaster:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "💈",
        "emoticons": [],
        "keywords": [
            "barber",
            "haircut",
            "pole"
        ],
        "name": "barber pole",
        "shortcodes": [
            ":barber_pole:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🎪",
        "emoticons": [],
        "keywords": [
            "big top",
            "circus",
            "tent"
        ],
        "name": "circus tent",
        "shortcodes": [
            ":circus_tent:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚂",
        "emoticons": [],
        "keywords": [
            "engine",
            "locomotive",
            "railway",
            "steam",
            "train"
        ],
        "name": "locomotive",
        "shortcodes": [
            ":locomotive:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚃",
        "emoticons": [],
        "keywords": [
            "car",
            "electric",
            "railway",
            "train",
            "tram",
            "trolley bus",
            "trolleybus",
            "railway carriage"
        ],
        "name": "railway car",
        "shortcodes": [
            ":railway_car:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚄",
        "emoticons": [],
        "keywords": [
            "high-speed train",
            "railway",
            "shinkansen",
            "speed",
            "train",
            "Shinkansen"
        ],
        "name": "high-speed train",
        "shortcodes": [
            ":high-speed_train:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚅",
        "emoticons": [],
        "keywords": [
            "bullet",
            "railway",
            "shinkansen",
            "speed",
            "train",
            "Shinkansen"
        ],
        "name": "bullet train",
        "shortcodes": [
            ":bullet_train:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚆",
        "emoticons": [],
        "keywords": [
            "railway",
            "train"
        ],
        "name": "train",
        "shortcodes": [
            ":train:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚇",
        "emoticons": [],
        "keywords": [
            "metro",
            "subway"
        ],
        "name": "metro",
        "shortcodes": [
            ":metro:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚈",
        "emoticons": [],
        "keywords": [
            "light rail",
            "railway"
        ],
        "name": "light rail",
        "shortcodes": [
            ":light_rail:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚉",
        "emoticons": [],
        "keywords": [
            "railway",
            "station",
            "train"
        ],
        "name": "station",
        "shortcodes": [
            ":station:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚊",
        "emoticons": [],
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
        ],
        "name": "tram",
        "shortcodes": [
            ":tram:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚝",
        "emoticons": [],
        "keywords": [
            "monorail",
            "vehicle"
        ],
        "name": "monorail",
        "shortcodes": [
            ":monorail:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚞",
        "emoticons": [],
        "keywords": [
            "car",
            "mountain",
            "railway"
        ],
        "name": "mountain railway",
        "shortcodes": [
            ":mountain_railway:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚋",
        "emoticons": [],
        "keywords": [
            "car",
            "tram",
            "trolley bus",
            "trolleybus",
            "streetcar",
            "tramcar",
            "trolley"
        ],
        "name": "tram car",
        "shortcodes": [
            ":tram_car:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚌",
        "emoticons": [],
        "keywords": [
            "bus",
            "vehicle"
        ],
        "name": "bus",
        "shortcodes": [
            ":bus:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚍",
        "emoticons": [],
        "keywords": [
            "bus",
            "oncoming"
        ],
        "name": "oncoming bus",
        "shortcodes": [
            ":oncoming_bus:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚎",
        "emoticons": [],
        "keywords": [
            "bus",
            "tram",
            "trolley",
            "trolleybus",
            "streetcar"
        ],
        "name": "trolleybus",
        "shortcodes": [
            ":trolleybus:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚐",
        "emoticons": [],
        "keywords": [
            "bus",
            "minibus"
        ],
        "name": "minibus",
        "shortcodes": [
            ":minibus:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚑",
        "emoticons": [],
        "keywords": [
            "ambulance",
            "vehicle"
        ],
        "name": "ambulance",
        "shortcodes": [
            ":ambulance:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚒",
        "emoticons": [],
        "keywords": [
            "engine",
            "fire",
            "truck"
        ],
        "name": "fire engine",
        "shortcodes": [
            ":fire_engine:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚓",
        "emoticons": [],
        "keywords": [
            "car",
            "patrol",
            "police"
        ],
        "name": "police car",
        "shortcodes": [
            ":police_car:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚔",
        "emoticons": [],
        "keywords": [
            "car",
            "oncoming",
            "police"
        ],
        "name": "oncoming police car",
        "shortcodes": [
            ":oncoming_police_car:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚕",
        "emoticons": [],
        "keywords": [
            "taxi",
            "vehicle"
        ],
        "name": "taxi",
        "shortcodes": [
            ":taxi:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚖",
        "emoticons": [],
        "keywords": [
            "oncoming",
            "taxi"
        ],
        "name": "oncoming taxi",
        "shortcodes": [
            ":oncoming_taxi:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚗",
        "emoticons": [],
        "keywords": [
            "automobile",
            "car"
        ],
        "name": "automobile",
        "shortcodes": [
            ":automobile:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚘",
        "emoticons": [],
        "keywords": [
            "automobile",
            "car",
            "oncoming"
        ],
        "name": "oncoming automobile",
        "shortcodes": [
            ":oncoming_automobile:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚙",
        "emoticons": [],
        "keywords": [
            "4WD",
            "four-wheel drive",
            "recreational",
            "sport utility",
            "sport utility vehicle",
            "4x4",
            "off-road vehicle",
            "SUV"
        ],
        "name": "sport utility vehicle",
        "shortcodes": [
            ":sport_utility_vehicle:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚚",
        "emoticons": [],
        "keywords": [
            "delivery",
            "truck"
        ],
        "name": "delivery truck",
        "shortcodes": [
            ":delivery_truck:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚛",
        "emoticons": [],
        "keywords": [
            "articulated truck",
            "lorry",
            "semi",
            "truck",
            "articulated lorry"
        ],
        "name": "articulated lorry",
        "shortcodes": [
            ":articulated_lorry:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚜",
        "emoticons": [],
        "keywords": [
            "tractor",
            "vehicle"
        ],
        "name": "tractor",
        "shortcodes": [
            ":tractor:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏎️",
        "emoticons": [],
        "keywords": [
            "car",
            "racing"
        ],
        "name": "racing car",
        "shortcodes": [
            ":racing_car:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🏍️",
        "emoticons": [],
        "keywords": [
            "motorcycle",
            "racing"
        ],
        "name": "motorcycle",
        "shortcodes": [
            ":motorcycle:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛵",
        "emoticons": [],
        "keywords": [
            "motor",
            "scooter"
        ],
        "name": "motor scooter",
        "shortcodes": [
            ":motor_scooter:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🦽",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "manual wheelchair"
        ],
        "name": "manual wheelchair",
        "shortcodes": [
            ":manual_wheelchair:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🦼",
        "emoticons": [],
        "keywords": [
            "mobility scooter",
            "accessibility",
            "motorized wheelchair",
            "powered wheelchair"
        ],
        "name": "motorized wheelchair",
        "shortcodes": [
            ":motorized_wheelchair:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛺",
        "emoticons": [],
        "keywords": [
            "auto rickshaw",
            "tuk tuk",
            "tuk-tuk",
            "tuktuk"
        ],
        "name": "auto rickshaw",
        "shortcodes": [
            ":auto_rickshaw:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚲",
        "emoticons": [],
        "keywords": [
            "bicycle",
            "bike"
        ],
        "name": "bicycle",
        "shortcodes": [
            ":bicycle:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛴",
        "emoticons": [],
        "keywords": [
            "kick",
            "scooter"
        ],
        "name": "kick scooter",
        "shortcodes": [
            ":kick_scooter:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛹",
        "emoticons": [],
        "keywords": [
            "board",
            "skateboard"
        ],
        "name": "skateboard",
        "shortcodes": [
            ":skateboard:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚏",
        "emoticons": [],
        "keywords": [
            "bus",
            "stop",
            "busstop"
        ],
        "name": "bus stop",
        "shortcodes": [
            ":bus_stop:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛣️",
        "emoticons": [],
        "keywords": [
            "freeway",
            "highway",
            "road",
            "motorway"
        ],
        "name": "motorway",
        "shortcodes": [
            ":motorway:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛤️",
        "emoticons": [],
        "keywords": [
            "railway",
            "railway track",
            "train"
        ],
        "name": "railway track",
        "shortcodes": [
            ":railway_track:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛢️",
        "emoticons": [],
        "keywords": [
            "drum",
            "oil"
        ],
        "name": "oil drum",
        "shortcodes": [
            ":oil_drum:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛽",
        "emoticons": [],
        "keywords": [
            "diesel",
            "fuel",
            "gas",
            "petrol pump",
            "pump",
            "station",
            "fuelpump"
        ],
        "name": "fuel pump",
        "shortcodes": [
            ":fuel_pump:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚨",
        "emoticons": [],
        "keywords": [
            "beacon",
            "car",
            "light",
            "police",
            "revolving"
        ],
        "name": "police car light",
        "shortcodes": [
            ":police_car_light:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚥",
        "emoticons": [],
        "keywords": [
            "horizontal traffic lights",
            "lights",
            "signal",
            "traffic",
            "horizontal traffic light",
            "light"
        ],
        "name": "horizontal traffic light",
        "shortcodes": [
            ":horizontal_traffic_light:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚦",
        "emoticons": [],
        "keywords": [
            "lights",
            "signal",
            "traffic",
            "vertical traffic lights",
            "light",
            "vertical traffic light"
        ],
        "name": "vertical traffic light",
        "shortcodes": [
            ":vertical_traffic_light:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛑",
        "emoticons": [],
        "keywords": [
            "octagonal",
            "sign",
            "stop"
        ],
        "name": "stop sign",
        "shortcodes": [
            ":stop_sign:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚧",
        "emoticons": [],
        "keywords": [
            "barrier",
            "construction"
        ],
        "name": "construction",
        "shortcodes": [
            ":construction:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⚓",
        "emoticons": [],
        "keywords": [
            "anchor",
            "ship",
            "tool"
        ],
        "name": "anchor",
        "shortcodes": [
            ":anchor:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛵",
        "emoticons": [],
        "keywords": [
            "boat",
            "resort",
            "sailboat",
            "sea",
            "yacht"
        ],
        "name": "sailboat",
        "shortcodes": [
            ":sailboat:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛶",
        "emoticons": [],
        "keywords": [
            "boat",
            "canoe"
        ],
        "name": "canoe",
        "shortcodes": [
            ":canoe:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚤",
        "emoticons": [],
        "keywords": [
            "boat",
            "speedboat"
        ],
        "name": "speedboat",
        "shortcodes": [
            ":speedboat:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛳️",
        "emoticons": [],
        "keywords": [
            "passenger",
            "ship"
        ],
        "name": "passenger ship",
        "shortcodes": [
            ":passenger_ship:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛴️",
        "emoticons": [],
        "keywords": [
            "boat",
            "ferry",
            "passenger"
        ],
        "name": "ferry",
        "shortcodes": [
            ":ferry:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛥️",
        "emoticons": [],
        "keywords": [
            "boat",
            "motor boat",
            "motorboat"
        ],
        "name": "motor boat",
        "shortcodes": [
            ":motor_boat:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚢",
        "emoticons": [],
        "keywords": [
            "boat",
            "passenger",
            "ship"
        ],
        "name": "ship",
        "shortcodes": [
            ":ship:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "✈️",
        "emoticons": [],
        "keywords": [
            "aeroplane",
            "airplane"
        ],
        "name": "airplane",
        "shortcodes": [
            ":airplane:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛩️",
        "emoticons": [],
        "keywords": [
            "aeroplane",
            "airplane",
            "small airplane"
        ],
        "name": "small airplane",
        "shortcodes": [
            ":small_airplane:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛫",
        "emoticons": [],
        "keywords": [
            "aeroplane",
            "airplane",
            "check-in",
            "departure",
            "departures",
            "take-off"
        ],
        "name": "airplane departure",
        "shortcodes": [
            ":airplane_departure:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛬",
        "emoticons": [],
        "keywords": [
            "aeroplane",
            "airplane",
            "airplane arrival",
            "arrivals",
            "arriving",
            "landing"
        ],
        "name": "airplane arrival",
        "shortcodes": [
            ":airplane_arrival:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🪂",
        "emoticons": [],
        "keywords": [
            "hang-glide",
            "parachute",
            "parasail",
            "skydive",
            "parascend"
        ],
        "name": "parachute",
        "shortcodes": [
            ":parachute:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "💺",
        "emoticons": [],
        "keywords": [
            "chair",
            "seat"
        ],
        "name": "seat",
        "shortcodes": [
            ":seat:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚁",
        "emoticons": [],
        "keywords": [
            "helicopter",
            "vehicle"
        ],
        "name": "helicopter",
        "shortcodes": [
            ":helicopter:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚟",
        "emoticons": [],
        "keywords": [
            "cable",
            "railway",
            "suspension"
        ],
        "name": "suspension railway",
        "shortcodes": [
            ":suspension_railway:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚠",
        "emoticons": [],
        "keywords": [
            "cable",
            "cableway",
            "gondola",
            "mountain",
            "mountain cableway"
        ],
        "name": "mountain cableway",
        "shortcodes": [
            ":mountain_cableway:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚡",
        "emoticons": [],
        "keywords": [
            "aerial",
            "cable",
            "car",
            "gondola",
            "tramway"
        ],
        "name": "aerial tramway",
        "shortcodes": [
            ":aerial_tramway:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛰️",
        "emoticons": [],
        "keywords": [
            "satellite",
            "space"
        ],
        "name": "satellite",
        "shortcodes": [
            ":satellite:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🚀",
        "emoticons": [],
        "keywords": [
            "rocket",
            "space"
        ],
        "name": "rocket",
        "shortcodes": [
            ":rocket:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛸",
        "emoticons": [],
        "keywords": [
            "flying saucer",
            "UFO"
        ],
        "name": "flying saucer",
        "shortcodes": [
            ":flying_saucer:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🛎️",
        "emoticons": [],
        "keywords": [
            "bell",
            "hotel",
            "porter",
            "bellhop"
        ],
        "name": "bellhop bell",
        "shortcodes": [
            ":bellhop_bell:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🧳",
        "emoticons": [],
        "keywords": [
            "luggage",
            "packing",
            "travel"
        ],
        "name": "luggage",
        "shortcodes": [
            ":luggage:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⌛",
        "emoticons": [],
        "keywords": [
            "hourglass",
            "hourglass done",
            "sand",
            "timer"
        ],
        "name": "hourglass done",
        "shortcodes": [
            ":hourglass_done:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⏳",
        "emoticons": [],
        "keywords": [
            "hourglass",
            "hourglass not done",
            "sand",
            "timer"
        ],
        "name": "hourglass not done",
        "shortcodes": [
            ":hourglass_not_done:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⌚",
        "emoticons": [],
        "keywords": [
            "clock",
            "watch"
        ],
        "name": "watch",
        "shortcodes": [
            ":watch:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⏰",
        "emoticons": [],
        "keywords": [
            "alarm",
            "clock"
        ],
        "name": "alarm clock",
        "shortcodes": [
            ":alarm_clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⏱️",
        "emoticons": [],
        "keywords": [
            "clock",
            "stopwatch"
        ],
        "name": "stopwatch",
        "shortcodes": [
            ":stopwatch:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⏲️",
        "emoticons": [],
        "keywords": [
            "clock",
            "timer"
        ],
        "name": "timer clock",
        "shortcodes": [
            ":timer_clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕰️",
        "emoticons": [],
        "keywords": [
            "clock",
            "mantelpiece clock"
        ],
        "name": "mantelpiece clock",
        "shortcodes": [
            ":mantelpiece_clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕛",
        "emoticons": [],
        "keywords": [
            "00",
            "12",
            "12:00",
            "clock",
            "o’clock",
            "twelve"
        ],
        "name": "twelve o’clock",
        "shortcodes": [
            ":twelve_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕧",
        "emoticons": [],
        "keywords": [
            "12",
            "12:30",
            "clock",
            "thirty",
            "twelve",
            "twelve-thirty",
            "half past twelve",
            "12.30"
        ],
        "name": "twelve-thirty",
        "shortcodes": [
            ":twelve-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕐",
        "emoticons": [],
        "keywords": [
            "00",
            "1",
            "1:00",
            "clock",
            "o’clock",
            "one"
        ],
        "name": "one o’clock",
        "shortcodes": [
            ":one_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕜",
        "emoticons": [],
        "keywords": [
            "1",
            "1:30",
            "clock",
            "one",
            "one-thirty",
            "thirty",
            "half past one",
            "1.30"
        ],
        "name": "one-thirty",
        "shortcodes": [
            ":one-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕑",
        "emoticons": [],
        "keywords": [
            "00",
            "2",
            "2:00",
            "clock",
            "o’clock",
            "two"
        ],
        "name": "two o’clock",
        "shortcodes": [
            ":two_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕝",
        "emoticons": [],
        "keywords": [
            "2",
            "2:30",
            "clock",
            "thirty",
            "two",
            "two-thirty",
            "half past two",
            "2.30"
        ],
        "name": "two-thirty",
        "shortcodes": [
            ":two-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕒",
        "emoticons": [],
        "keywords": [
            "00",
            "3",
            "3:00",
            "clock",
            "o’clock",
            "three"
        ],
        "name": "three o’clock",
        "shortcodes": [
            ":three_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕞",
        "emoticons": [],
        "keywords": [
            "3",
            "3:30",
            "clock",
            "thirty",
            "three",
            "three-thirty",
            "half past three",
            "3.30"
        ],
        "name": "three-thirty",
        "shortcodes": [
            ":three-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕓",
        "emoticons": [],
        "keywords": [
            "00",
            "4",
            "4:00",
            "clock",
            "four",
            "o’clock"
        ],
        "name": "four o’clock",
        "shortcodes": [
            ":four_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕟",
        "emoticons": [],
        "keywords": [
            "4",
            "4:30",
            "clock",
            "four",
            "four-thirty",
            "thirty",
            "half past four",
            "4.30"
        ],
        "name": "four-thirty",
        "shortcodes": [
            ":four-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕔",
        "emoticons": [],
        "keywords": [
            "00",
            "5",
            "5:00",
            "clock",
            "five",
            "o’clock"
        ],
        "name": "five o’clock",
        "shortcodes": [
            ":five_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕠",
        "emoticons": [],
        "keywords": [
            "5",
            "5:30",
            "clock",
            "five",
            "five-thirty",
            "thirty",
            "half past five",
            "5.30"
        ],
        "name": "five-thirty",
        "shortcodes": [
            ":five-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕕",
        "emoticons": [],
        "keywords": [
            "00",
            "6",
            "6:00",
            "clock",
            "o’clock",
            "six"
        ],
        "name": "six o’clock",
        "shortcodes": [
            ":six_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕡",
        "emoticons": [],
        "keywords": [
            "6",
            "6:30",
            "clock",
            "six",
            "six-thirty",
            "thirty",
            "half past six",
            "6.30"
        ],
        "name": "six-thirty",
        "shortcodes": [
            ":six-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕖",
        "emoticons": [],
        "keywords": [
            "00",
            "7",
            "7:00",
            "clock",
            "o’clock",
            "seven"
        ],
        "name": "seven o’clock",
        "shortcodes": [
            ":seven_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕢",
        "emoticons": [],
        "keywords": [
            "7",
            "7:30",
            "clock",
            "seven",
            "seven-thirty",
            "thirty",
            "half past seven",
            "7.30"
        ],
        "name": "seven-thirty",
        "shortcodes": [
            ":seven-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕗",
        "emoticons": [],
        "keywords": [
            "00",
            "8",
            "8:00",
            "clock",
            "eight",
            "o’clock"
        ],
        "name": "eight o’clock",
        "shortcodes": [
            ":eight_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕣",
        "emoticons": [],
        "keywords": [
            "8",
            "8:30",
            "clock",
            "eight",
            "eight-thirty",
            "thirty",
            "half past eight",
            "8.30"
        ],
        "name": "eight-thirty",
        "shortcodes": [
            ":eight-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕘",
        "emoticons": [],
        "keywords": [
            "00",
            "9",
            "9:00",
            "clock",
            "nine",
            "o’clock"
        ],
        "name": "nine o’clock",
        "shortcodes": [
            ":nine_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕤",
        "emoticons": [],
        "keywords": [
            "9",
            "9:30",
            "clock",
            "nine",
            "nine-thirty",
            "thirty",
            "half past nine",
            "9.30"
        ],
        "name": "nine-thirty",
        "shortcodes": [
            ":nine-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕙",
        "emoticons": [],
        "keywords": [
            "00",
            "10",
            "10:00",
            "clock",
            "o’clock",
            "ten"
        ],
        "name": "ten o’clock",
        "shortcodes": [
            ":ten_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕥",
        "emoticons": [],
        "keywords": [
            "10",
            "10:30",
            "clock",
            "ten",
            "ten-thirty",
            "thirty",
            "half past ten",
            "10.30"
        ],
        "name": "ten-thirty",
        "shortcodes": [
            ":ten-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕚",
        "emoticons": [],
        "keywords": [
            "00",
            "11",
            "11:00",
            "clock",
            "eleven",
            "o’clock"
        ],
        "name": "eleven o’clock",
        "shortcodes": [
            ":eleven_o’clock:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🕦",
        "emoticons": [],
        "keywords": [
            "11",
            "11:30",
            "clock",
            "eleven",
            "eleven-thirty",
            "thirty",
            "half past eleven",
            "11.30"
        ],
        "name": "eleven-thirty",
        "shortcodes": [
            ":eleven-thirty:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌑",
        "emoticons": [],
        "keywords": [
            "dark",
            "moon",
            "new moon"
        ],
        "name": "new moon",
        "shortcodes": [
            ":new_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌒",
        "emoticons": [],
        "keywords": [
            "crescent",
            "moon",
            "waxing"
        ],
        "name": "waxing crescent moon",
        "shortcodes": [
            ":waxing_crescent_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌓",
        "emoticons": [],
        "keywords": [
            "first quarter moon",
            "moon",
            "quarter"
        ],
        "name": "first quarter moon",
        "shortcodes": [
            ":first_quarter_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌔",
        "emoticons": [],
        "keywords": [
            "gibbous",
            "moon",
            "waxing"
        ],
        "name": "waxing gibbous moon",
        "shortcodes": [
            ":waxing_gibbous_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌕",
        "emoticons": [],
        "keywords": [
            "full",
            "moon"
        ],
        "name": "full moon",
        "shortcodes": [
            ":full_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌖",
        "emoticons": [],
        "keywords": [
            "gibbous",
            "moon",
            "waning"
        ],
        "name": "waning gibbous moon",
        "shortcodes": [
            ":waning_gibbous_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌗",
        "emoticons": [],
        "keywords": [
            "last quarter moon",
            "moon",
            "quarter"
        ],
        "name": "last quarter moon",
        "shortcodes": [
            ":last_quarter_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌘",
        "emoticons": [],
        "keywords": [
            "crescent",
            "moon",
            "waning"
        ],
        "name": "waning crescent moon",
        "shortcodes": [
            ":waning_crescent_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌙",
        "emoticons": [],
        "keywords": [
            "crescent",
            "moon"
        ],
        "name": "crescent moon",
        "shortcodes": [
            ":crescent_moon:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌚",
        "emoticons": [],
        "keywords": [
            "face",
            "moon",
            "new moon face"
        ],
        "name": "new moon face",
        "shortcodes": [
            ":new_moon_face:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌛",
        "emoticons": [],
        "keywords": [
            "face",
            "first quarter moon face",
            "moon",
            "quarter"
        ],
        "name": "first quarter moon face",
        "shortcodes": [
            ":first_quarter_moon_face:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌜",
        "emoticons": [],
        "keywords": [
            "face",
            "last quarter moon face",
            "moon",
            "quarter"
        ],
        "name": "last quarter moon face",
        "shortcodes": [
            ":last_quarter_moon_face:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌡️",
        "emoticons": [],
        "keywords": [
            "thermometer",
            "weather"
        ],
        "name": "thermometer",
        "shortcodes": [
            ":thermometer:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "☀️",
        "emoticons": [],
        "keywords": [
            "bright",
            "rays",
            "sun",
            "sunny"
        ],
        "name": "sun",
        "shortcodes": [
            ":sun:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌝",
        "emoticons": [],
        "keywords": [
            "bright",
            "face",
            "full",
            "moon",
            "full-moon face"
        ],
        "name": "full moon face",
        "shortcodes": [
            ":full_moon_face:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌞",
        "emoticons": [],
        "keywords": [
            "bright",
            "face",
            "sun",
            "sun with face"
        ],
        "name": "sun with face",
        "shortcodes": [
            ":sun_with_face:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🪐",
        "emoticons": [],
        "keywords": [
            "ringed planet",
            "saturn",
            "saturnine"
        ],
        "name": "ringed planet",
        "shortcodes": [
            ":ringed_planet:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⭐",
        "emoticons": [],
        "keywords": [
            "star"
        ],
        "name": "star",
        "shortcodes": [
            ":star:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌟",
        "emoticons": [],
        "keywords": [
            "glittery",
            "glow",
            "glowing star",
            "shining",
            "sparkle",
            "star"
        ],
        "name": "glowing star",
        "shortcodes": [
            ":glowing_star:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌠",
        "emoticons": [],
        "keywords": [
            "falling",
            "shooting",
            "star"
        ],
        "name": "shooting star",
        "shortcodes": [
            ":shooting_star:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌌",
        "emoticons": [],
        "keywords": [
            "Milky Way",
            "space",
            "milky way",
            "Milky",
            "Way"
        ],
        "name": "milky way",
        "shortcodes": [
            ":milky_way:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "☁️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "weather"
        ],
        "name": "cloud",
        "shortcodes": [
            ":cloud:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛅",
        "emoticons": [],
        "keywords": [
            "cloud",
            "sun",
            "sun behind cloud"
        ],
        "name": "sun behind cloud",
        "shortcodes": [
            ":sun_behind_cloud:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛈️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "cloud with lightning and rain",
            "rain",
            "thunder"
        ],
        "name": "cloud with lightning and rain",
        "shortcodes": [
            ":cloud_with_lightning_and_rain:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌤️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "sun",
            "sun behind small cloud"
        ],
        "name": "sun behind small cloud",
        "shortcodes": [
            ":sun_behind_small_cloud:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌥️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "sun",
            "sun behind large cloud"
        ],
        "name": "sun behind large cloud",
        "shortcodes": [
            ":sun_behind_large_cloud:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌦️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "rain",
            "sun",
            "sun behind rain cloud"
        ],
        "name": "sun behind rain cloud",
        "shortcodes": [
            ":sun_behind_rain_cloud:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌧️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "cloud with rain",
            "rain"
        ],
        "name": "cloud with rain",
        "shortcodes": [
            ":cloud_with_rain:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌨️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "cloud with snow",
            "cold",
            "snow"
        ],
        "name": "cloud with snow",
        "shortcodes": [
            ":cloud_with_snow:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌩️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "cloud with lightning",
            "lightning"
        ],
        "name": "cloud with lightning",
        "shortcodes": [
            ":cloud_with_lightning:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌪️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "tornado",
            "whirlwind"
        ],
        "name": "tornado",
        "shortcodes": [
            ":tornado:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌫️",
        "emoticons": [],
        "keywords": [
            "cloud",
            "fog"
        ],
        "name": "fog",
        "shortcodes": [
            ":fog:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌬️",
        "emoticons": [],
        "keywords": [
            "blow",
            "cloud",
            "face",
            "wind"
        ],
        "name": "wind face",
        "shortcodes": [
            ":wind_face:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌀",
        "emoticons": [],
        "keywords": [
            "cyclone",
            "dizzy",
            "hurricane",
            "twister",
            "typhoon"
        ],
        "name": "cyclone",
        "shortcodes": [
            ":cyclone:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌈",
        "emoticons": [],
        "keywords": [
            "rain",
            "rainbow"
        ],
        "name": "rainbow",
        "shortcodes": [
            ":rainbow:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌂",
        "emoticons": [],
        "keywords": [
            "closed umbrella",
            "clothing",
            "rain",
            "umbrella"
        ],
        "name": "closed umbrella",
        "shortcodes": [
            ":closed_umbrella:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "☂️",
        "emoticons": [],
        "keywords": [
            "clothing",
            "rain",
            "umbrella"
        ],
        "name": "umbrella",
        "shortcodes": [
            ":umbrella:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "☔",
        "emoticons": [],
        "keywords": [
            "clothing",
            "drop",
            "rain",
            "umbrella",
            "umbrella with rain drops"
        ],
        "name": "umbrella with rain drops",
        "shortcodes": [
            ":umbrella_with_rain_drops:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛱️",
        "emoticons": [],
        "keywords": [
            "beach",
            "sand",
            "sun",
            "umbrella",
            "rain",
            "umbrella on ground"
        ],
        "name": "umbrella on ground",
        "shortcodes": [
            ":umbrella_on_ground:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⚡",
        "emoticons": [],
        "keywords": [
            "danger",
            "electric",
            "high voltage",
            "lightning",
            "voltage",
            "zap"
        ],
        "name": "high voltage",
        "shortcodes": [
            ":high_voltage:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "❄️",
        "emoticons": [],
        "keywords": [
            "cold",
            "snow",
            "snowflake"
        ],
        "name": "snowflake",
        "shortcodes": [
            ":snowflake:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "☃️",
        "emoticons": [],
        "keywords": [
            "cold",
            "snow",
            "snowman"
        ],
        "name": "snowman",
        "shortcodes": [
            ":snowman:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "⛄",
        "emoticons": [],
        "keywords": [
            "cold",
            "snow",
            "snowman",
            "snowman without snow"
        ],
        "name": "snowman without snow",
        "shortcodes": [
            ":snowman_without_snow:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "☄️",
        "emoticons": [],
        "keywords": [
            "comet",
            "space"
        ],
        "name": "comet",
        "shortcodes": [
            ":comet:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🔥",
        "emoticons": [],
        "keywords": [
            "fire",
            "flame",
            "tool"
        ],
        "name": "fire",
        "shortcodes": [
            ":fire:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "💧",
        "emoticons": [],
        "keywords": [
            "cold",
            "comic",
            "drop",
            "droplet",
            "sweat"
        ],
        "name": "droplet",
        "shortcodes": [
            ":droplet:"
        ]
    },
    {
        "category": "Travel & Places",
        "codepoints": "🌊",
        "emoticons": [],
        "keywords": [
            "ocean",
            "water",
            "wave"
        ],
        "name": "water wave",
        "shortcodes": [
            ":water_wave:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎃",
        "emoticons": [],
        "keywords": [
            "celebration",
            "halloween",
            "jack",
            "jack-o-lantern",
            "lantern",
            "Halloween",
            "jack-o’-lantern"
        ],
        "name": "jack-o-lantern",
        "shortcodes": [
            ":jack-o-lantern:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎄",
        "emoticons": [],
        "keywords": [
            "celebration",
            "Christmas",
            "tree"
        ],
        "name": "Christmas tree",
        "shortcodes": [
            ":Christmas_tree:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎆",
        "emoticons": [],
        "keywords": [
            "celebration",
            "fireworks"
        ],
        "name": "fireworks",
        "shortcodes": [
            ":fireworks:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎇",
        "emoticons": [],
        "keywords": [
            "celebration",
            "fireworks",
            "sparkle",
            "sparkler"
        ],
        "name": "sparkler",
        "shortcodes": [
            ":sparkler:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🧨",
        "emoticons": [],
        "keywords": [
            "dynamite",
            "explosive",
            "firecracker",
            "fireworks"
        ],
        "name": "firecracker",
        "shortcodes": [
            ":firecracker:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "✨",
        "emoticons": [],
        "keywords": [
            "*",
            "sparkle",
            "sparkles",
            "star"
        ],
        "name": "sparkles",
        "shortcodes": [
            ":sparkles:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎈",
        "emoticons": [],
        "keywords": [
            "balloon",
            "celebration"
        ],
        "name": "balloon",
        "shortcodes": [
            ":balloon:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎉",
        "emoticons": [],
        "keywords": [
            "celebration",
            "party",
            "popper",
            "ta-da",
            "tada"
        ],
        "name": "party popper",
        "shortcodes": [
            ":party_popper:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎊",
        "emoticons": [],
        "keywords": [
            "ball",
            "celebration",
            "confetti"
        ],
        "name": "confetti ball",
        "shortcodes": [
            ":confetti_ball:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎋",
        "emoticons": [],
        "keywords": [
            "banner",
            "celebration",
            "Japanese",
            "tanabata tree",
            "tree",
            "Tanabata tree"
        ],
        "name": "tanabata tree",
        "shortcodes": [
            ":tanabata_tree:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎍",
        "emoticons": [],
        "keywords": [
            "bamboo",
            "celebration",
            "decoration",
            "Japanese",
            "pine",
            "pine decoration"
        ],
        "name": "pine decoration",
        "shortcodes": [
            ":pine_decoration:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎎",
        "emoticons": [],
        "keywords": [
            "celebration",
            "doll",
            "festival",
            "Japanese",
            "Japanese dolls"
        ],
        "name": "Japanese dolls",
        "shortcodes": [
            ":Japanese_dolls:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎏",
        "emoticons": [],
        "keywords": [
            "carp",
            "celebration",
            "streamer",
            "carp wind sock",
            "Japanese wind socks",
            "koinobori"
        ],
        "name": "carp streamer",
        "shortcodes": [
            ":carp_streamer:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎐",
        "emoticons": [],
        "keywords": [
            "bell",
            "celebration",
            "chime",
            "wind"
        ],
        "name": "wind chime",
        "shortcodes": [
            ":wind_chime:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎑",
        "emoticons": [],
        "keywords": [
            "celebration",
            "ceremony",
            "moon",
            "moon viewing ceremony",
            "moon-viewing ceremony"
        ],
        "name": "moon viewing ceremony",
        "shortcodes": [
            ":moon_viewing_ceremony:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🧧",
        "emoticons": [],
        "keywords": [
            "gift",
            "good luck",
            "hóngbāo",
            "lai see",
            "money",
            "red envelope"
        ],
        "name": "red envelope",
        "shortcodes": [
            ":red_envelope:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎀",
        "emoticons": [],
        "keywords": [
            "celebration",
            "ribbon"
        ],
        "name": "ribbon",
        "shortcodes": [
            ":ribbon:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎁",
        "emoticons": [],
        "keywords": [
            "box",
            "celebration",
            "gift",
            "present",
            "wrapped"
        ],
        "name": "wrapped gift",
        "shortcodes": [
            ":wrapped_gift:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎗️",
        "emoticons": [],
        "keywords": [
            "celebration",
            "reminder",
            "ribbon"
        ],
        "name": "reminder ribbon",
        "shortcodes": [
            ":reminder_ribbon:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎟️",
        "emoticons": [],
        "keywords": [
            "admission",
            "admission tickets",
            "entry",
            "ticket"
        ],
        "name": "admission tickets",
        "shortcodes": [
            ":admission_tickets:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎫",
        "emoticons": [],
        "keywords": [
            "admission",
            "ticket"
        ],
        "name": "ticket",
        "shortcodes": [
            ":ticket:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎖️",
        "emoticons": [],
        "keywords": [
            "celebration",
            "medal",
            "military"
        ],
        "name": "military medal",
        "shortcodes": [
            ":military_medal:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏆",
        "emoticons": [],
        "keywords": [
            "celebration",
            "prize",
            "trophy"
        ],
        "name": "trophy",
        "shortcodes": [
            ":trophy:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏅",
        "emoticons": [],
        "keywords": [
            "celebration",
            "medal",
            "sports",
            "sports medal"
        ],
        "name": "sports medal",
        "shortcodes": [
            ":sports_medal:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥇",
        "emoticons": [],
        "keywords": [
            "1st place medal",
            "first",
            "gold",
            "medal"
        ],
        "name": "1st place medal",
        "shortcodes": [
            ":1st_place_medal:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥈",
        "emoticons": [],
        "keywords": [
            "2nd place medal",
            "medal",
            "second",
            "silver"
        ],
        "name": "2nd place medal",
        "shortcodes": [
            ":2nd_place_medal:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥉",
        "emoticons": [],
        "keywords": [
            "3rd place medal",
            "bronze",
            "medal",
            "third"
        ],
        "name": "3rd place medal",
        "shortcodes": [
            ":3rd_place_medal:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "⚽",
        "emoticons": [],
        "keywords": [
            "ball",
            "football",
            "soccer"
        ],
        "name": "soccer ball",
        "shortcodes": [
            ":soccer_ball:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "⚾",
        "emoticons": [],
        "keywords": [
            "ball",
            "baseball"
        ],
        "name": "baseball",
        "shortcodes": [
            ":baseball:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥎",
        "emoticons": [],
        "keywords": [
            "ball",
            "glove",
            "softball",
            "underarm"
        ],
        "name": "softball",
        "shortcodes": [
            ":softball:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏀",
        "emoticons": [],
        "keywords": [
            "ball",
            "basketball",
            "hoop"
        ],
        "name": "basketball",
        "shortcodes": [
            ":basketball:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏐",
        "emoticons": [],
        "keywords": [
            "ball",
            "game",
            "volleyball"
        ],
        "name": "volleyball",
        "shortcodes": [
            ":volleyball:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏈",
        "emoticons": [],
        "keywords": [
            "american",
            "ball",
            "football"
        ],
        "name": "american football",
        "shortcodes": [
            ":american_football:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏉",
        "emoticons": [],
        "keywords": [
            "australian football",
            "rugby ball",
            "rugby league",
            "rugby union",
            "ball",
            "football",
            "rugby"
        ],
        "name": "rugby football",
        "shortcodes": [
            ":rugby_football:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎾",
        "emoticons": [],
        "keywords": [
            "ball",
            "racquet",
            "tennis"
        ],
        "name": "tennis",
        "shortcodes": [
            ":tennis:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥏",
        "emoticons": [],
        "keywords": [
            "flying disc",
            "frisbee",
            "ultimate",
            "Frisbee"
        ],
        "name": "flying disc",
        "shortcodes": [
            ":flying_disc:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎳",
        "emoticons": [],
        "keywords": [
            "ball",
            "game",
            "tenpin bowling",
            "bowling"
        ],
        "name": "bowling",
        "shortcodes": [
            ":bowling:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏏",
        "emoticons": [],
        "keywords": [
            "ball",
            "bat",
            "cricket game",
            "game",
            "cricket",
            "cricket match"
        ],
        "name": "cricket game",
        "shortcodes": [
            ":cricket_game:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏑",
        "emoticons": [],
        "keywords": [
            "ball",
            "field",
            "game",
            "hockey",
            "stick"
        ],
        "name": "field hockey",
        "shortcodes": [
            ":field_hockey:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏒",
        "emoticons": [],
        "keywords": [
            "game",
            "hockey",
            "ice",
            "puck",
            "stick"
        ],
        "name": "ice hockey",
        "shortcodes": [
            ":ice_hockey:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥍",
        "emoticons": [],
        "keywords": [
            "ball",
            "goal",
            "lacrosse",
            "stick"
        ],
        "name": "lacrosse",
        "shortcodes": [
            ":lacrosse:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏓",
        "emoticons": [],
        "keywords": [
            "ball",
            "bat",
            "game",
            "paddle",
            "ping pong",
            "table tennis"
        ],
        "name": "ping pong",
        "shortcodes": [
            ":ping_pong:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🏸",
        "emoticons": [],
        "keywords": [
            "badminton",
            "birdie",
            "game",
            "racquet",
            "shuttlecock"
        ],
        "name": "badminton",
        "shortcodes": [
            ":badminton:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥊",
        "emoticons": [],
        "keywords": [
            "boxing",
            "glove"
        ],
        "name": "boxing glove",
        "shortcodes": [
            ":boxing_glove:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥋",
        "emoticons": [],
        "keywords": [
            "judo",
            "karate",
            "martial arts",
            "martial arts uniform",
            "taekwondo",
            "uniform"
        ],
        "name": "martial arts uniform",
        "shortcodes": [
            ":martial_arts_uniform:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥅",
        "emoticons": [],
        "keywords": [
            "goal",
            "goal cage",
            "net"
        ],
        "name": "goal net",
        "shortcodes": [
            ":goal_net:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "⛳",
        "emoticons": [],
        "keywords": [
            "flag",
            "flag in hole",
            "golf",
            "hole"
        ],
        "name": "flag in hole",
        "shortcodes": [
            ":flag_in_hole:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "⛸️",
        "emoticons": [],
        "keywords": [
            "ice",
            "ice skating",
            "skate"
        ],
        "name": "ice skate",
        "shortcodes": [
            ":ice_skate:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎣",
        "emoticons": [],
        "keywords": [
            "fish",
            "fishing",
            "pole",
            "rod",
            "fishing pole"
        ],
        "name": "fishing pole",
        "shortcodes": [
            ":fishing_pole:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🤿",
        "emoticons": [],
        "keywords": [
            "diving",
            "diving mask",
            "scuba",
            "snorkeling",
            "snorkelling"
        ],
        "name": "diving mask",
        "shortcodes": [
            ":diving_mask:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎽",
        "emoticons": [],
        "keywords": [
            "athletics",
            "running",
            "sash",
            "shirt"
        ],
        "name": "running shirt",
        "shortcodes": [
            ":running_shirt:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎿",
        "emoticons": [],
        "keywords": [
            "ski",
            "skiing",
            "skis",
            "snow"
        ],
        "name": "skis",
        "shortcodes": [
            ":skis:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🛷",
        "emoticons": [],
        "keywords": [
            "sled",
            "sledge",
            "sleigh"
        ],
        "name": "sled",
        "shortcodes": [
            ":sled:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🥌",
        "emoticons": [],
        "keywords": [
            "curling",
            "game",
            "rock",
            "stone",
            "curling stone",
            "curling rock"
        ],
        "name": "curling stone",
        "shortcodes": [
            ":curling_stone:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎯",
        "emoticons": [],
        "keywords": [
            "bullseye",
            "dart",
            "direct hit",
            "game",
            "hit",
            "target"
        ],
        "name": "bullseye",
        "shortcodes": [
            ":bullseye:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🪀",
        "emoticons": [],
        "keywords": [
            "fluctuate",
            "toy",
            "yo-yo"
        ],
        "name": "yo-yo",
        "shortcodes": [
            ":yo-yo:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🪁",
        "emoticons": [],
        "keywords": [
            "fly",
            "kite",
            "soar"
        ],
        "name": "kite",
        "shortcodes": [
            ":kite:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎱",
        "emoticons": [],
        "keywords": [
            "8",
            "ball",
            "billiard",
            "eight",
            "game",
            "pool 8 ball"
        ],
        "name": "pool 8 ball",
        "shortcodes": [
            ":pool_8_ball:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🔮",
        "emoticons": [],
        "keywords": [
            "ball",
            "crystal",
            "fairy tale",
            "fantasy",
            "fortune",
            "tool"
        ],
        "name": "crystal ball",
        "shortcodes": [
            ":crystal_ball:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🧿",
        "emoticons": [],
        "keywords": [
            "amulet",
            "charm",
            "evil-eye",
            "nazar",
            "talisman",
            "bead",
            "nazar amulet",
            "evil eye"
        ],
        "name": "nazar amulet",
        "shortcodes": [
            ":nazar_amulet:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎮",
        "emoticons": [],
        "keywords": [
            "controller",
            "game",
            "video game"
        ],
        "name": "video game",
        "shortcodes": [
            ":video_game:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🕹️",
        "emoticons": [],
        "keywords": [
            "game",
            "joystick",
            "video game"
        ],
        "name": "joystick",
        "shortcodes": [
            ":joystick:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎰",
        "emoticons": [],
        "keywords": [
            "game",
            "pokie",
            "pokies",
            "slot",
            "slot machine"
        ],
        "name": "slot machine",
        "shortcodes": [
            ":slot_machine:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎲",
        "emoticons": [],
        "keywords": [
            "dice",
            "die",
            "game"
        ],
        "name": "game die",
        "shortcodes": [
            ":game_die:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🧩",
        "emoticons": [],
        "keywords": [
            "clue",
            "interlocking",
            "jigsaw",
            "piece",
            "puzzle"
        ],
        "name": "puzzle piece",
        "shortcodes": [
            ":puzzle_piece:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🧸",
        "emoticons": [],
        "keywords": [
            "plaything",
            "plush",
            "stuffed",
            "teddy bear",
            "toy"
        ],
        "name": "teddy bear",
        "shortcodes": [
            ":teddy_bear:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "♠️",
        "emoticons": [],
        "keywords": [
            "card",
            "game",
            "spade suit"
        ],
        "name": "spade suit",
        "shortcodes": [
            ":spade_suit:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "♥️",
        "emoticons": [],
        "keywords": [
            "card",
            "game",
            "heart suit"
        ],
        "name": "heart suit",
        "shortcodes": [
            ":heart_suit:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "♦️",
        "emoticons": [],
        "keywords": [
            "card",
            "diamond suit",
            "diamonds",
            "game"
        ],
        "name": "diamond suit",
        "shortcodes": [
            ":diamond_suit:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "♣️",
        "emoticons": [],
        "keywords": [
            "card",
            "club suit",
            "clubs",
            "game"
        ],
        "name": "club suit",
        "shortcodes": [
            ":club_suit:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "♟️",
        "emoticons": [],
        "keywords": [
            "chess",
            "chess pawn",
            "dupe",
            "expendable"
        ],
        "name": "chess pawn",
        "shortcodes": [
            ":chess_pawn:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🃏",
        "emoticons": [],
        "keywords": [
            "card",
            "game",
            "joker",
            "wildcard"
        ],
        "name": "joker",
        "shortcodes": [
            ":joker:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🀄",
        "emoticons": [],
        "keywords": [
            "game",
            "mahjong",
            "mahjong red dragon",
            "red",
            "Mahjong",
            "Mahjong red dragon"
        ],
        "name": "mahjong red dragon",
        "shortcodes": [
            ":mahjong_red_dragon:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎴",
        "emoticons": [],
        "keywords": [
            "card",
            "flower",
            "flower playing cards",
            "game",
            "Japanese",
            "playing"
        ],
        "name": "flower playing cards",
        "shortcodes": [
            ":flower_playing_cards:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎭",
        "emoticons": [],
        "keywords": [
            "art",
            "mask",
            "performing",
            "performing arts",
            "theater",
            "theatre"
        ],
        "name": "performing arts",
        "shortcodes": [
            ":performing_arts:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🖼️",
        "emoticons": [],
        "keywords": [
            "art",
            "frame",
            "framed picture",
            "museum",
            "painting",
            "picture"
        ],
        "name": "framed picture",
        "shortcodes": [
            ":framed_picture:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🎨",
        "emoticons": [],
        "keywords": [
            "art",
            "artist palette",
            "museum",
            "painting",
            "palette"
        ],
        "name": "artist palette",
        "shortcodes": [
            ":artist_palette:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🧵",
        "emoticons": [],
        "keywords": [
            "needle",
            "sewing",
            "spool",
            "string",
            "thread"
        ],
        "name": "thread",
        "shortcodes": [
            ":thread:"
        ]
    },
    {
        "category": "Activities",
        "codepoints": "🧶",
        "emoticons": [],
        "keywords": [
            "ball",
            "crochet",
            "knit",
            "yarn"
        ],
        "name": "yarn",
        "shortcodes": [
            ":yarn:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👓",
        "emoticons": [],
        "keywords": [
            "clothing",
            "eye",
            "eyeglasses",
            "eyewear",
            "glasses"
        ],
        "name": "glasses",
        "shortcodes": [
            ":glasses:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🕶️",
        "emoticons": [],
        "keywords": [
            "dark",
            "eye",
            "eyewear",
            "glasses",
            "sunglasses",
            "sunnies"
        ],
        "name": "sunglasses",
        "shortcodes": [
            ":sunglasses:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🥽",
        "emoticons": [],
        "keywords": [
            "eye protection",
            "goggles",
            "swimming",
            "welding"
        ],
        "name": "goggles",
        "shortcodes": [
            ":goggles:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🥼",
        "emoticons": [],
        "keywords": [
            "doctor",
            "experiment",
            "lab coat",
            "scientist"
        ],
        "name": "lab coat",
        "shortcodes": [
            ":lab_coat:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🦺",
        "emoticons": [],
        "keywords": [
            "emergency",
            "safety",
            "vest",
            "hi-vis",
            "high-vis",
            "jacket",
            "life jacket"
        ],
        "name": "safety vest",
        "shortcodes": [
            ":safety_vest:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👔",
        "emoticons": [],
        "keywords": [
            "clothing",
            "necktie",
            "tie"
        ],
        "name": "necktie",
        "shortcodes": [
            ":necktie:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👕",
        "emoticons": [],
        "keywords": [
            "clothing",
            "shirt",
            "t-shirt",
            "T-shirt",
            "tee",
            "tshirt",
            "tee-shirt"
        ],
        "name": "t-shirt",
        "shortcodes": [
            ":t-shirt:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👖",
        "emoticons": [],
        "keywords": [
            "clothing",
            "jeans",
            "pants",
            "trousers"
        ],
        "name": "jeans",
        "shortcodes": [
            ":jeans:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧣",
        "emoticons": [],
        "keywords": [
            "neck",
            "scarf"
        ],
        "name": "scarf",
        "shortcodes": [
            ":scarf:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧤",
        "emoticons": [],
        "keywords": [
            "gloves",
            "hand"
        ],
        "name": "gloves",
        "shortcodes": [
            ":gloves:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧥",
        "emoticons": [],
        "keywords": [
            "coat",
            "jacket"
        ],
        "name": "coat",
        "shortcodes": [
            ":coat:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧦",
        "emoticons": [],
        "keywords": [
            "socks",
            "stocking"
        ],
        "name": "socks",
        "shortcodes": [
            ":socks:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👗",
        "emoticons": [],
        "keywords": [
            "clothing",
            "dress",
            "woman’s clothes"
        ],
        "name": "dress",
        "shortcodes": [
            ":dress:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👘",
        "emoticons": [],
        "keywords": [
            "clothing",
            "kimono"
        ],
        "name": "kimono",
        "shortcodes": [
            ":kimono:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🥻",
        "emoticons": [],
        "keywords": [
            "clothing",
            "dress",
            "sari"
        ],
        "name": "sari",
        "shortcodes": [
            ":sari:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🩱",
        "emoticons": [],
        "keywords": [
            "bathing suit",
            "one-piece swimsuit",
            "swimming costume"
        ],
        "name": "one-piece swimsuit",
        "shortcodes": [
            ":one-piece_swimsuit:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🩲",
        "emoticons": [],
        "keywords": [
            "bathers",
            "briefs",
            "speedos",
            "underwear",
            "bathing suit",
            "one-piece",
            "swimsuit",
            "pants"
        ],
        "name": "briefs",
        "shortcodes": [
            ":briefs:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🩳",
        "emoticons": [],
        "keywords": [
            "bathing suit",
            "boardies",
            "boardshorts",
            "shorts",
            "swim shorts",
            "underwear",
            "pants"
        ],
        "name": "shorts",
        "shortcodes": [
            ":shorts:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👙",
        "emoticons": [],
        "keywords": [
            "bikini",
            "clothing",
            "swim suit",
            "two-piece",
            "swim"
        ],
        "name": "bikini",
        "shortcodes": [
            ":bikini:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👚",
        "emoticons": [],
        "keywords": [
            "blouse",
            "clothing",
            "top",
            "woman",
            "woman’s clothes"
        ],
        "name": "woman’s clothes",
        "shortcodes": [
            ":woman’s_clothes:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👛",
        "emoticons": [],
        "keywords": [
            "accessories",
            "coin",
            "purse",
            "clothing"
        ],
        "name": "purse",
        "shortcodes": [
            ":purse:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👜",
        "emoticons": [],
        "keywords": [
            "accessories",
            "bag",
            "handbag",
            "tote",
            "clothing",
            "purse"
        ],
        "name": "handbag",
        "shortcodes": [
            ":handbag:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👝",
        "emoticons": [],
        "keywords": [
            "accessories",
            "bag",
            "clutch bag",
            "pouch",
            "clothing"
        ],
        "name": "clutch bag",
        "shortcodes": [
            ":clutch_bag:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🛍️",
        "emoticons": [],
        "keywords": [
            "bag",
            "hotel",
            "shopping",
            "shopping bags"
        ],
        "name": "shopping bags",
        "shortcodes": [
            ":shopping_bags:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎒",
        "emoticons": [],
        "keywords": [
            "backpack",
            "bag",
            "rucksack",
            "satchel",
            "school"
        ],
        "name": "backpack",
        "shortcodes": [
            ":backpack:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👞",
        "emoticons": [],
        "keywords": [
            "clothing",
            "man",
            "man’s shoe",
            "shoe"
        ],
        "name": "man’s shoe",
        "shortcodes": [
            ":man’s_shoe:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👟",
        "emoticons": [],
        "keywords": [
            "athletic",
            "clothing",
            "runners",
            "running shoe",
            "shoe",
            "sneaker",
            "trainer"
        ],
        "name": "running shoe",
        "shortcodes": [
            ":running_shoe:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🥾",
        "emoticons": [],
        "keywords": [
            "backpacking",
            "boot",
            "camping",
            "hiking"
        ],
        "name": "hiking boot",
        "shortcodes": [
            ":hiking_boot:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🥿",
        "emoticons": [],
        "keywords": [
            "ballet flat",
            "flat shoe",
            "slip-on",
            "slipper",
            "pump"
        ],
        "name": "flat shoe",
        "shortcodes": [
            ":flat_shoe:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👠",
        "emoticons": [],
        "keywords": [
            "clothing",
            "heel",
            "high-heeled shoe",
            "shoe",
            "woman"
        ],
        "name": "high-heeled shoe",
        "shortcodes": [
            ":high-heeled_shoe:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👡",
        "emoticons": [],
        "keywords": [
            "clothing",
            "sandal",
            "shoe",
            "woman",
            "woman’s sandal"
        ],
        "name": "woman’s sandal",
        "shortcodes": [
            ":woman’s_sandal:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🩰",
        "emoticons": [],
        "keywords": [
            "ballet",
            "ballet shoes",
            "dance"
        ],
        "name": "ballet shoes",
        "shortcodes": [
            ":ballet_shoes:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👢",
        "emoticons": [],
        "keywords": [
            "boot",
            "clothing",
            "shoe",
            "woman",
            "woman’s boot"
        ],
        "name": "woman’s boot",
        "shortcodes": [
            ":woman’s_boot:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👑",
        "emoticons": [],
        "keywords": [
            "clothing",
            "crown",
            "king",
            "queen"
        ],
        "name": "crown",
        "shortcodes": [
            ":crown:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "👒",
        "emoticons": [],
        "keywords": [
            "clothing",
            "hat",
            "woman",
            "woman’s hat"
        ],
        "name": "woman’s hat",
        "shortcodes": [
            ":woman’s_hat:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎩",
        "emoticons": [],
        "keywords": [
            "clothing",
            "hat",
            "top",
            "tophat"
        ],
        "name": "top hat",
        "shortcodes": [
            ":top_hat:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎓",
        "emoticons": [],
        "keywords": [
            "cap",
            "celebration",
            "clothing",
            "graduation",
            "hat"
        ],
        "name": "graduation cap",
        "shortcodes": [
            ":graduation_cap:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧢",
        "emoticons": [],
        "keywords": [
            "baseball cap",
            "billed cap"
        ],
        "name": "billed cap",
        "shortcodes": [
            ":billed_cap:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⛑️",
        "emoticons": [],
        "keywords": [
            "aid",
            "cross",
            "face",
            "hat",
            "helmet",
            "rescue worker’s helmet"
        ],
        "name": "rescue worker’s helmet",
        "shortcodes": [
            ":rescue_worker’s_helmet:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📿",
        "emoticons": [],
        "keywords": [
            "beads",
            "clothing",
            "necklace",
            "prayer",
            "religion"
        ],
        "name": "prayer beads",
        "shortcodes": [
            ":prayer_beads:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💄",
        "emoticons": [],
        "keywords": [
            "cosmetics",
            "lipstick",
            "make-up",
            "makeup"
        ],
        "name": "lipstick",
        "shortcodes": [
            ":lipstick:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💍",
        "emoticons": [],
        "keywords": [
            "diamond",
            "ring"
        ],
        "name": "ring",
        "shortcodes": [
            ":ring:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💎",
        "emoticons": [],
        "keywords": [
            "diamond",
            "gem",
            "gem stone",
            "jewel",
            "gemstone"
        ],
        "name": "gem stone",
        "shortcodes": [
            ":gem_stone:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔇",
        "emoticons": [],
        "keywords": [
            "mute",
            "muted speaker",
            "quiet",
            "silent",
            "speaker"
        ],
        "name": "muted speaker",
        "shortcodes": [
            ":muted_speaker:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔈",
        "emoticons": [],
        "keywords": [
            "low",
            "quiet",
            "soft",
            "speaker",
            "volume",
            "speaker low volume"
        ],
        "name": "speaker low volume",
        "shortcodes": [
            ":speaker_low_volume:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔉",
        "emoticons": [],
        "keywords": [
            "medium",
            "speaker medium volume"
        ],
        "name": "speaker medium volume",
        "shortcodes": [
            ":speaker_medium_volume:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔊",
        "emoticons": [],
        "keywords": [
            "loud",
            "speaker high volume"
        ],
        "name": "speaker high volume",
        "shortcodes": [
            ":speaker_high_volume:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📢",
        "emoticons": [],
        "keywords": [
            "loud",
            "loudspeaker",
            "public address"
        ],
        "name": "loudspeaker",
        "shortcodes": [
            ":loudspeaker:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📣",
        "emoticons": [],
        "keywords": [
            "cheering",
            "megaphone"
        ],
        "name": "megaphone",
        "shortcodes": [
            ":megaphone:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📯",
        "emoticons": [],
        "keywords": [
            "horn",
            "post",
            "postal"
        ],
        "name": "postal horn",
        "shortcodes": [
            ":postal_horn:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔔",
        "emoticons": [],
        "keywords": [
            "bell"
        ],
        "name": "bell",
        "shortcodes": [
            ":bell:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔕",
        "emoticons": [],
        "keywords": [
            "bell",
            "bell with slash",
            "forbidden",
            "mute",
            "quiet",
            "silent"
        ],
        "name": "bell with slash",
        "shortcodes": [
            ":bell_with_slash:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎼",
        "emoticons": [],
        "keywords": [
            "music",
            "musical score",
            "score"
        ],
        "name": "musical score",
        "shortcodes": [
            ":musical_score:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎵",
        "emoticons": [],
        "keywords": [
            "music",
            "musical note",
            "note"
        ],
        "name": "musical note",
        "shortcodes": [
            ":musical_note:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎶",
        "emoticons": [],
        "keywords": [
            "music",
            "musical notes",
            "note",
            "notes"
        ],
        "name": "musical notes",
        "shortcodes": [
            ":musical_notes:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎙️",
        "emoticons": [],
        "keywords": [
            "mic",
            "microphone",
            "music",
            "studio"
        ],
        "name": "studio microphone",
        "shortcodes": [
            ":studio_microphone:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎚️",
        "emoticons": [],
        "keywords": [
            "level",
            "music",
            "slider"
        ],
        "name": "level slider",
        "shortcodes": [
            ":level_slider:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎛️",
        "emoticons": [],
        "keywords": [
            "control",
            "knobs",
            "music"
        ],
        "name": "control knobs",
        "shortcodes": [
            ":control_knobs:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎤",
        "emoticons": [],
        "keywords": [
            "karaoke",
            "mic",
            "microphone"
        ],
        "name": "microphone",
        "shortcodes": [
            ":microphone:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎧",
        "emoticons": [],
        "keywords": [
            "earbud",
            "headphone"
        ],
        "name": "headphone",
        "shortcodes": [
            ":headphone:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📻",
        "emoticons": [],
        "keywords": [
            "AM",
            "FM",
            "radio",
            "wireless",
            "video"
        ],
        "name": "radio",
        "shortcodes": [
            ":radio:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎷",
        "emoticons": [],
        "keywords": [
            "instrument",
            "music",
            "sax",
            "saxophone"
        ],
        "name": "saxophone",
        "shortcodes": [
            ":saxophone:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎸",
        "emoticons": [],
        "keywords": [
            "guitar",
            "instrument",
            "music"
        ],
        "name": "guitar",
        "shortcodes": [
            ":guitar:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎹",
        "emoticons": [],
        "keywords": [
            "instrument",
            "keyboard",
            "music",
            "musical keyboard",
            "organ",
            "piano"
        ],
        "name": "musical keyboard",
        "shortcodes": [
            ":musical_keyboard:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎺",
        "emoticons": [],
        "keywords": [
            "instrument",
            "music",
            "trumpet"
        ],
        "name": "trumpet",
        "shortcodes": [
            ":trumpet:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎻",
        "emoticons": [],
        "keywords": [
            "instrument",
            "music",
            "violin"
        ],
        "name": "violin",
        "shortcodes": [
            ":violin:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🪕",
        "emoticons": [],
        "keywords": [
            "banjo",
            "music",
            "stringed"
        ],
        "name": "banjo",
        "shortcodes": [
            ":banjo:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🥁",
        "emoticons": [],
        "keywords": [
            "drum",
            "drumsticks",
            "music",
            "percussions"
        ],
        "name": "drum",
        "shortcodes": [
            ":drum:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📱",
        "emoticons": [],
        "keywords": [
            "cell",
            "mobile",
            "phone",
            "telephone"
        ],
        "name": "mobile phone",
        "shortcodes": [
            ":mobile_phone:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📲",
        "emoticons": [],
        "keywords": [
            "arrow",
            "cell",
            "mobile",
            "mobile phone with arrow",
            "phone",
            "receive"
        ],
        "name": "mobile phone with arrow",
        "shortcodes": [
            ":mobile_phone_with_arrow:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "☎️",
        "emoticons": [],
        "keywords": [
            "landline",
            "phone",
            "telephone"
        ],
        "name": "telephone",
        "shortcodes": [
            ":telephone:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📞",
        "emoticons": [],
        "keywords": [
            "phone",
            "receiver",
            "telephone"
        ],
        "name": "telephone receiver",
        "shortcodes": [
            ":telephone_receiver:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📟",
        "emoticons": [],
        "keywords": [
            "pager"
        ],
        "name": "pager",
        "shortcodes": [
            ":pager:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📠",
        "emoticons": [],
        "keywords": [
            "fax",
            "fax machine"
        ],
        "name": "fax machine",
        "shortcodes": [
            ":fax_machine:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔋",
        "emoticons": [],
        "keywords": [
            "battery"
        ],
        "name": "battery",
        "shortcodes": [
            ":battery:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔌",
        "emoticons": [],
        "keywords": [
            "electric",
            "electricity",
            "plug"
        ],
        "name": "electric plug",
        "shortcodes": [
            ":electric_plug:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💻",
        "emoticons": [],
        "keywords": [
            "computer",
            "laptop",
            "PC",
            "personal",
            "pc"
        ],
        "name": "laptop",
        "shortcodes": [
            ":laptop:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖥️",
        "emoticons": [],
        "keywords": [
            "computer",
            "desktop"
        ],
        "name": "desktop computer",
        "shortcodes": [
            ":desktop_computer:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖨️",
        "emoticons": [],
        "keywords": [
            "computer",
            "printer"
        ],
        "name": "printer",
        "shortcodes": [
            ":printer:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⌨️",
        "emoticons": [],
        "keywords": [
            "computer",
            "keyboard"
        ],
        "name": "keyboard",
        "shortcodes": [
            ":keyboard:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖱️",
        "emoticons": [],
        "keywords": [
            "computer",
            "computer mouse"
        ],
        "name": "computer mouse",
        "shortcodes": [
            ":computer_mouse:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖲️",
        "emoticons": [],
        "keywords": [
            "computer",
            "trackball"
        ],
        "name": "trackball",
        "shortcodes": [
            ":trackball:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💽",
        "emoticons": [],
        "keywords": [
            "computer",
            "disk",
            "minidisk",
            "optical"
        ],
        "name": "computer disk",
        "shortcodes": [
            ":computer_disk:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💾",
        "emoticons": [],
        "keywords": [
            "computer",
            "disk",
            "diskette",
            "floppy"
        ],
        "name": "floppy disk",
        "shortcodes": [
            ":floppy_disk:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💿",
        "emoticons": [],
        "keywords": [
            "CD",
            "computer",
            "disk",
            "optical"
        ],
        "name": "optical disk",
        "shortcodes": [
            ":optical_disk:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📀",
        "emoticons": [],
        "keywords": [
            "blu-ray",
            "computer",
            "disk",
            "dvd",
            "DVD",
            "optical",
            "Blu-ray"
        ],
        "name": "dvd",
        "shortcodes": [
            ":dvd:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧮",
        "emoticons": [],
        "keywords": [
            "abacus",
            "calculation"
        ],
        "name": "abacus",
        "shortcodes": [
            ":abacus:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎥",
        "emoticons": [],
        "keywords": [
            "camera",
            "cinema",
            "movie"
        ],
        "name": "movie camera",
        "shortcodes": [
            ":movie_camera:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎞️",
        "emoticons": [],
        "keywords": [
            "cinema",
            "film",
            "frames",
            "movie"
        ],
        "name": "film frames",
        "shortcodes": [
            ":film_frames:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📽️",
        "emoticons": [],
        "keywords": [
            "cinema",
            "film",
            "movie",
            "projector",
            "video"
        ],
        "name": "film projector",
        "shortcodes": [
            ":film_projector:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🎬",
        "emoticons": [],
        "keywords": [
            "clapper",
            "clapper board",
            "clapperboard",
            "film",
            "movie"
        ],
        "name": "clapper board",
        "shortcodes": [
            ":clapper_board:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📺",
        "emoticons": [],
        "keywords": [
            "television",
            "TV",
            "video",
            "tv"
        ],
        "name": "television",
        "shortcodes": [
            ":television:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📷",
        "emoticons": [],
        "keywords": [
            "camera",
            "video"
        ],
        "name": "camera",
        "shortcodes": [
            ":camera:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📸",
        "emoticons": [],
        "keywords": [
            "camera",
            "camera with flash",
            "flash",
            "video"
        ],
        "name": "camera with flash",
        "shortcodes": [
            ":camera_with_flash:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📹",
        "emoticons": [],
        "keywords": [
            "camera",
            "video"
        ],
        "name": "video camera",
        "shortcodes": [
            ":video_camera:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📼",
        "emoticons": [],
        "keywords": [
            "tape",
            "VHS",
            "video",
            "videocassette",
            "vhs"
        ],
        "name": "videocassette",
        "shortcodes": [
            ":videocassette:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔍",
        "emoticons": [],
        "keywords": [
            "glass",
            "magnifying",
            "magnifying glass tilted left",
            "search",
            "tool"
        ],
        "name": "magnifying glass tilted left",
        "shortcodes": [
            ":magnifying_glass_tilted_left:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔎",
        "emoticons": [],
        "keywords": [
            "glass",
            "magnifying",
            "magnifying glass tilted right",
            "search",
            "tool"
        ],
        "name": "magnifying glass tilted right",
        "shortcodes": [
            ":magnifying_glass_tilted_right:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🕯️",
        "emoticons": [],
        "keywords": [
            "candle",
            "light"
        ],
        "name": "candle",
        "shortcodes": [
            ":candle:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💡",
        "emoticons": [],
        "keywords": [
            "bulb",
            "comic",
            "electric",
            "globe",
            "idea",
            "light"
        ],
        "name": "light bulb",
        "shortcodes": [
            ":light_bulb:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔦",
        "emoticons": [],
        "keywords": [
            "electric",
            "flashlight",
            "light",
            "tool",
            "torch"
        ],
        "name": "flashlight",
        "shortcodes": [
            ":flashlight:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🏮",
        "emoticons": [],
        "keywords": [
            "bar",
            "lantern",
            "light",
            "red",
            "red paper lantern"
        ],
        "name": "red paper lantern",
        "shortcodes": [
            ":red_paper_lantern:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🪔",
        "emoticons": [],
        "keywords": [
            "diya",
            "lamp",
            "oil"
        ],
        "name": "diya lamp",
        "shortcodes": [
            ":diya_lamp:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📔",
        "emoticons": [],
        "keywords": [
            "book",
            "cover",
            "decorated",
            "notebook",
            "notebook with decorative cover"
        ],
        "name": "notebook with decorative cover",
        "shortcodes": [
            ":notebook_with_decorative_cover:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📕",
        "emoticons": [],
        "keywords": [
            "book",
            "closed"
        ],
        "name": "closed book",
        "shortcodes": [
            ":closed_book:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📖",
        "emoticons": [],
        "keywords": [
            "book",
            "open"
        ],
        "name": "open book",
        "shortcodes": [
            ":open_book:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📗",
        "emoticons": [],
        "keywords": [
            "book",
            "green"
        ],
        "name": "green book",
        "shortcodes": [
            ":green_book:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📘",
        "emoticons": [],
        "keywords": [
            "blue",
            "book"
        ],
        "name": "blue book",
        "shortcodes": [
            ":blue_book:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📙",
        "emoticons": [],
        "keywords": [
            "book",
            "orange"
        ],
        "name": "orange book",
        "shortcodes": [
            ":orange_book:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📚",
        "emoticons": [],
        "keywords": [
            "book",
            "books"
        ],
        "name": "books",
        "shortcodes": [
            ":books:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📓",
        "emoticons": [],
        "keywords": [
            "notebook"
        ],
        "name": "notebook",
        "shortcodes": [
            ":notebook:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📒",
        "emoticons": [],
        "keywords": [
            "ledger",
            "notebook"
        ],
        "name": "ledger",
        "shortcodes": [
            ":ledger:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📃",
        "emoticons": [],
        "keywords": [
            "curl",
            "document",
            "page",
            "page with curl"
        ],
        "name": "page with curl",
        "shortcodes": [
            ":page_with_curl:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📜",
        "emoticons": [],
        "keywords": [
            "paper",
            "scroll"
        ],
        "name": "scroll",
        "shortcodes": [
            ":scroll:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📄",
        "emoticons": [],
        "keywords": [
            "document",
            "page",
            "page facing up"
        ],
        "name": "page facing up",
        "shortcodes": [
            ":page_facing_up:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📰",
        "emoticons": [],
        "keywords": [
            "news",
            "newspaper",
            "paper"
        ],
        "name": "newspaper",
        "shortcodes": [
            ":newspaper:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗞️",
        "emoticons": [],
        "keywords": [
            "news",
            "newspaper",
            "paper",
            "rolled",
            "rolled-up newspaper"
        ],
        "name": "rolled-up newspaper",
        "shortcodes": [
            ":rolled-up_newspaper:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📑",
        "emoticons": [],
        "keywords": [
            "bookmark",
            "mark",
            "marker",
            "tabs"
        ],
        "name": "bookmark tabs",
        "shortcodes": [
            ":bookmark_tabs:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔖",
        "emoticons": [],
        "keywords": [
            "bookmark",
            "mark"
        ],
        "name": "bookmark",
        "shortcodes": [
            ":bookmark:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🏷️",
        "emoticons": [],
        "keywords": [
            "label"
        ],
        "name": "label",
        "shortcodes": [
            ":label:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💰",
        "emoticons": [],
        "keywords": [
            "bag",
            "dollar",
            "money",
            "moneybag"
        ],
        "name": "money bag",
        "shortcodes": [
            ":money_bag:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💴",
        "emoticons": [],
        "keywords": [
            "banknote",
            "bill",
            "currency",
            "money",
            "note",
            "yen"
        ],
        "name": "yen banknote",
        "shortcodes": [
            ":yen_banknote:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💵",
        "emoticons": [],
        "keywords": [
            "banknote",
            "bill",
            "currency",
            "dollar",
            "money",
            "note"
        ],
        "name": "dollar banknote",
        "shortcodes": [
            ":dollar_banknote:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💶",
        "emoticons": [],
        "keywords": [
            "banknote",
            "bill",
            "currency",
            "euro",
            "money",
            "note"
        ],
        "name": "euro banknote",
        "shortcodes": [
            ":euro_banknote:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💷",
        "emoticons": [],
        "keywords": [
            "banknote",
            "bill",
            "currency",
            "money",
            "note",
            "pound",
            "sterling"
        ],
        "name": "pound banknote",
        "shortcodes": [
            ":pound_banknote:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💸",
        "emoticons": [],
        "keywords": [
            "banknote",
            "bill",
            "fly",
            "money",
            "money with wings",
            "wings"
        ],
        "name": "money with wings",
        "shortcodes": [
            ":money_with_wings:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💳",
        "emoticons": [],
        "keywords": [
            "card",
            "credit",
            "money"
        ],
        "name": "credit card",
        "shortcodes": [
            ":credit_card:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧾",
        "emoticons": [],
        "keywords": [
            "accounting",
            "bookkeeping",
            "evidence",
            "proof",
            "receipt"
        ],
        "name": "receipt",
        "shortcodes": [
            ":receipt:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💹",
        "emoticons": [],
        "keywords": [
            "chart",
            "chart increasing with yen",
            "graph",
            "graph increasing with yen",
            "growth",
            "money",
            "yen"
        ],
        "name": "chart increasing with yen",
        "shortcodes": [
            ":chart_increasing_with_yen:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "✉️",
        "emoticons": [],
        "keywords": [
            "email",
            "envelope",
            "letter",
            "e-mail"
        ],
        "name": "envelope",
        "shortcodes": [
            ":envelope:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📧",
        "emoticons": [],
        "keywords": [
            "e-mail",
            "email",
            "letter",
            "mail"
        ],
        "name": "e-mail",
        "shortcodes": [
            ":e-mail:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📨",
        "emoticons": [],
        "keywords": [
            "e-mail",
            "email",
            "envelope",
            "incoming",
            "letter",
            "receive"
        ],
        "name": "incoming envelope",
        "shortcodes": [
            ":incoming_envelope:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📩",
        "emoticons": [],
        "keywords": [
            "arrow",
            "e-mail",
            "email",
            "envelope",
            "envelope with arrow",
            "outgoing"
        ],
        "name": "envelope with arrow",
        "shortcodes": [
            ":envelope_with_arrow:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📤",
        "emoticons": [],
        "keywords": [
            "box",
            "letter",
            "mail",
            "out tray",
            "outbox",
            "sent",
            "tray"
        ],
        "name": "outbox tray",
        "shortcodes": [
            ":outbox_tray:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📥",
        "emoticons": [],
        "keywords": [
            "box",
            "in tray",
            "inbox",
            "letter",
            "mail",
            "receive",
            "tray"
        ],
        "name": "inbox tray",
        "shortcodes": [
            ":inbox_tray:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📦",
        "emoticons": [],
        "keywords": [
            "box",
            "package",
            "parcel"
        ],
        "name": "package",
        "shortcodes": [
            ":package:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📫",
        "emoticons": [],
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
        ],
        "name": "closed mailbox with raised flag",
        "shortcodes": [
            ":closed_mailbox_with_raised_flag:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📪",
        "emoticons": [],
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
        ],
        "name": "closed mailbox with lowered flag",
        "shortcodes": [
            ":closed_mailbox_with_lowered_flag:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📬",
        "emoticons": [],
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
        ],
        "name": "open mailbox with raised flag",
        "shortcodes": [
            ":open_mailbox_with_raised_flag:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📭",
        "emoticons": [],
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
        ],
        "name": "open mailbox with lowered flag",
        "shortcodes": [
            ":open_mailbox_with_lowered_flag:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📮",
        "emoticons": [],
        "keywords": [
            "mail",
            "mailbox",
            "postbox",
            "post",
            "post box"
        ],
        "name": "postbox",
        "shortcodes": [
            ":postbox:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗳️",
        "emoticons": [],
        "keywords": [
            "ballot",
            "ballot box with ballot",
            "box"
        ],
        "name": "ballot box with ballot",
        "shortcodes": [
            ":ballot_box_with_ballot:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "✏️",
        "emoticons": [],
        "keywords": [
            "pencil"
        ],
        "name": "pencil",
        "shortcodes": [
            ":pencil:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "✒️",
        "emoticons": [],
        "keywords": [
            "black nib",
            "nib",
            "pen"
        ],
        "name": "black nib",
        "shortcodes": [
            ":black_nib:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖋️",
        "emoticons": [],
        "keywords": [
            "fountain",
            "pen"
        ],
        "name": "fountain pen",
        "shortcodes": [
            ":fountain_pen:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖊️",
        "emoticons": [],
        "keywords": [
            "ballpoint",
            "pen"
        ],
        "name": "pen",
        "shortcodes": [
            ":pen:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖌️",
        "emoticons": [],
        "keywords": [
            "paintbrush",
            "painting"
        ],
        "name": "paintbrush",
        "shortcodes": [
            ":paintbrush:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖍️",
        "emoticons": [],
        "keywords": [
            "crayon"
        ],
        "name": "crayon",
        "shortcodes": [
            ":crayon:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📝",
        "emoticons": [],
        "keywords": [
            "memo",
            "pencil"
        ],
        "name": "memo",
        "shortcodes": [
            ":memo:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💼",
        "emoticons": [],
        "keywords": [
            "briefcase"
        ],
        "name": "briefcase",
        "shortcodes": [
            ":briefcase:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📁",
        "emoticons": [],
        "keywords": [
            "file",
            "folder"
        ],
        "name": "file folder",
        "shortcodes": [
            ":file_folder:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📂",
        "emoticons": [],
        "keywords": [
            "file",
            "folder",
            "open"
        ],
        "name": "open file folder",
        "shortcodes": [
            ":open_file_folder:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗂️",
        "emoticons": [],
        "keywords": [
            "card",
            "dividers",
            "index"
        ],
        "name": "card index dividers",
        "shortcodes": [
            ":card_index_dividers:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📅",
        "emoticons": [],
        "keywords": [
            "calendar",
            "date"
        ],
        "name": "calendar",
        "shortcodes": [
            ":calendar:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📆",
        "emoticons": [],
        "keywords": [
            "calendar",
            "tear-off calendar"
        ],
        "name": "tear-off calendar",
        "shortcodes": [
            ":tear-off_calendar:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗒️",
        "emoticons": [],
        "keywords": [
            "note",
            "pad",
            "spiral",
            "spiral notepad"
        ],
        "name": "spiral notepad",
        "shortcodes": [
            ":spiral_notepad:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗓️",
        "emoticons": [],
        "keywords": [
            "calendar",
            "pad",
            "spiral"
        ],
        "name": "spiral calendar",
        "shortcodes": [
            ":spiral_calendar:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📇",
        "emoticons": [],
        "keywords": [
            "card",
            "index",
            "rolodex"
        ],
        "name": "card index",
        "shortcodes": [
            ":card_index:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📈",
        "emoticons": [],
        "keywords": [
            "chart",
            "chart increasing",
            "graph",
            "graph increasing",
            "growth",
            "trend",
            "upward"
        ],
        "name": "chart increasing",
        "shortcodes": [
            ":chart_increasing:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📉",
        "emoticons": [],
        "keywords": [
            "chart",
            "chart decreasing",
            "down",
            "graph",
            "graph decreasing",
            "trend"
        ],
        "name": "chart decreasing",
        "shortcodes": [
            ":chart_decreasing:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📊",
        "emoticons": [],
        "keywords": [
            "bar",
            "chart",
            "graph"
        ],
        "name": "bar chart",
        "shortcodes": [
            ":bar_chart:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📋",
        "emoticons": [],
        "keywords": [
            "clipboard"
        ],
        "name": "clipboard",
        "shortcodes": [
            ":clipboard:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📌",
        "emoticons": [],
        "keywords": [
            "drawing-pin",
            "pin",
            "pushpin"
        ],
        "name": "pushpin",
        "shortcodes": [
            ":pushpin:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📍",
        "emoticons": [],
        "keywords": [
            "pin",
            "pushpin",
            "round drawing-pin",
            "round pushpin"
        ],
        "name": "round pushpin",
        "shortcodes": [
            ":round_pushpin:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📎",
        "emoticons": [],
        "keywords": [
            "paperclip"
        ],
        "name": "paperclip",
        "shortcodes": [
            ":paperclip:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🖇️",
        "emoticons": [],
        "keywords": [
            "link",
            "linked paperclips",
            "paperclip"
        ],
        "name": "linked paperclips",
        "shortcodes": [
            ":linked_paperclips:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📏",
        "emoticons": [],
        "keywords": [
            "ruler",
            "straight edge",
            "straight ruler"
        ],
        "name": "straight ruler",
        "shortcodes": [
            ":straight_ruler:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📐",
        "emoticons": [],
        "keywords": [
            "ruler",
            "set",
            "triangle",
            "triangular ruler",
            "set square"
        ],
        "name": "triangular ruler",
        "shortcodes": [
            ":triangular_ruler:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "✂️",
        "emoticons": [],
        "keywords": [
            "cutting",
            "scissors",
            "tool"
        ],
        "name": "scissors",
        "shortcodes": [
            ":scissors:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗃️",
        "emoticons": [],
        "keywords": [
            "box",
            "card",
            "file"
        ],
        "name": "card file box",
        "shortcodes": [
            ":card_file_box:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗄️",
        "emoticons": [],
        "keywords": [
            "cabinet",
            "file",
            "filing"
        ],
        "name": "file cabinet",
        "shortcodes": [
            ":file_cabinet:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗑️",
        "emoticons": [],
        "keywords": [
            "wastebasket"
        ],
        "name": "wastebasket",
        "shortcodes": [
            ":wastebasket:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔒",
        "emoticons": [],
        "keywords": [
            "closed",
            "locked",
            "padlock"
        ],
        "name": "locked",
        "shortcodes": [
            ":locked:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔓",
        "emoticons": [],
        "keywords": [
            "lock",
            "open",
            "unlock",
            "unlocked",
            "padlock"
        ],
        "name": "unlocked",
        "shortcodes": [
            ":unlocked:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔏",
        "emoticons": [],
        "keywords": [
            "ink",
            "lock",
            "locked with pen",
            "nib",
            "pen",
            "privacy"
        ],
        "name": "locked with pen",
        "shortcodes": [
            ":locked_with_pen:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔐",
        "emoticons": [],
        "keywords": [
            "closed",
            "key",
            "lock",
            "locked with key",
            "secure"
        ],
        "name": "locked with key",
        "shortcodes": [
            ":locked_with_key:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔑",
        "emoticons": [],
        "keywords": [
            "key",
            "lock",
            "password"
        ],
        "name": "key",
        "shortcodes": [
            ":key:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗝️",
        "emoticons": [],
        "keywords": [
            "clue",
            "key",
            "lock",
            "old"
        ],
        "name": "old key",
        "shortcodes": [
            ":old_key:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔨",
        "emoticons": [],
        "keywords": [
            "hammer",
            "tool"
        ],
        "name": "hammer",
        "shortcodes": [
            ":hammer:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🪓",
        "emoticons": [],
        "keywords": [
            "axe",
            "chop",
            "hatchet",
            "split",
            "wood"
        ],
        "name": "axe",
        "shortcodes": [
            ":axe:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⛏️",
        "emoticons": [],
        "keywords": [
            "mining",
            "pick",
            "tool"
        ],
        "name": "pick",
        "shortcodes": [
            ":pick:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⚒️",
        "emoticons": [],
        "keywords": [
            "hammer",
            "hammer and pick",
            "pick",
            "tool"
        ],
        "name": "hammer and pick",
        "shortcodes": [
            ":hammer_and_pick:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🛠️",
        "emoticons": [],
        "keywords": [
            "hammer",
            "hammer and spanner",
            "hammer and wrench",
            "spanner",
            "tool",
            "wrench"
        ],
        "name": "hammer and wrench",
        "shortcodes": [
            ":hammer_and_wrench:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗡️",
        "emoticons": [],
        "keywords": [
            "dagger",
            "knife",
            "weapon"
        ],
        "name": "dagger",
        "shortcodes": [
            ":dagger:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⚔️",
        "emoticons": [],
        "keywords": [
            "crossed",
            "swords",
            "weapon"
        ],
        "name": "crossed swords",
        "shortcodes": [
            ":crossed_swords:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔫",
        "emoticons": [],
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
        ],
        "name": "water pistol",
        "shortcodes": [
            ":water_pistol:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🏹",
        "emoticons": [],
        "keywords": [
            "archer",
            "arrow",
            "bow",
            "bow and arrow",
            "Sagittarius",
            "zodiac"
        ],
        "name": "bow and arrow",
        "shortcodes": [
            ":bow_and_arrow:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🛡️",
        "emoticons": [],
        "keywords": [
            "shield",
            "weapon"
        ],
        "name": "shield",
        "shortcodes": [
            ":shield:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔧",
        "emoticons": [],
        "keywords": [
            "spanner",
            "tool",
            "wrench"
        ],
        "name": "wrench",
        "shortcodes": [
            ":wrench:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔩",
        "emoticons": [],
        "keywords": [
            "bolt",
            "nut",
            "nut and bolt",
            "tool"
        ],
        "name": "nut and bolt",
        "shortcodes": [
            ":nut_and_bolt:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⚙️",
        "emoticons": [],
        "keywords": [
            "cog",
            "cogwheel",
            "gear",
            "tool"
        ],
        "name": "gear",
        "shortcodes": [
            ":gear:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗜️",
        "emoticons": [],
        "keywords": [
            "clamp",
            "compress",
            "tool",
            "vice"
        ],
        "name": "clamp",
        "shortcodes": [
            ":clamp:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⚖️",
        "emoticons": [],
        "keywords": [
            "balance",
            "justice",
            "Libra",
            "scale",
            "zodiac"
        ],
        "name": "balance scale",
        "shortcodes": [
            ":balance_scale:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🦯",
        "emoticons": [],
        "keywords": [
            "accessibility",
            "long mobility cane",
            "white cane",
            "blind",
            "guide cane"
        ],
        "name": "white cane",
        "shortcodes": [
            ":white_cane:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔗",
        "emoticons": [],
        "keywords": [
            "link"
        ],
        "name": "link",
        "shortcodes": [
            ":link:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⛓️",
        "emoticons": [],
        "keywords": [
            "chain",
            "chains"
        ],
        "name": "chains",
        "shortcodes": [
            ":chains:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧰",
        "emoticons": [],
        "keywords": [
            "chest",
            "mechanic",
            "tool",
            "toolbox"
        ],
        "name": "toolbox",
        "shortcodes": [
            ":toolbox:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧲",
        "emoticons": [],
        "keywords": [
            "attraction",
            "horseshoe",
            "magnet",
            "magnetic"
        ],
        "name": "magnet",
        "shortcodes": [
            ":magnet:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⚗️",
        "emoticons": [],
        "keywords": [
            "alembic",
            "chemistry",
            "tool"
        ],
        "name": "alembic",
        "shortcodes": [
            ":alembic:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧪",
        "emoticons": [],
        "keywords": [
            "chemist",
            "chemistry",
            "experiment",
            "lab",
            "science",
            "test tube"
        ],
        "name": "test tube",
        "shortcodes": [
            ":test_tube:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧫",
        "emoticons": [],
        "keywords": [
            "bacteria",
            "biologist",
            "biology",
            "culture",
            "lab",
            "petri dish"
        ],
        "name": "petri dish",
        "shortcodes": [
            ":petri_dish:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧬",
        "emoticons": [],
        "keywords": [
            "biologist",
            "dna",
            "DNA",
            "evolution",
            "gene",
            "genetics",
            "life"
        ],
        "name": "dna",
        "shortcodes": [
            ":dna:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔬",
        "emoticons": [],
        "keywords": [
            "microscope",
            "science",
            "tool"
        ],
        "name": "microscope",
        "shortcodes": [
            ":microscope:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🔭",
        "emoticons": [],
        "keywords": [
            "science",
            "telescope",
            "tool"
        ],
        "name": "telescope",
        "shortcodes": [
            ":telescope:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "📡",
        "emoticons": [],
        "keywords": [
            "antenna",
            "dish",
            "satellite"
        ],
        "name": "satellite antenna",
        "shortcodes": [
            ":satellite_antenna:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💉",
        "emoticons": [],
        "keywords": [
            "medicine",
            "needle",
            "shot",
            "sick",
            "syringe",
            "ill",
            "injection"
        ],
        "name": "syringe",
        "shortcodes": [
            ":syringe:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🩸",
        "emoticons": [],
        "keywords": [
            "bleed",
            "blood donation",
            "drop of blood",
            "injury",
            "medicine",
            "menstruation"
        ],
        "name": "drop of blood",
        "shortcodes": [
            ":drop_of_blood:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "💊",
        "emoticons": [],
        "keywords": [
            "doctor",
            "medicine",
            "pill",
            "sick"
        ],
        "name": "pill",
        "shortcodes": [
            ":pill:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🩹",
        "emoticons": [],
        "keywords": [
            "adhesive bandage",
            "bandage",
            "bandaid",
            "dressing",
            "injury",
            "plaster",
            "sticking plaster"
        ],
        "name": "adhesive bandage",
        "shortcodes": [
            ":adhesive_bandage:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🩺",
        "emoticons": [],
        "keywords": [
            "doctor",
            "heart",
            "medicine",
            "stethoscope"
        ],
        "name": "stethoscope",
        "shortcodes": [
            ":stethoscope:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🚪",
        "emoticons": [],
        "keywords": [
            "door"
        ],
        "name": "door",
        "shortcodes": [
            ":door:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🛏️",
        "emoticons": [],
        "keywords": [
            "bed",
            "hotel",
            "sleep"
        ],
        "name": "bed",
        "shortcodes": [
            ":bed:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🛋️",
        "emoticons": [],
        "keywords": [
            "couch",
            "couch and lamp",
            "hotel",
            "lamp",
            "sofa",
            "sofa and lamp"
        ],
        "name": "couch and lamp",
        "shortcodes": [
            ":couch_and_lamp:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🪑",
        "emoticons": [],
        "keywords": [
            "chair",
            "seat",
            "sit"
        ],
        "name": "chair",
        "shortcodes": [
            ":chair:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🚽",
        "emoticons": [],
        "keywords": [
            "facilities",
            "loo",
            "toilet",
            "WC",
            "lavatory"
        ],
        "name": "toilet",
        "shortcodes": [
            ":toilet:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🚿",
        "emoticons": [],
        "keywords": [
            "shower",
            "water"
        ],
        "name": "shower",
        "shortcodes": [
            ":shower:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🛁",
        "emoticons": [],
        "keywords": [
            "bath",
            "bathtub"
        ],
        "name": "bathtub",
        "shortcodes": [
            ":bathtub:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🪒",
        "emoticons": [],
        "keywords": [
            "razor",
            "sharp",
            "shave",
            "cut-throat"
        ],
        "name": "razor",
        "shortcodes": [
            ":razor:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧴",
        "emoticons": [],
        "keywords": [
            "lotion",
            "lotion bottle",
            "moisturizer",
            "shampoo",
            "sunscreen",
            "moisturiser"
        ],
        "name": "lotion bottle",
        "shortcodes": [
            ":lotion_bottle:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧷",
        "emoticons": [],
        "keywords": [
            "nappy",
            "punk rock",
            "safety pin",
            "diaper"
        ],
        "name": "safety pin",
        "shortcodes": [
            ":safety_pin:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧹",
        "emoticons": [],
        "keywords": [
            "broom",
            "cleaning",
            "sweeping",
            "witch"
        ],
        "name": "broom",
        "shortcodes": [
            ":broom:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧺",
        "emoticons": [],
        "keywords": [
            "basket",
            "farming",
            "laundry",
            "picnic"
        ],
        "name": "basket",
        "shortcodes": [
            ":basket:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧻",
        "emoticons": [],
        "keywords": [
            "paper towels",
            "roll of paper",
            "toilet paper",
            "toilet roll"
        ],
        "name": "roll of paper",
        "shortcodes": [
            ":roll_of_paper:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧼",
        "emoticons": [],
        "keywords": [
            "bar",
            "bathing",
            "cleaning",
            "lather",
            "soap",
            "soapdish"
        ],
        "name": "soap",
        "shortcodes": [
            ":soap:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧽",
        "emoticons": [],
        "keywords": [
            "absorbing",
            "cleaning",
            "porous",
            "sponge"
        ],
        "name": "sponge",
        "shortcodes": [
            ":sponge:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🧯",
        "emoticons": [],
        "keywords": [
            "extinguish",
            "fire",
            "fire extinguisher",
            "quench"
        ],
        "name": "fire extinguisher",
        "shortcodes": [
            ":fire_extinguisher:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🛒",
        "emoticons": [],
        "keywords": [
            "cart",
            "shopping",
            "trolley",
            "basket"
        ],
        "name": "shopping cart",
        "shortcodes": [
            ":shopping_cart:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🚬",
        "emoticons": [],
        "keywords": [
            "cigarette",
            "smoking"
        ],
        "name": "cigarette",
        "shortcodes": [
            ":cigarette:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⚰️",
        "emoticons": [],
        "keywords": [
            "coffin",
            "death"
        ],
        "name": "coffin",
        "shortcodes": [
            ":coffin:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "⚱️",
        "emoticons": [],
        "keywords": [
            "ashes",
            "death",
            "funeral",
            "urn"
        ],
        "name": "funeral urn",
        "shortcodes": [
            ":funeral_urn:"
        ]
    },
    {
        "category": "Objects",
        "codepoints": "🗿",
        "emoticons": [],
        "keywords": [
            "face",
            "moai",
            "moyai",
            "statue"
        ],
        "name": "moai",
        "shortcodes": [
            ":moai:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏧",
        "emoticons": [],
        "keywords": [
            "ATM",
            "ATM sign",
            "automated",
            "bank",
            "teller"
        ],
        "name": "ATM sign",
        "shortcodes": [
            ":ATM_sign:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚮",
        "emoticons": [],
        "keywords": [
            "litter",
            "litter bin",
            "litter in bin sign",
            "garbage",
            "trash"
        ],
        "name": "litter in bin sign",
        "shortcodes": [
            ":litter_in_bin_sign:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚰",
        "emoticons": [],
        "keywords": [
            "drinking",
            "potable",
            "water"
        ],
        "name": "potable water",
        "shortcodes": [
            ":potable_water:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♿",
        "emoticons": [],
        "keywords": [
            "access",
            "disabled access",
            "wheelchair symbol"
        ],
        "name": "wheelchair symbol",
        "shortcodes": [
            ":wheelchair_symbol:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚹",
        "emoticons": [],
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
        ],
        "name": "men’s room",
        "shortcodes": [
            ":men’s_room:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚺",
        "emoticons": [],
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
        ],
        "name": "women’s room",
        "shortcodes": [
            ":women’s_room:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚻",
        "emoticons": [],
        "keywords": [
            "bathroom",
            "lavatory",
            "restroom",
            "toilet",
            "WC",
            "washroom"
        ],
        "name": "restroom",
        "shortcodes": [
            ":restroom:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚼",
        "emoticons": [],
        "keywords": [
            "baby",
            "baby symbol",
            "change room",
            "changing"
        ],
        "name": "baby symbol",
        "shortcodes": [
            ":baby_symbol:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚾",
        "emoticons": [],
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
        ],
        "name": "water closet",
        "shortcodes": [
            ":water_closet:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🛂",
        "emoticons": [],
        "keywords": [
            "border",
            "control",
            "passport",
            "security"
        ],
        "name": "passport control",
        "shortcodes": [
            ":passport_control:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🛃",
        "emoticons": [],
        "keywords": [
            "customs"
        ],
        "name": "customs",
        "shortcodes": [
            ":customs:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🛄",
        "emoticons": [],
        "keywords": [
            "baggage",
            "claim"
        ],
        "name": "baggage claim",
        "shortcodes": [
            ":baggage_claim:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🛅",
        "emoticons": [],
        "keywords": [
            "baggage",
            "left luggage",
            "locker",
            "luggage"
        ],
        "name": "left luggage",
        "shortcodes": [
            ":left_luggage:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⚠️",
        "emoticons": [],
        "keywords": [
            "warning"
        ],
        "name": "warning",
        "shortcodes": [
            ":warning:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚸",
        "emoticons": [],
        "keywords": [
            "child",
            "children crossing",
            "crossing",
            "pedestrian",
            "traffic"
        ],
        "name": "children crossing",
        "shortcodes": [
            ":children_crossing:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⛔",
        "emoticons": [],
        "keywords": [
            "denied",
            "entry",
            "forbidden",
            "no",
            "prohibited",
            "traffic",
            "not"
        ],
        "name": "no entry",
        "shortcodes": [
            ":no_entry:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚫",
        "emoticons": [],
        "keywords": [
            "denied",
            "entry",
            "forbidden",
            "no",
            "prohibited",
            "not"
        ],
        "name": "prohibited",
        "shortcodes": [
            ":prohibited:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚳",
        "emoticons": [],
        "keywords": [
            "bicycle",
            "bike",
            "forbidden",
            "no",
            "no bicycles",
            "prohibited"
        ],
        "name": "no bicycles",
        "shortcodes": [
            ":no_bicycles:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚭",
        "emoticons": [],
        "keywords": [
            "denied",
            "forbidden",
            "no",
            "prohibited",
            "smoking",
            "not"
        ],
        "name": "no smoking",
        "shortcodes": [
            ":no_smoking:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚯",
        "emoticons": [],
        "keywords": [
            "denied",
            "forbidden",
            "litter",
            "no",
            "no littering",
            "prohibited",
            "not"
        ],
        "name": "no littering",
        "shortcodes": [
            ":no_littering:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚱",
        "emoticons": [],
        "keywords": [
            "non-drinkable water",
            "non-drinking",
            "non-potable",
            "water"
        ],
        "name": "non-potable water",
        "shortcodes": [
            ":non-potable_water:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚷",
        "emoticons": [],
        "keywords": [
            "denied",
            "forbidden",
            "no",
            "no pedestrians",
            "pedestrian",
            "prohibited",
            "not"
        ],
        "name": "no pedestrians",
        "shortcodes": [
            ":no_pedestrians:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "📵",
        "emoticons": [],
        "keywords": [
            "cell",
            "forbidden",
            "mobile",
            "no",
            "no mobile phones",
            "phone"
        ],
        "name": "no mobile phones",
        "shortcodes": [
            ":no_mobile_phones:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔞",
        "emoticons": [],
        "keywords": [
            "18",
            "age restriction",
            "eighteen",
            "no one under eighteen",
            "prohibited",
            "underage"
        ],
        "name": "no one under eighteen",
        "shortcodes": [
            ":no_one_under_eighteen:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "☢️",
        "emoticons": [],
        "keywords": [
            "radioactive",
            "sign"
        ],
        "name": "radioactive",
        "shortcodes": [
            ":radioactive:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "☣️",
        "emoticons": [],
        "keywords": [
            "biohazard",
            "sign"
        ],
        "name": "biohazard",
        "shortcodes": [
            ":biohazard:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⬆️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "cardinal",
            "direction",
            "north",
            "up",
            "up arrow"
        ],
        "name": "up arrow",
        "shortcodes": [
            ":up_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "↗️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "direction",
            "intercardinal",
            "northeast",
            "up-right arrow"
        ],
        "name": "up-right arrow",
        "shortcodes": [
            ":up-right_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "➡️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "cardinal",
            "direction",
            "east",
            "right arrow"
        ],
        "name": "right arrow",
        "shortcodes": [
            ":right_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "↘️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "direction",
            "down-right arrow",
            "intercardinal",
            "southeast"
        ],
        "name": "down-right arrow",
        "shortcodes": [
            ":down-right_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⬇️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "cardinal",
            "direction",
            "down",
            "south"
        ],
        "name": "down arrow",
        "shortcodes": [
            ":down_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "↙️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "direction",
            "down-left arrow",
            "intercardinal",
            "southwest"
        ],
        "name": "down-left arrow",
        "shortcodes": [
            ":down-left_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⬅️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "cardinal",
            "direction",
            "left arrow",
            "west"
        ],
        "name": "left arrow",
        "shortcodes": [
            ":left_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "↖️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "direction",
            "intercardinal",
            "northwest",
            "up-left arrow"
        ],
        "name": "up-left arrow",
        "shortcodes": [
            ":up-left_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "↕️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "up-down arrow"
        ],
        "name": "up-down arrow",
        "shortcodes": [
            ":up-down_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "↔️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "left-right arrow"
        ],
        "name": "left-right arrow",
        "shortcodes": [
            ":left-right_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "↩️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "right arrow curving left"
        ],
        "name": "right arrow curving left",
        "shortcodes": [
            ":right_arrow_curving_left:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "↪️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "left arrow curving right"
        ],
        "name": "left arrow curving right",
        "shortcodes": [
            ":left_arrow_curving_right:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⤴️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "right arrow curving up"
        ],
        "name": "right arrow curving up",
        "shortcodes": [
            ":right_arrow_curving_up:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⤵️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "down",
            "right arrow curving down"
        ],
        "name": "right arrow curving down",
        "shortcodes": [
            ":right_arrow_curving_down:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔃",
        "emoticons": [],
        "keywords": [
            "arrow",
            "clockwise",
            "clockwise vertical arrows",
            "reload"
        ],
        "name": "clockwise vertical arrows",
        "shortcodes": [
            ":clockwise_vertical_arrows:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔄",
        "emoticons": [],
        "keywords": [
            "anticlockwise",
            "arrow",
            "counterclockwise",
            "counterclockwise arrows button",
            "withershins",
            "anticlockwise arrows button"
        ],
        "name": "counterclockwise arrows button",
        "shortcodes": [
            ":counterclockwise_arrows_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔙",
        "emoticons": [],
        "keywords": [
            "arrow",
            "BACK"
        ],
        "name": "BACK arrow",
        "shortcodes": [
            ":BACK_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔚",
        "emoticons": [],
        "keywords": [
            "arrow",
            "END"
        ],
        "name": "END arrow",
        "shortcodes": [
            ":END_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔛",
        "emoticons": [],
        "keywords": [
            "arrow",
            "mark",
            "ON",
            "ON!"
        ],
        "name": "ON! arrow",
        "shortcodes": [
            ":ON!_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔜",
        "emoticons": [],
        "keywords": [
            "arrow",
            "SOON"
        ],
        "name": "SOON arrow",
        "shortcodes": [
            ":SOON_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔝",
        "emoticons": [],
        "keywords": [
            "arrow",
            "TOP",
            "up"
        ],
        "name": "TOP arrow",
        "shortcodes": [
            ":TOP_arrow:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🛐",
        "emoticons": [],
        "keywords": [
            "place of worship",
            "religion",
            "worship"
        ],
        "name": "place of worship",
        "shortcodes": [
            ":place_of_worship:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⚛️",
        "emoticons": [],
        "keywords": [
            "atheist",
            "atom",
            "atom symbol"
        ],
        "name": "atom symbol",
        "shortcodes": [
            ":atom_symbol:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🕉️",
        "emoticons": [],
        "keywords": [
            "Hindu",
            "om",
            "religion"
        ],
        "name": "om",
        "shortcodes": [
            ":om:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "✡️",
        "emoticons": [],
        "keywords": [
            "David",
            "Jew",
            "Jewish",
            "religion",
            "star",
            "star of David",
            "Judaism",
            "Star of David"
        ],
        "name": "star of David",
        "shortcodes": [
            ":star_of_David:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "☸️",
        "emoticons": [],
        "keywords": [
            "Buddhist",
            "dharma",
            "religion",
            "wheel",
            "wheel of dharma"
        ],
        "name": "wheel of dharma",
        "shortcodes": [
            ":wheel_of_dharma:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "☯️",
        "emoticons": [],
        "keywords": [
            "religion",
            "tao",
            "taoist",
            "yang",
            "yin",
            "Tao",
            "Taoist"
        ],
        "name": "yin yang",
        "shortcodes": [
            ":yin_yang:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "✝️",
        "emoticons": [],
        "keywords": [
            "Christian",
            "cross",
            "religion",
            "latin cross",
            "Latin cross"
        ],
        "name": "latin cross",
        "shortcodes": [
            ":latin_cross:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "☦️",
        "emoticons": [],
        "keywords": [
            "Christian",
            "cross",
            "orthodox cross",
            "religion",
            "Orthodox cross"
        ],
        "name": "orthodox cross",
        "shortcodes": [
            ":orthodox_cross:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "☪️",
        "emoticons": [],
        "keywords": [
            "islam",
            "Muslim",
            "religion",
            "star and crescent",
            "Islam"
        ],
        "name": "star and crescent",
        "shortcodes": [
            ":star_and_crescent:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "☮️",
        "emoticons": [],
        "keywords": [
            "peace",
            "peace symbol"
        ],
        "name": "peace symbol",
        "shortcodes": [
            ":peace_symbol:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🕎",
        "emoticons": [],
        "keywords": [
            "candelabrum",
            "candlestick",
            "menorah",
            "religion"
        ],
        "name": "menorah",
        "shortcodes": [
            ":menorah:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔯",
        "emoticons": [],
        "keywords": [
            "dotted six-pointed star",
            "fortune",
            "star"
        ],
        "name": "dotted six-pointed star",
        "shortcodes": [
            ":dotted_six-pointed_star:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♈",
        "emoticons": [],
        "keywords": [
            "Aries",
            "ram",
            "zodiac"
        ],
        "name": "Aries",
        "shortcodes": [
            ":Aries:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♉",
        "emoticons": [],
        "keywords": [
            "bull",
            "ox",
            "Taurus",
            "zodiac"
        ],
        "name": "Taurus",
        "shortcodes": [
            ":Taurus:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♊",
        "emoticons": [],
        "keywords": [
            "Gemini",
            "twins",
            "zodiac"
        ],
        "name": "Gemini",
        "shortcodes": [
            ":Gemini:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♋",
        "emoticons": [],
        "keywords": [
            "Cancer",
            "crab",
            "zodiac"
        ],
        "name": "Cancer",
        "shortcodes": [
            ":Cancer:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♌",
        "emoticons": [],
        "keywords": [
            "Leo",
            "lion",
            "zodiac"
        ],
        "name": "Leo",
        "shortcodes": [
            ":Leo:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♍",
        "emoticons": [],
        "keywords": [
            "virgin",
            "Virgo",
            "zodiac"
        ],
        "name": "Virgo",
        "shortcodes": [
            ":Virgo:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♎",
        "emoticons": [],
        "keywords": [
            "balance",
            "justice",
            "Libra",
            "scales",
            "zodiac"
        ],
        "name": "Libra",
        "shortcodes": [
            ":Libra:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♏",
        "emoticons": [],
        "keywords": [
            "Scorpio",
            "scorpion",
            "scorpius",
            "zodiac",
            "Scorpius"
        ],
        "name": "Scorpio",
        "shortcodes": [
            ":Scorpio:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♐",
        "emoticons": [],
        "keywords": [
            "archer",
            "centaur",
            "Sagittarius",
            "zodiac"
        ],
        "name": "Sagittarius",
        "shortcodes": [
            ":Sagittarius:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♑",
        "emoticons": [],
        "keywords": [
            "Capricorn",
            "goat",
            "zodiac"
        ],
        "name": "Capricorn",
        "shortcodes": [
            ":Capricorn:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♒",
        "emoticons": [],
        "keywords": [
            "Aquarius",
            "water bearer",
            "zodiac",
            "bearer",
            "water"
        ],
        "name": "Aquarius",
        "shortcodes": [
            ":Aquarius:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♓",
        "emoticons": [],
        "keywords": [
            "fish",
            "Pisces",
            "zodiac"
        ],
        "name": "Pisces",
        "shortcodes": [
            ":Pisces:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⛎",
        "emoticons": [],
        "keywords": [
            "bearer",
            "Ophiuchus",
            "serpent",
            "snake",
            "zodiac"
        ],
        "name": "Ophiuchus",
        "shortcodes": [
            ":Ophiuchus:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔀",
        "emoticons": [],
        "keywords": [
            "arrow",
            "crossed",
            "shuffle tracks button"
        ],
        "name": "shuffle tracks button",
        "shortcodes": [
            ":shuffle_tracks_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔁",
        "emoticons": [],
        "keywords": [
            "arrow",
            "clockwise",
            "repeat",
            "repeat button"
        ],
        "name": "repeat button",
        "shortcodes": [
            ":repeat_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔂",
        "emoticons": [],
        "keywords": [
            "arrow",
            "clockwise",
            "once",
            "repeat single button"
        ],
        "name": "repeat single button",
        "shortcodes": [
            ":repeat_single_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "▶️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "play",
            "play button",
            "right",
            "triangle"
        ],
        "name": "play button",
        "shortcodes": [
            ":play_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏩",
        "emoticons": [],
        "keywords": [
            "fast forward button",
            "arrow",
            "double",
            "fast",
            "fast-forward button",
            "forward"
        ],
        "name": "fast-forward button",
        "shortcodes": [
            ":fast-forward_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏭️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "next scene",
            "next track",
            "next track button",
            "triangle"
        ],
        "name": "next track button",
        "shortcodes": [
            ":next_track_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏯️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "pause",
            "play",
            "play or pause button",
            "right",
            "triangle"
        ],
        "name": "play or pause button",
        "shortcodes": [
            ":play_or_pause_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "◀️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "left",
            "reverse",
            "reverse button",
            "triangle"
        ],
        "name": "reverse button",
        "shortcodes": [
            ":reverse_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏪",
        "emoticons": [],
        "keywords": [
            "arrow",
            "double",
            "fast reverse button",
            "rewind"
        ],
        "name": "fast reverse button",
        "shortcodes": [
            ":fast_reverse_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏮️",
        "emoticons": [],
        "keywords": [
            "arrow",
            "last track button",
            "previous scene",
            "previous track",
            "triangle"
        ],
        "name": "last track button",
        "shortcodes": [
            ":last_track_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔼",
        "emoticons": [],
        "keywords": [
            "arrow",
            "button",
            "red",
            "upwards button",
            "upward button"
        ],
        "name": "upwards button",
        "shortcodes": [
            ":upwards_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏫",
        "emoticons": [],
        "keywords": [
            "arrow",
            "double",
            "fast up button"
        ],
        "name": "fast up button",
        "shortcodes": [
            ":fast_up_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔽",
        "emoticons": [],
        "keywords": [
            "arrow",
            "button",
            "down",
            "downwards button",
            "red",
            "downward button"
        ],
        "name": "downwards button",
        "shortcodes": [
            ":downwards_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏬",
        "emoticons": [],
        "keywords": [
            "arrow",
            "double",
            "down",
            "fast down button"
        ],
        "name": "fast down button",
        "shortcodes": [
            ":fast_down_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏸️",
        "emoticons": [],
        "keywords": [
            "bar",
            "double",
            "pause",
            "pause button",
            "vertical"
        ],
        "name": "pause button",
        "shortcodes": [
            ":pause_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏹️",
        "emoticons": [],
        "keywords": [
            "square",
            "stop",
            "stop button"
        ],
        "name": "stop button",
        "shortcodes": [
            ":stop_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏺️",
        "emoticons": [],
        "keywords": [
            "circle",
            "record",
            "record button"
        ],
        "name": "record button",
        "shortcodes": [
            ":record_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⏏️",
        "emoticons": [],
        "keywords": [
            "eject",
            "eject button"
        ],
        "name": "eject button",
        "shortcodes": [
            ":eject_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🎦",
        "emoticons": [],
        "keywords": [
            "camera",
            "cinema",
            "film",
            "movie"
        ],
        "name": "cinema",
        "shortcodes": [
            ":cinema:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔅",
        "emoticons": [],
        "keywords": [
            "brightness",
            "dim",
            "dim button",
            "low"
        ],
        "name": "dim button",
        "shortcodes": [
            ":dim_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔆",
        "emoticons": [],
        "keywords": [
            "bright button",
            "brightness",
            "brightness button",
            "bright"
        ],
        "name": "bright button",
        "shortcodes": [
            ":bright_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "📶",
        "emoticons": [],
        "keywords": [
            "antenna",
            "antenna bars",
            "bar",
            "cell",
            "mobile",
            "phone"
        ],
        "name": "antenna bars",
        "shortcodes": [
            ":antenna_bars:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "📳",
        "emoticons": [],
        "keywords": [
            "cell",
            "mobile",
            "mode",
            "phone",
            "telephone",
            "vibration",
            "vibrate"
        ],
        "name": "vibration mode",
        "shortcodes": [
            ":vibration_mode:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "📴",
        "emoticons": [],
        "keywords": [
            "cell",
            "mobile",
            "off",
            "phone",
            "telephone"
        ],
        "name": "mobile phone off",
        "shortcodes": [
            ":mobile_phone_off:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♀️",
        "emoticons": [],
        "keywords": [
            "female sign",
            "woman"
        ],
        "name": "female sign",
        "shortcodes": [
            ":female_sign:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♂️",
        "emoticons": [],
        "keywords": [
            "male sign",
            "man"
        ],
        "name": "male sign",
        "shortcodes": [
            ":male_sign:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "✖️",
        "emoticons": [],
        "keywords": [
            "×",
            "cancel",
            "multiplication",
            "multiply",
            "sign",
            "x",
            "heavy multiplication sign"
        ],
        "name": "multiply",
        "shortcodes": [
            ":multiply:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "➕",
        "emoticons": [],
        "keywords": [
            "+",
            "add",
            "addition",
            "math",
            "maths",
            "plus",
            "sign"
        ],
        "name": "plus",
        "shortcodes": [
            ":plus:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "➖",
        "emoticons": [],
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
        ],
        "name": "minus",
        "shortcodes": [
            ":minus:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "➗",
        "emoticons": [],
        "keywords": [
            "÷",
            "divide",
            "division",
            "math",
            "sign"
        ],
        "name": "divide",
        "shortcodes": [
            ":divide:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♾️",
        "emoticons": [],
        "keywords": [
            "eternal",
            "forever",
            "infinity",
            "unbound",
            "universal",
            "unbounded"
        ],
        "name": "infinity",
        "shortcodes": [
            ":infinity:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "‼️",
        "emoticons": [],
        "keywords": [
            "double exclamation mark",
            "exclamation",
            "mark",
            "punctuation",
            "!",
            "!!",
            "bangbang"
        ],
        "name": "double exclamation mark",
        "shortcodes": [
            ":double_exclamation_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⁉️",
        "emoticons": [],
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
        ],
        "name": "exclamation question mark",
        "shortcodes": [
            ":exclamation_question_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "❓",
        "emoticons": [],
        "keywords": [
            "?",
            "mark",
            "punctuation",
            "question",
            "red question mark"
        ],
        "name": "red question mark",
        "shortcodes": [
            ":red_question_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "❔",
        "emoticons": [],
        "keywords": [
            "?",
            "mark",
            "outlined",
            "punctuation",
            "question",
            "white question mark"
        ],
        "name": "white question mark",
        "shortcodes": [
            ":white_question_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "❕",
        "emoticons": [],
        "keywords": [
            "!",
            "exclamation",
            "mark",
            "outlined",
            "punctuation",
            "white exclamation mark"
        ],
        "name": "white exclamation mark",
        "shortcodes": [
            ":white_exclamation_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "❗",
        "emoticons": [],
        "keywords": [
            "!",
            "exclamation",
            "mark",
            "punctuation",
            "red exclamation mark"
        ],
        "name": "red exclamation mark",
        "shortcodes": [
            ":red_exclamation_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "〰️",
        "emoticons": [],
        "keywords": [
            "dash",
            "punctuation",
            "wavy"
        ],
        "name": "wavy dash",
        "shortcodes": [
            ":wavy_dash:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "💱",
        "emoticons": [],
        "keywords": [
            "bank",
            "currency",
            "exchange",
            "money"
        ],
        "name": "currency exchange",
        "shortcodes": [
            ":currency_exchange:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "💲",
        "emoticons": [],
        "keywords": [
            "currency",
            "dollar",
            "heavy dollar sign",
            "money"
        ],
        "name": "heavy dollar sign",
        "shortcodes": [
            ":heavy_dollar_sign:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⚕️",
        "emoticons": [],
        "keywords": [
            "aesculapius",
            "medical symbol",
            "medicine",
            "staff"
        ],
        "name": "medical symbol",
        "shortcodes": [
            ":medical_symbol:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "♻️",
        "emoticons": [],
        "keywords": [
            "recycle",
            "recycling symbol"
        ],
        "name": "recycling symbol",
        "shortcodes": [
            ":recycling_symbol:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⚜️",
        "emoticons": [],
        "keywords": [
            "fleur-de-lis"
        ],
        "name": "fleur-de-lis",
        "shortcodes": [
            ":fleur-de-lis:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔱",
        "emoticons": [],
        "keywords": [
            "anchor",
            "emblem",
            "ship",
            "tool",
            "trident"
        ],
        "name": "trident emblem",
        "shortcodes": [
            ":trident_emblem:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "📛",
        "emoticons": [],
        "keywords": [
            "badge",
            "name"
        ],
        "name": "name badge",
        "shortcodes": [
            ":name_badge:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔰",
        "emoticons": [],
        "keywords": [
            "beginner",
            "chevron",
            "Japanese",
            "Japanese symbol for beginner",
            "leaf"
        ],
        "name": "Japanese symbol for beginner",
        "shortcodes": [
            ":Japanese_symbol_for_beginner:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⭕",
        "emoticons": [],
        "keywords": [
            "circle",
            "hollow red circle",
            "large",
            "o",
            "red"
        ],
        "name": "hollow red circle",
        "shortcodes": [
            ":hollow_red_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "✅",
        "emoticons": [],
        "keywords": [
            "✓",
            "button",
            "check",
            "mark",
            "tick"
        ],
        "name": "check mark button",
        "shortcodes": [
            ":check_mark_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "☑️",
        "emoticons": [],
        "keywords": [
            "ballot",
            "box",
            "check box with check",
            "tick",
            "tick box with tick",
            "✓",
            "check"
        ],
        "name": "check box with check",
        "shortcodes": [
            ":check_box_with_check:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "✔️",
        "emoticons": [],
        "keywords": [
            "check mark",
            "heavy tick mark",
            "mark",
            "tick",
            "✓",
            "check"
        ],
        "name": "check mark",
        "shortcodes": [
            ":check_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "❌",
        "emoticons": [],
        "keywords": [
            "×",
            "cancel",
            "cross",
            "mark",
            "multiplication",
            "multiply",
            "x"
        ],
        "name": "cross mark",
        "shortcodes": [
            ":cross_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "❎",
        "emoticons": [],
        "keywords": [
            "×",
            "cross mark button",
            "mark",
            "square",
            "x"
        ],
        "name": "cross mark button",
        "shortcodes": [
            ":cross_mark_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "➰",
        "emoticons": [],
        "keywords": [
            "curl",
            "curly loop",
            "loop"
        ],
        "name": "curly loop",
        "shortcodes": [
            ":curly_loop:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "➿",
        "emoticons": [],
        "keywords": [
            "curl",
            "double",
            "double curly loop",
            "loop"
        ],
        "name": "double curly loop",
        "shortcodes": [
            ":double_curly_loop:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "〽️",
        "emoticons": [],
        "keywords": [
            "mark",
            "part",
            "part alternation mark"
        ],
        "name": "part alternation mark",
        "shortcodes": [
            ":part_alternation_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "✳️",
        "emoticons": [],
        "keywords": [
            "*",
            "asterisk",
            "eight-spoked asterisk"
        ],
        "name": "eight-spoked asterisk",
        "shortcodes": [
            ":eight-spoked_asterisk:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "✴️",
        "emoticons": [],
        "keywords": [
            "*",
            "eight-pointed star",
            "star"
        ],
        "name": "eight-pointed star",
        "shortcodes": [
            ":eight-pointed_star:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "❇️",
        "emoticons": [],
        "keywords": [
            "*",
            "sparkle"
        ],
        "name": "sparkle",
        "shortcodes": [
            ":sparkle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "©️",
        "emoticons": [],
        "keywords": [
            "C",
            "copyright"
        ],
        "name": "copyright",
        "shortcodes": [
            ":copyright:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "®️",
        "emoticons": [],
        "keywords": [
            "R",
            "registered",
            "r",
            "trademark"
        ],
        "name": "registered",
        "shortcodes": [
            ":registered:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "™️",
        "emoticons": [],
        "keywords": [
            "mark",
            "TM",
            "trade mark",
            "trademark"
        ],
        "name": "trade mark",
        "shortcodes": [
            ":trade_mark:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "#️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: #",
        "shortcodes": [
            ":keycap:_#:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "*️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: *",
        "shortcodes": [
            ":keycap:_*:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "0️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 0",
        "shortcodes": [
            ":keycap:_0:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "1️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 1",
        "shortcodes": [
            ":keycap:_1:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "2️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 2",
        "shortcodes": [
            ":keycap:_2:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "3️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 3",
        "shortcodes": [
            ":keycap:_3:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "4️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 4",
        "shortcodes": [
            ":keycap:_4:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "5️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 5",
        "shortcodes": [
            ":keycap:_5:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "6️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 6",
        "shortcodes": [
            ":keycap:_6:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "7️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 7",
        "shortcodes": [
            ":keycap:_7:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "8️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 8",
        "shortcodes": [
            ":keycap:_8:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "9️⃣",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 9",
        "shortcodes": [
            ":keycap:_9:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔟",
        "emoticons": [],
        "keywords": [
            "keycap"
        ],
        "name": "keycap: 10",
        "shortcodes": [
            ":keycap:_10:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔠",
        "emoticons": [],
        "keywords": [
            "input Latin uppercase",
            "ABCD",
            "input",
            "latin",
            "letters",
            "uppercase",
            "Latin"
        ],
        "name": "input latin uppercase",
        "shortcodes": [
            ":input_latin_uppercase:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔡",
        "emoticons": [],
        "keywords": [
            "input Latin lowercase",
            "abcd",
            "input",
            "latin",
            "letters",
            "lowercase",
            "Latin"
        ],
        "name": "input latin lowercase",
        "shortcodes": [
            ":input_latin_lowercase:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔢",
        "emoticons": [],
        "keywords": [
            "1234",
            "input",
            "numbers"
        ],
        "name": "input numbers",
        "shortcodes": [
            ":input_numbers:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔣",
        "emoticons": [],
        "keywords": [
            "〒♪&%",
            "input",
            "input symbols"
        ],
        "name": "input symbols",
        "shortcodes": [
            ":input_symbols:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔤",
        "emoticons": [],
        "keywords": [
            "input Latin letters",
            "abc",
            "alphabet",
            "input",
            "latin",
            "letters",
            "Latin"
        ],
        "name": "input latin letters",
        "shortcodes": [
            ":input_latin_letters:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🅰️",
        "emoticons": [],
        "keywords": [
            "A",
            "A button (blood type)",
            "blood type"
        ],
        "name": "A button (blood type)",
        "shortcodes": [
            ":A_button_(blood_type):"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆎",
        "emoticons": [],
        "keywords": [
            "AB",
            "AB button (blood type)",
            "blood type"
        ],
        "name": "AB button (blood type)",
        "shortcodes": [
            ":AB_button_(blood_type):"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🅱️",
        "emoticons": [],
        "keywords": [
            "B",
            "B button (blood type)",
            "blood type"
        ],
        "name": "B button (blood type)",
        "shortcodes": [
            ":B_button_(blood_type):"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆑",
        "emoticons": [],
        "keywords": [
            "CL",
            "CL button"
        ],
        "name": "CL button",
        "shortcodes": [
            ":CL_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆒",
        "emoticons": [],
        "keywords": [
            "COOL",
            "COOL button"
        ],
        "name": "COOL button",
        "shortcodes": [
            ":COOL_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆓",
        "emoticons": [],
        "keywords": [
            "FREE",
            "FREE button"
        ],
        "name": "FREE button",
        "shortcodes": [
            ":FREE_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "ℹ️",
        "emoticons": [],
        "keywords": [
            "i",
            "information"
        ],
        "name": "information",
        "shortcodes": [
            ":information:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆔",
        "emoticons": [],
        "keywords": [
            "ID",
            "ID button",
            "identity"
        ],
        "name": "ID button",
        "shortcodes": [
            ":ID_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "Ⓜ️",
        "emoticons": [],
        "keywords": [
            "circle",
            "circled M",
            "M"
        ],
        "name": "circled M",
        "shortcodes": [
            ":circled_M:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆕",
        "emoticons": [],
        "keywords": [
            "NEW",
            "NEW button"
        ],
        "name": "NEW button",
        "shortcodes": [
            ":NEW_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆖",
        "emoticons": [],
        "keywords": [
            "NG",
            "NG button"
        ],
        "name": "NG button",
        "shortcodes": [
            ":NG_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🅾️",
        "emoticons": [],
        "keywords": [
            "blood type",
            "O",
            "O button (blood type)"
        ],
        "name": "O button (blood type)",
        "shortcodes": [
            ":O_button_(blood_type):"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆗",
        "emoticons": [],
        "keywords": [
            "OK",
            "OK button"
        ],
        "name": "OK button",
        "shortcodes": [
            ":OK_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🅿️",
        "emoticons": [],
        "keywords": [
            "P",
            "P button",
            "parking"
        ],
        "name": "P button",
        "shortcodes": [
            ":P_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆘",
        "emoticons": [],
        "keywords": [
            "help",
            "SOS",
            "SOS button"
        ],
        "name": "SOS button",
        "shortcodes": [
            ":SOS_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆙",
        "emoticons": [],
        "keywords": [
            "mark",
            "UP",
            "UP!",
            "UP! button"
        ],
        "name": "UP! button",
        "shortcodes": [
            ":UP!_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🆚",
        "emoticons": [],
        "keywords": [
            "versus",
            "VS",
            "VS button"
        ],
        "name": "VS button",
        "shortcodes": [
            ":VS_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈁",
        "emoticons": [],
        "keywords": [
            "“here”",
            "Japanese",
            "Japanese “here” button",
            "katakana",
            "ココ"
        ],
        "name": "Japanese “here” button",
        "shortcodes": [
            ":Japanese_“here”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈂️",
        "emoticons": [],
        "keywords": [
            "“service charge”",
            "Japanese",
            "Japanese “service charge” button",
            "katakana",
            "サ"
        ],
        "name": "Japanese “service charge” button",
        "shortcodes": [
            ":Japanese_“service_charge”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈷️",
        "emoticons": [],
        "keywords": [
            "“monthly amount”",
            "ideograph",
            "Japanese",
            "Japanese “monthly amount” button",
            "月"
        ],
        "name": "Japanese “monthly amount” button",
        "shortcodes": [
            ":Japanese_“monthly_amount”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈶",
        "emoticons": [],
        "keywords": [
            "“not free of charge”",
            "ideograph",
            "Japanese",
            "Japanese “not free of charge” button",
            "有"
        ],
        "name": "Japanese “not free of charge” button",
        "shortcodes": [
            ":Japanese_“not_free_of_charge”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈯",
        "emoticons": [],
        "keywords": [
            "“reserved”",
            "ideograph",
            "Japanese",
            "Japanese “reserved” button",
            "指"
        ],
        "name": "Japanese “reserved” button",
        "shortcodes": [
            ":Japanese_“reserved”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🉐",
        "emoticons": [],
        "keywords": [
            "“bargain”",
            "ideograph",
            "Japanese",
            "Japanese “bargain” button",
            "得"
        ],
        "name": "Japanese “bargain” button",
        "shortcodes": [
            ":Japanese_“bargain”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈹",
        "emoticons": [],
        "keywords": [
            "“discount”",
            "ideograph",
            "Japanese",
            "Japanese “discount” button",
            "割"
        ],
        "name": "Japanese “discount” button",
        "shortcodes": [
            ":Japanese_“discount”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈚",
        "emoticons": [],
        "keywords": [
            "“free of charge”",
            "ideograph",
            "Japanese",
            "Japanese “free of charge” button",
            "無"
        ],
        "name": "Japanese “free of charge” button",
        "shortcodes": [
            ":Japanese_“free_of_charge”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈲",
        "emoticons": [],
        "keywords": [
            "“prohibited”",
            "ideograph",
            "Japanese",
            "Japanese “prohibited” button",
            "禁"
        ],
        "name": "Japanese “prohibited” button",
        "shortcodes": [
            ":Japanese_“prohibited”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🉑",
        "emoticons": [],
        "keywords": [
            "“acceptable”",
            "ideograph",
            "Japanese",
            "Japanese “acceptable” button",
            "可"
        ],
        "name": "Japanese “acceptable” button",
        "shortcodes": [
            ":Japanese_“acceptable”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈸",
        "emoticons": [],
        "keywords": [
            "“application”",
            "ideograph",
            "Japanese",
            "Japanese “application” button",
            "申"
        ],
        "name": "Japanese “application” button",
        "shortcodes": [
            ":Japanese_“application”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈴",
        "emoticons": [],
        "keywords": [
            "“passing grade”",
            "ideograph",
            "Japanese",
            "Japanese “passing grade” button",
            "合"
        ],
        "name": "Japanese “passing grade” button",
        "shortcodes": [
            ":Japanese_“passing_grade”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈳",
        "emoticons": [],
        "keywords": [
            "“vacancy”",
            "ideograph",
            "Japanese",
            "Japanese “vacancy” button",
            "空"
        ],
        "name": "Japanese “vacancy” button",
        "shortcodes": [
            ":Japanese_“vacancy”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "㊗️",
        "emoticons": [],
        "keywords": [
            "“congratulations”",
            "ideograph",
            "Japanese",
            "Japanese “congratulations” button",
            "祝"
        ],
        "name": "Japanese “congratulations” button",
        "shortcodes": [
            ":Japanese_“congratulations”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "㊙️",
        "emoticons": [],
        "keywords": [
            "“secret”",
            "ideograph",
            "Japanese",
            "Japanese “secret” button",
            "秘"
        ],
        "name": "Japanese “secret” button",
        "shortcodes": [
            ":Japanese_“secret”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈺",
        "emoticons": [],
        "keywords": [
            "“open for business”",
            "ideograph",
            "Japanese",
            "Japanese “open for business” button",
            "営"
        ],
        "name": "Japanese “open for business” button",
        "shortcodes": [
            ":Japanese_“open_for_business”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🈵",
        "emoticons": [],
        "keywords": [
            "“no vacancy”",
            "ideograph",
            "Japanese",
            "Japanese “no vacancy” button",
            "満"
        ],
        "name": "Japanese “no vacancy” button",
        "shortcodes": [
            ":Japanese_“no_vacancy”_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔴",
        "emoticons": [],
        "keywords": [
            "circle",
            "geometric",
            "red"
        ],
        "name": "red circle",
        "shortcodes": [
            ":red_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟠",
        "emoticons": [],
        "keywords": [
            "circle",
            "orange"
        ],
        "name": "orange circle",
        "shortcodes": [
            ":orange_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟡",
        "emoticons": [],
        "keywords": [
            "circle",
            "yellow"
        ],
        "name": "yellow circle",
        "shortcodes": [
            ":yellow_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟢",
        "emoticons": [],
        "keywords": [
            "circle",
            "green"
        ],
        "name": "green circle",
        "shortcodes": [
            ":green_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔵",
        "emoticons": [],
        "keywords": [
            "blue",
            "circle",
            "geometric"
        ],
        "name": "blue circle",
        "shortcodes": [
            ":blue_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟣",
        "emoticons": [],
        "keywords": [
            "circle",
            "purple"
        ],
        "name": "purple circle",
        "shortcodes": [
            ":purple_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟤",
        "emoticons": [],
        "keywords": [
            "brown",
            "circle"
        ],
        "name": "brown circle",
        "shortcodes": [
            ":brown_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⚫",
        "emoticons": [],
        "keywords": [
            "black circle",
            "circle",
            "geometric"
        ],
        "name": "black circle",
        "shortcodes": [
            ":black_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⚪",
        "emoticons": [],
        "keywords": [
            "circle",
            "geometric",
            "white circle"
        ],
        "name": "white circle",
        "shortcodes": [
            ":white_circle:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟥",
        "emoticons": [],
        "keywords": [
            "red",
            "square"
        ],
        "name": "red square",
        "shortcodes": [
            ":red_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟧",
        "emoticons": [],
        "keywords": [
            "orange",
            "square"
        ],
        "name": "orange square",
        "shortcodes": [
            ":orange_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟨",
        "emoticons": [],
        "keywords": [
            "square",
            "yellow"
        ],
        "name": "yellow square",
        "shortcodes": [
            ":yellow_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟩",
        "emoticons": [],
        "keywords": [
            "green",
            "square"
        ],
        "name": "green square",
        "shortcodes": [
            ":green_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟦",
        "emoticons": [],
        "keywords": [
            "blue",
            "square"
        ],
        "name": "blue square",
        "shortcodes": [
            ":blue_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟪",
        "emoticons": [],
        "keywords": [
            "purple",
            "square"
        ],
        "name": "purple square",
        "shortcodes": [
            ":purple_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🟫",
        "emoticons": [],
        "keywords": [
            "brown",
            "square"
        ],
        "name": "brown square",
        "shortcodes": [
            ":brown_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⬛",
        "emoticons": [],
        "keywords": [
            "black large square",
            "geometric",
            "square"
        ],
        "name": "black large square",
        "shortcodes": [
            ":black_large_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "⬜",
        "emoticons": [],
        "keywords": [
            "geometric",
            "square",
            "white large square"
        ],
        "name": "white large square",
        "shortcodes": [
            ":white_large_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "◼️",
        "emoticons": [],
        "keywords": [
            "black medium square",
            "geometric",
            "square"
        ],
        "name": "black medium square",
        "shortcodes": [
            ":black_medium_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "◻️",
        "emoticons": [],
        "keywords": [
            "geometric",
            "square",
            "white medium square"
        ],
        "name": "white medium square",
        "shortcodes": [
            ":white_medium_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "◾",
        "emoticons": [],
        "keywords": [
            "black medium-small square",
            "geometric",
            "square"
        ],
        "name": "black medium-small square",
        "shortcodes": [
            ":black_medium-small_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "◽",
        "emoticons": [],
        "keywords": [
            "geometric",
            "square",
            "white medium-small square"
        ],
        "name": "white medium-small square",
        "shortcodes": [
            ":white_medium-small_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "▪️",
        "emoticons": [],
        "keywords": [
            "black small square",
            "geometric",
            "square"
        ],
        "name": "black small square",
        "shortcodes": [
            ":black_small_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "▫️",
        "emoticons": [],
        "keywords": [
            "geometric",
            "square",
            "white small square"
        ],
        "name": "white small square",
        "shortcodes": [
            ":white_small_square:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔶",
        "emoticons": [],
        "keywords": [
            "diamond",
            "geometric",
            "large orange diamond",
            "orange"
        ],
        "name": "large orange diamond",
        "shortcodes": [
            ":large_orange_diamond:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔷",
        "emoticons": [],
        "keywords": [
            "blue",
            "diamond",
            "geometric",
            "large blue diamond"
        ],
        "name": "large blue diamond",
        "shortcodes": [
            ":large_blue_diamond:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔸",
        "emoticons": [],
        "keywords": [
            "diamond",
            "geometric",
            "orange",
            "small orange diamond"
        ],
        "name": "small orange diamond",
        "shortcodes": [
            ":small_orange_diamond:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔹",
        "emoticons": [],
        "keywords": [
            "blue",
            "diamond",
            "geometric",
            "small blue diamond"
        ],
        "name": "small blue diamond",
        "shortcodes": [
            ":small_blue_diamond:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔺",
        "emoticons": [],
        "keywords": [
            "geometric",
            "red",
            "red triangle pointed up"
        ],
        "name": "red triangle pointed up",
        "shortcodes": [
            ":red_triangle_pointed_up:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔻",
        "emoticons": [],
        "keywords": [
            "down",
            "geometric",
            "red",
            "red triangle pointed down"
        ],
        "name": "red triangle pointed down",
        "shortcodes": [
            ":red_triangle_pointed_down:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "💠",
        "emoticons": [],
        "keywords": [
            "comic",
            "diamond",
            "diamond with a dot",
            "geometric",
            "inside"
        ],
        "name": "diamond with a dot",
        "shortcodes": [
            ":diamond_with_a_dot:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔘",
        "emoticons": [],
        "keywords": [
            "button",
            "geometric",
            "radio"
        ],
        "name": "radio button",
        "shortcodes": [
            ":radio_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔳",
        "emoticons": [],
        "keywords": [
            "button",
            "geometric",
            "outlined",
            "square",
            "white square button"
        ],
        "name": "white square button",
        "shortcodes": [
            ":white_square_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🔲",
        "emoticons": [],
        "keywords": [
            "black square button",
            "button",
            "geometric",
            "square"
        ],
        "name": "black square button",
        "shortcodes": [
            ":black_square_button:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏁",
        "emoticons": [],
        "keywords": [
            "checkered",
            "chequered",
            "chequered flag",
            "racing",
            "checkered flag"
        ],
        "name": "chequered flag",
        "shortcodes": [
            ":chequered_flag:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🚩",
        "emoticons": [],
        "keywords": [
            "post",
            "triangular flag",
            "red flag"
        ],
        "name": "triangular flag",
        "shortcodes": [
            ":triangular_flag:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🎌",
        "emoticons": [],
        "keywords": [
            "celebration",
            "cross",
            "crossed",
            "crossed flags",
            "Japanese"
        ],
        "name": "crossed flags",
        "shortcodes": [
            ":crossed_flags:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏴",
        "emoticons": [],
        "keywords": [
            "black flag",
            "waving"
        ],
        "name": "black flag",
        "shortcodes": [
            ":black_flag:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏳️",
        "emoticons": [],
        "keywords": [
            "waving",
            "white flag",
            "surrender"
        ],
        "name": "white flag",
        "shortcodes": [
            ":white_flag:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏳️‍🌈",
        "emoticons": [],
        "keywords": [
            "pride",
            "rainbow",
            "rainbow flag"
        ],
        "name": "rainbow flag",
        "shortcodes": [
            ":rainbow_flag:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏴‍☠️",
        "emoticons": [],
        "keywords": [
            "Jolly Roger",
            "pirate",
            "pirate flag",
            "plunder",
            "treasure"
        ],
        "name": "pirate flag",
        "shortcodes": [
            ":pirate_flag:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "emoticons": [],
        "keywords": [
            "flag"
        ],
        "name": "flag: England",
        "shortcodes": [
            ":england:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        "emoticons": [],
        "keywords": [
            "flag"
        ],
        "name": "flag: Scotland",
        "shortcodes": [
            ":scotland:"
        ]
    },
    {
        "category": "Symbols",
        "codepoints": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
        "emoticons": [],
        "keywords": [
            "flag"
        ],
        "name": "flag: Wales",
        "shortcodes": [
            ":wales:"
        ]
    }
]`);
