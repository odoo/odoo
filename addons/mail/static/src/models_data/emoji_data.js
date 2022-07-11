/** @odoo-module **/

export const categoryTitleByCategoryName = new Map([
    ['Smileys & Emotion', "🤠"],
    ['People & Body', "🤟"],
    ['Animals & Nature', "🐘"],
    ['Food & Drink', "🍔"],
    ['Travel & Places', "🚍"],
    ['Activities', "🎣"],
    ['Objects', "🎩"],
    ['Symbols', "🚰"],
    ['Flags', "🇻🇨"],
]);

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
export const emojiData = JSON.parse(`[
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
    },
    {
        "codepoints": "👁️‍🗨️",
        "name": "eye in speech bubble",
        "shortcodes": [
            ":eye_in_speech_bubble:"
        ],
        "emoticons": [],
        "category": "Smileys & Emotion",
        "keywords": [],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
    },
    {
        "codepoints": "🕵️‍♂️",
        "name": "man detective",
        "shortcodes": [
            ":man_detective:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [],
        "hasSkinToneVariations": true
    },
    {
        "codepoints": "🕵️‍♀️",
        "name": "woman detective",
        "shortcodes": [
            ":woman_detective:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
    },
    {
        "codepoints": "🏌️‍♂️",
        "name": "man golfing",
        "shortcodes": [
            ":man_golfing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [],
        "hasSkinToneVariations": true
    },
    {
        "codepoints": "🏌️‍♀️",
        "name": "woman golfing",
        "shortcodes": [
            ":woman_golfing:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
    },
    {
        "codepoints": "⛹️‍♂️",
        "name": "man bouncing ball",
        "shortcodes": [
            ":man_bouncing_ball:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [],
        "hasSkinToneVariations": true
    },
    {
        "codepoints": "⛹️‍♀️",
        "name": "woman bouncing ball",
        "shortcodes": [
            ":woman_bouncing_ball:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
    },
    {
        "codepoints": "🏋️‍♂️",
        "name": "man lifting weights",
        "shortcodes": [
            ":man_lifting_weights:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [],
        "hasSkinToneVariations": true
    },
    {
        "codepoints": "🏋️‍♀️",
        "name": "woman lifting weights",
        "shortcodes": [
            ":woman_lifting_weights:"
        ],
        "emoticons": [],
        "category": "People & Body",
        "keywords": [],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": true
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
    },
    {
        "codepoints": "🏳️‍⚧️",
        "name": "transgender flag",
        "shortcodes": [
            ":transgender_flag:"
        ],
        "emoticons": [],
        "category": "Flags",
        "keywords": [],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
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
        ],
        "hasSkinToneVariations": false
    }
]`);
