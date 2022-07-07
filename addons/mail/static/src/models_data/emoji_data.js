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
        "hasSkinToneVariations": false
    }
]`);
