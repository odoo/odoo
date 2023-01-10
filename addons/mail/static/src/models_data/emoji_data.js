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

import { _lt as lazyTranslate } from "@web/core/l10n/translation";
const _lt = str => JSON.stringify(lazyTranslate(str)).slice(1, -1);

export const emojiCategoriesData = JSON.parse(`[
    {
        "name": "Smileys & Emotion",
        "displayName": "`+ _lt("Smileys & Emotion") + `",
        "title": "🙂",
        "sortId": 1
    },
    {
        "name": "People & Body",
        "displayName": "`+ _lt("People & Body") + `",
        "title": "🤟",
        "sortId": 2
    },
    {
        "name": "Animals & Nature",
        "displayName": "`+ _lt("Animals & Nature") + `",
        "title": "🐢",
        "sortId": 3
    },
    {
        "name": "Food & Drink",
        "displayName": "`+ _lt("Food & Drink") + `",
        "title": "🍭",
        "sortId": 4
    },
    {
        "name": "Travel & Places",
        "displayName": "`+ _lt("Travel & Places") + `",
        "title": "🚗",
        "sortId": 5
    },
    {
        "name": "Activities",
        "displayName": "`+ _lt("Activities") + `",
        "title": "🏈",
        "sortId": 6
    },
    {
        "name": "Objects",
        "displayName": "`+ _lt("Objects") + `",
        "title": "📕",
        "sortId": 7
    },
    {
        "name": "Symbols",
        "displayName": "`+ _lt("Symbols") + `",
        "title": "🔠",
        "sortId": 8
    }
]`);

const emojisData1 = `{
    "category": "Smileys & Emotion",
    "codepoints": "😀",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("grin") + `",
        "` + _lt("grinning face") + `"
    ],
    "name": "` + _lt("grinning face") + `",
    "shortcodes": [
        ":grinning:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😃",
    "emoticons": [
        ":D",
        ":-D",
        "=D"
    ],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("grinning face with big eyes") + `",
        "` + _lt("mouth") + `",
        "` + _lt("open") + `",
        "` + _lt("smile") + `"
    ],
    "name": "` + _lt("grinning face with big eyes") + `",
    "shortcodes": [
        ":smiley:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😄",
    "emoticons": [],
    "keywords": [
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("grinning face with smiling eyes") + `",
        "` + _lt("mouth") + `",
        "` + _lt("open") + `",
        "` + _lt("smile") + `"
    ],
    "name": "` + _lt("grinning face with smiling eyes") + `",
    "shortcodes": [
        ":smile:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😁",
    "emoticons": [],
    "keywords": [
        "` + _lt("beaming face with smiling eyes") + `",
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("grin") + `",
        "` + _lt("smile") + `"
    ],
    "name": "` + _lt("beaming face with smiling eyes") + `",
    "shortcodes": [
        ":grin:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😆",
    "emoticons": [
        "xD",
        "XD"
    ],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("grinning squinting face") + `",
        "` + _lt("laugh") + `",
        "` + _lt("mouth") + `",
        "` + _lt("satisfied") + `",
        "` + _lt("smile") + `"
    ],
    "name": "` + _lt("grinning squinting face") + `",
    "shortcodes": [
        ":laughing:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😅",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("face") + `",
        "` + _lt("grinning face with sweat") + `",
        "` + _lt("open") + `",
        "` + _lt("smile") + `",
        "` + _lt("sweat") + `"
    ],
    "name": "` + _lt("grinning face with sweat") + `",
    "shortcodes": [
        ":sweat_smile:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤣",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("floor") + `",
        "` + _lt("laugh") + `",
        "` + _lt("rofl") + `",
        "` + _lt("rolling") + `",
        "` + _lt("rolling on the floor laughing") + `",
        "` + _lt("rotfl") + `"
    ],
    "name": "` + _lt("rolling on the floor laughing") + `",
    "shortcodes": [
        ":rofl:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😂",
    "emoticons": [
        "x'D"
    ],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("face with tears of joy") + `",
        "` + _lt("joy") + `",
        "` + _lt("laugh") + `",
        "` + _lt("tear") + `"
    ],
    "name": "` + _lt("face with tears of joy") + `",
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
        "` + _lt("face") + `",
        "` + _lt("slightly smiling face") + `",
        "` + _lt("smile") + `"
    ],
    "name": "` + _lt("slightly smiling face") + `",
    "shortcodes": [
        ":slight_smile:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙃",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("upside-down") + `",
        "` + _lt("upside down") + `",
        "` + _lt("upside-down face") + `"
    ],
    "name": "` + _lt("upside-down face") + `",
    "shortcodes": [
        ":upside_down:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😉",
    "emoticons": [
        ";)",
        ";-)"
    ],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("wink") + `",
        "` + _lt("winking face") + `"
    ],
    "name": "` + _lt("winking face") + `",
    "shortcodes": [
        ":wink:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😊",
    "emoticons": [
        ":)",
        ":-)",
        "=)",
        ":]"
    ],
    "keywords": [
        "` + _lt("blush") + `",
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("smile") + `",
        "` + _lt("smiling face with smiling eyes") + `"
    ],
    "name": "` + _lt("smiling face with smiling eyes") + `",
    "shortcodes": [
        ":smiling_face_with_smiling_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😇",
    "emoticons": [
        "o:)"
    ],
    "keywords": [
        "` + _lt("angel") + `",
        "` + _lt("face") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("halo") + `",
        "` + _lt("innocent") + `",
        "` + _lt("smiling face with halo") + `"
    ],
    "name": "` + _lt("smiling face with halo") + `",
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
        "` + _lt("adore") + `",
        "` + _lt("crush") + `",
        "` + _lt("hearts") + `",
        "` + _lt("in love") + `",
        "` + _lt("smiling face with hearts") + `"
    ],
    "name": "` + _lt("smiling face with hearts") + `",
    "shortcodes": [
        ":smiling_face_with_hearts:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😍",
    "emoticons": [
        ":heart_eyes"
    ],
    "keywords": [
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("love") + `",
        "` + _lt("smile") + `",
        "` + _lt("smiling face with heart-eyes") + `",
        "` + _lt("smiling face with heart eyes") + `"
    ],
    "name": "` + _lt("smiling face with heart-eyes") + `",
    "shortcodes": [
        ":heart_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤩",
    "emoticons": [],
    "keywords": [
        "` + _lt("eyes") + `",
        "` + _lt("face") + `",
        "` + _lt("grinning") + `",
        "` + _lt("star") + `",
        "` + _lt("star-struck") + `"
    ],
    "name": "` + _lt("star-struck") + `",
    "shortcodes": [
        ":star_struck:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😘",
    "emoticons": [
        ":*",
        ":-*"
    ],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("face blowing a kiss") + `",
        "` + _lt("kiss") + `"
    ],
    "name": "` + _lt("face blowing a kiss") + `",
    "shortcodes": [
        ":kissing_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😗",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("kiss") + `",
        "` + _lt("kissing face") + `"
    ],
    "name": "` + _lt("kissing face") + `",
    "shortcodes": [
        ":kissing:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😚",
    "emoticons": [],
    "keywords": [
        "` + _lt("closed") + `",
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("kiss") + `",
        "` + _lt("kissing face with closed eyes") + `"
    ],
    "name": "` + _lt("kissing face with closed eyes") + `",
    "shortcodes": [
        ":kissing_closed_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😙",
    "emoticons": [],
    "keywords": [
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("kiss") + `",
        "` + _lt("kissing face with smiling eyes") + `",
        "` + _lt("smile") + `"
    ],
    "name": "` + _lt("kissing face with smiling eyes") + `",
    "shortcodes": [
        ":kissing_smiling_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😋",
    "emoticons": [
        ":p",
        ":P",
        ":-p",
        ":-P",
        "=P"
    ],
    "keywords": [
        "` + _lt("delicious") + `",
        "` + _lt("face") + `",
        "` + _lt("face savoring food") + `",
        "` + _lt("savouring") + `",
        "` + _lt("smile") + `",
        "` + _lt("yum") + `",
        "` + _lt("face savouring food") + `",
        "` + _lt("savoring") + `"
    ],
    "name": "` + _lt("face savoring food") + `",
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
        "` + _lt("face") + `",
        "` + _lt("face with tongue") + `",
        "` + _lt("tongue") + `"
    ],
    "name": "` + _lt("face with tongue") + `",
    "shortcodes": [
        ":stuck_out_ltongue:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😜",
    "emoticons": [
        ";p",
        ";P"
    ],
    "keywords": [
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("joke") + `",
        "` + _lt("tongue") + `",
        "` + _lt("wink") + `",
        "` + _lt("winking face with tongue") + `"
    ],
    "name": "` + _lt("winking face with tongue") + `",
    "shortcodes": [
        ":stuck_out_ltongue_winking_eye:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤪",
    "emoticons": [],
    "keywords": [
        "` + _lt("eye") + `",
        "` + _lt("goofy") + `",
        "` + _lt("large") + `",
        "` + _lt("small") + `",
        "` + _lt("zany face") + `"
    ],
    "name": "` + _lt("zany face") + `",
    "shortcodes": [
        ":zany:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😝",
    "emoticons": [
        "xp",
        "xP"
    ],
    "keywords": [
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("horrible") + `",
        "` + _lt("squinting face with tongue") + `",
        "` + _lt("taste") + `",
        "` + _lt("tongue") + `"
    ],
    "name": "` + _lt("squinting face with tongue") + `",
    "shortcodes": [
        ":stuck_out_ltongue_closed_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤑",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("money") + `",
        "` + _lt("money-mouth face") + `",
        "` + _lt("mouth") + `"
    ],
    "name": "` + _lt("money-mouth face") + `",
    "shortcodes": [
        ":money_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤗",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("hug") + `",
        "` + _lt("hugging") + `",
        "` + _lt("open hands") + `",
        "` + _lt("smiling face") + `",
        "` + _lt("smiling face with open hands") + `"
    ],
    "name": "` + _lt("smiling face with open hands") + `",
    "shortcodes": [
        ":hugging_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤭",
    "emoticons": [],
    "keywords": [
        "` + _lt("face with hand over mouth") + `",
        "` + _lt("whoops") + `",
        "` + _lt("oops") + `",
        "` + _lt("embarrassed") + `"
    ],
    "name": "` + _lt("face with hand over mouth") + `",
    "shortcodes": [
        ":hand_over_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤫",
    "emoticons": [],
    "keywords": [
        "` + _lt("quiet") + `",
        "` + _lt("shooshing face") + `",
        "` + _lt("shush") + `",
        "` + _lt("shushing face") + `"
    ],
    "name": "` + _lt("shushing face") + `",
    "shortcodes": [
        ":shush:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤔",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("thinking") + `"
    ],
    "name": "` + _lt("thinking face") + `",
    "shortcodes": [
        ":thinking:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤐",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("mouth") + `",
        "` + _lt("zipper") + `",
        "` + _lt("zipper-mouth face") + `"
    ],
    "name": "` + _lt("zipper-mouth face") + `",
    "shortcodes": [
        ":zipper_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤨",
    "emoticons": [],
    "keywords": [
        "` + _lt("distrust") + `",
        "` + _lt("face with raised eyebrow") + `",
        "` + _lt("skeptic") + `"
    ],
    "name": "` + _lt("face with raised eyebrow") + `",
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
        "` + _lt("deadpan") + `",
        "` + _lt("face") + `",
        "` + _lt("meh") + `",
        "` + _lt("neutral") + `"
    ],
    "name": "` + _lt("neutral face") + `",
    "shortcodes": [
        ":neutral:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😑",
    "emoticons": [],
    "keywords": [
        "` + _lt("expressionless") + `",
        "` + _lt("face") + `",
        "` + _lt("inexpressive") + `",
        "` + _lt("meh") + `",
        "` + _lt("unexpressive") + `"
    ],
    "name": "` + _lt("expressionless face") + `",
    "shortcodes": [
        ":expressionless:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😶",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("face without mouth") + `",
        "` + _lt("mouth") + `",
        "` + _lt("quiet") + `",
        "` + _lt("silent") + `"
    ],
    "name": "` + _lt("face without mouth") + `",
    "shortcodes": [
        ":no_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😏",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("smirk") + `",
        "` + _lt("smirking face") + `"
    ],
    "name": "` + _lt("smirking face") + `",
    "shortcodes": [
        ":smirk:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😒",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("unamused") + `",
        "` + _lt("unhappy") + `"
    ],
    "name": "` + _lt("unamused face") + `",
    "shortcodes": [
        ":unamused_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙄",
    "emoticons": [],
    "keywords": [
        "` + _lt("eyeroll") + `",
        "` + _lt("eyes") + `",
        "` + _lt("face") + `",
        "` + _lt("face with rolling eyes") + `",
        "` + _lt("rolling") + `"
    ],
    "name": "` + _lt("face with rolling eyes") + `",
    "shortcodes": [
        ":face_with_rolling_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😬",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("grimace") + `",
        "` + _lt("grimacing face") + `"
    ],
    "name": "` + _lt("grimacing face") + `",
    "shortcodes": [
        ":grimacing_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤥",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("lie") + `",
        "` + _lt("lying face") + `",
        "` + _lt("pinocchio") + `"
    ],
    "name": "` + _lt("lying face") + `",
    "shortcodes": [
        ":lying_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😌",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("relieved") + `"
    ],
    "name": "` + _lt("relieved face") + `",
    "shortcodes": [
        ":relieved_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😔",
    "emoticons": [],
    "keywords": [
        "` + _lt("dejected") + `",
        "` + _lt("face") + `",
        "` + _lt("pensive") + `"
    ],
    "name": "` + _lt("pensive face") + `",
    "shortcodes": [
        ":pensive_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😪",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("good night") + `",
        "` + _lt("sleep") + `",
        "` + _lt("sleepy face") + `"
    ],
    "name": "` + _lt("sleepy face") + `",
    "shortcodes": [
        ":sleepy_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤤",
    "emoticons": [],
    "keywords": [
        "` + _lt("drooling") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("drooling face") + `",
    "shortcodes": [
        ":drooling_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😴",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("good night") + `",
        "` + _lt("sleep") + `",
        "` + _lt("sleeping face") + `",
        "` + _lt("ZZZ") + `"
    ],
    "name": "` + _lt("sleeping face") + `",
    "shortcodes": [
        ":sleeping_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😷",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("doctor") + `",
        "` + _lt("face") + `",
        "` + _lt("face with medical mask") + `",
        "` + _lt("mask") + `",
        "` + _lt("sick") + `",
        "` + _lt("ill") + `",
        "` + _lt("medicine") + `",
        "` + _lt("poorly") + `"
    ],
    "name": "` + _lt("face with medical mask") + `",
    "shortcodes": [
        ":face_with_medical_mask:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤒",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("face with thermometer") + `",
        "` + _lt("ill") + `",
        "` + _lt("sick") + `",
        "` + _lt("thermometer") + `"
    ],
    "name": "` + _lt("face with thermometer") + `",
    "shortcodes": [
        ":face_with_lthermometer:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤕",
    "emoticons": [],
    "keywords": [
        "` + _lt("bandage") + `",
        "` + _lt("face") + `",
        "` + _lt("face with head-bandage") + `",
        "` + _lt("hurt") + `",
        "` + _lt("injury") + `",
        "` + _lt("face with head bandage") + `"
    ],
    "name": "` + _lt("face with head-bandage") + `",
    "shortcodes": [
        ":face_with_head-bandage:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤢",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("nauseated") + `",
        "` + _lt("vomit") + `"
    ],
    "name": "` + _lt("nauseated face") + `",
    "shortcodes": [
        ":nauseated_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤮",
    "emoticons": [],
    "keywords": [
        "` + _lt("face vomiting") + `",
        "` + _lt("puke") + `",
        "` + _lt("sick") + `",
        "` + _lt("vomit") + `"
    ],
    "name": "` + _lt("face vomiting") + `",
    "shortcodes": [
        ":face_vomiting:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤧",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("gesundheit") + `",
        "` + _lt("sneeze") + `",
        "` + _lt("sneezing face") + `",
        "` + _lt("bless you") + `"
    ],
    "name": "` + _lt("sneezing face") + `",
    "shortcodes": [
        ":sneezing_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥵",
    "emoticons": [],
    "keywords": [
        "` + _lt("feverish") + `",
        "` + _lt("flushed") + `",
        "` + _lt("heat stroke") + `",
        "` + _lt("hot") + `",
        "` + _lt("hot face") + `",
        "` + _lt("red-faced") + `",
        "` + _lt("sweating") + `"
    ],
    "name": "` + _lt("hot face") + `",
    "shortcodes": [
        ":hot_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥶",
    "emoticons": [],
    "keywords": [
        "` + _lt("blue-faced") + `",
        "` + _lt("cold") + `",
        "` + _lt("cold face") + `",
        "` + _lt("freezing") + `",
        "` + _lt("frostbite") + `",
        "` + _lt("icicles") + `"
    ],
    "name": "` + _lt("cold face") + `",
    "shortcodes": [
        ":cold_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥴",
    "emoticons": [],
    "keywords": [
        "` + _lt("dizzy") + `",
        "` + _lt("intoxicated") + `",
        "` + _lt("tipsy") + `",
        "` + _lt("uneven eyes") + `",
        "` + _lt("wavy mouth") + `",
        "` + _lt("woozy face") + `"
    ],
    "name": "` + _lt("woozy face") + `",
    "shortcodes": [
        ":woozy_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😵",
    "emoticons": [],
    "keywords": [
        "` + _lt("crossed-out eyes") + `",
        "` + _lt("dead") + `",
        "` + _lt("face") + `",
        "` + _lt("face with crossed-out eyes") + `",
        "` + _lt("knocked out") + `"
    ],
    "name": "` + _lt("face with crossed-out eyes") + `",
    "shortcodes": [
        ":face_with_crossed-out_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤯",
    "emoticons": [],
    "keywords": [
        "` + _lt("exploding head") + `",
        "` + _lt("mind blown") + `",
        "` + _lt("shocked") + `"
    ],
    "name": "` + _lt("exploding head") + `",
    "shortcodes": [
        ":exploding_head:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤠",
    "emoticons": [],
    "keywords": [
        "` + _lt("cowboy") + `",
        "` + _lt("cowgirl") + `",
        "` + _lt("face") + `",
        "` + _lt("hat") + `"
    ],
    "name": "` + _lt("cowboy hat face") + `",
    "shortcodes": [
        ":cowboy_hat_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥳",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("hat") + `",
        "` + _lt("horn") + `",
        "` + _lt("party") + `",
        "` + _lt("partying face") + `"
    ],
    "name": "` + _lt("partying face") + `",
    "shortcodes": [
        ":partying_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😎",
    "emoticons": [
        "B)",
        "8)",
        "B-)",
        "8-)"
    ],
    "keywords": [
        "` + _lt("bright") + `",
        "` + _lt("cool") + `",
        "` + _lt("face") + `",
        "` + _lt("smiling face with sunglasses") + `",
        "` + _lt("sun") + `",
        "` + _lt("sunglasses") + `"
    ],
    "name": "` + _lt("smiling face with sunglasses") + `",
    "shortcodes": [
        ":smiling_face_with_sunglasses:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤓",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("geek") + `",
        "` + _lt("nerd") + `"
    ],
    "name": "` + _lt("nerd face") + `",
    "shortcodes": [
        ":nerd_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🧐",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("face with monocle") + `",
        "` + _lt("monocle") + `",
        "` + _lt("stuffy") + `"
    ],
    "name": "` + _lt("face with monocle") + `",
    "shortcodes": [
        ":face_with_monocle:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😕",
    "emoticons": [
        ":/",
        ":-/"
    ],
    "keywords": [
        "` + _lt("confused") + `",
        "` + _lt("face") + `",
        "` + _lt("meh") + `"
    ],
    "name": "` + _lt("confused face") + `",
    "shortcodes": [
        ":confused_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😟",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("worried") + `"
    ],
    "name": "` + _lt("worried face") + `",
    "shortcodes": [
        ":worried_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙁",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("frown") + `",
        "` + _lt("slightly frowning face") + `"
    ],
    "name": "` + _lt("slightly frowning face") + `",
    "shortcodes": [
        ":slightly_frowning_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😮",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("face with open mouth") + `",
        "` + _lt("mouth") + `",
        "` + _lt("open") + `",
        "` + _lt("sympathy") + `"
    ],
    "name": "` + _lt("face with open mouth") + `",
    "shortcodes": [
        ":face_with_open_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😯",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("hushed") + `",
        "` + _lt("stunned") + `",
        "` + _lt("surprised") + `"
    ],
    "name": "` + _lt("hushed face") + `",
    "shortcodes": [
        ":hushed_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😲",
    "emoticons": [
        ":O",
        ":-O",
        ":o",
        ":-o"
    ],
    "keywords": [
        "` + _lt("astonished") + `",
        "` + _lt("face") + `",
        "` + _lt("shocked") + `",
        "` + _lt("totally") + `"
    ],
    "name": "` + _lt("astonished face") + `",
    "shortcodes": [
        ":astonished_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😳",
    "emoticons": [
        "o_o"
    ],
    "keywords": [
        "` + _lt("dazed") + `",
        "` + _lt("face") + `",
        "` + _lt("flushed") + `"
    ],
    "name": "` + _lt("flushed face") + `",
    "shortcodes": [
        ":flushed_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥺",
    "emoticons": [],
    "keywords": [
        "` + _lt("begging") + `",
        "` + _lt("mercy") + `",
        "` + _lt("pleading face") + `",
        "` + _lt("puppy eyes") + `"
    ],
    "name": "` + _lt("pleading face") + `",
    "shortcodes": [
        ":pleading_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😦",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("frown") + `",
        "` + _lt("frowning face with open mouth") + `",
        "` + _lt("mouth") + `",
        "` + _lt("open") + `"
    ],
    "name": "` + _lt("frowning face with open mouth") + `",
    "shortcodes": [
        ":frowning_face_with_open_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😧",
    "emoticons": [],
    "keywords": [
        "` + _lt("anguished") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("anguished face") + `",
    "shortcodes": [
        ":anguished_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😨",
    "emoticons": [
        ":'o"
    ],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("fear") + `",
        "` + _lt("fearful") + `",
        "` + _lt("scared") + `"
    ],
    "name": "` + _lt("fearful face") + `",
    "shortcodes": [
        ":fearful_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😰",
    "emoticons": [],
    "keywords": [
        "` + _lt("anxious face with sweat") + `",
        "` + _lt("blue") + `",
        "` + _lt("cold") + `",
        "` + _lt("face") + `",
        "` + _lt("rushed") + `",
        "` + _lt("sweat") + `"
    ],
    "name": "` + _lt("anxious face with sweat") + `",
    "shortcodes": [
        ":anxious_face_with_sweat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😥",
    "emoticons": [],
    "keywords": [
        "` + _lt("disappointed") + `",
        "` + _lt("face") + `",
        "` + _lt("relieved") + `",
        "` + _lt("sad but relieved face") + `",
        "` + _lt("whew") + `"
    ],
    "name": "` + _lt("sad but relieved face") + `",
    "shortcodes": [
        ":sad_but_relieved_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😢",
    "emoticons": [
        ":'("
    ],
    "keywords": [
        "` + _lt("cry") + `",
        "` + _lt("crying face") + `",
        "` + _lt("face") + `",
        "` + _lt("sad") + `",
        "` + _lt("tear") + `"
    ],
    "name": "` + _lt("crying face") + `",
    "shortcodes": [
        ":crying_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😭",
    "emoticons": [
        ":'-(",
        ":\\"("
    ],
    "keywords": [
        "` + _lt("cry") + `",
        "` + _lt("face") + `",
        "` + _lt("loudly crying face") + `",
        "` + _lt("sad") + `",
        "` + _lt("sob") + `",
        "` + _lt("tear") + `"
    ],
    "name": "` + _lt("loudly crying face") + `",
    "shortcodes": [
        ":loudly_crying_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😱",
    "emoticons": [
        ":@"
    ],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("face screaming in fear") + `",
        "` + _lt("fear") + `",
        "` + _lt("Munch") + `",
        "` + _lt("scared") + `",
        "` + _lt("scream") + `",
        "` + _lt("munch") + `"
    ],
    "name": "` + _lt("face screaming in fear") + `",
    "shortcodes": [
        ":face_screaming_in_fear:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😖",
    "emoticons": [],
    "keywords": [
        "` + _lt("confounded") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("confounded face") + `",
    "shortcodes": [
        ":confounded_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😣",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("persevere") + `",
        "` + _lt("persevering face") + `"
    ],
    "name": "` + _lt("persevering face") + `",
    "shortcodes": [
        ":persevering_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😞",
    "emoticons": [
        ":("
    ],
    "keywords": [
        "` + _lt("disappointed") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("disappointed face") + `",
    "shortcodes": [
        ":disappointed_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😓",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("downcast face with sweat") + `",
        "` + _lt("face") + `",
        "` + _lt("sweat") + `"
    ],
    "name": "` + _lt("downcast face with sweat") + `",
    "shortcodes": [
        ":downcast_face_with_sweat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😩",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("tired") + `",
        "` + _lt("weary") + `"
    ],
    "name": "` + _lt("weary face") + `",
    "shortcodes": [
        ":weary_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😫",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("tired") + `"
    ],
    "name": "` + _lt("tired face") + `",
    "shortcodes": [
        ":tired_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥱",
    "emoticons": [],
    "keywords": [
        "` + _lt("bored") + `",
        "` + _lt("tired") + `",
        "` + _lt("yawn") + `",
        "` + _lt("yawning face") + `"
    ],
    "name": "` + _lt("yawning face") + `",
    "shortcodes": [
        ":yawning_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😤",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("face with steam from nose") + `",
        "` + _lt("triumph") + `",
        "` + _lt("won") + `",
        "` + _lt("angry") + `",
        "` + _lt("frustration") + `"
    ],
    "name": "` + _lt("face with steam from nose") + `",
    "shortcodes": [
        ":face_with_steam_from_nose:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😡",
    "emoticons": [],
    "keywords": [
        "` + _lt("angry") + `",
        "` + _lt("enraged") + `",
        "` + _lt("face") + `",
        "` + _lt("mad") + `",
        "` + _lt("pouting") + `",
        "` + _lt("rage") + `",
        "` + _lt("red") + `"
    ],
    "name": "` + _lt("enraged face") + `",
    "shortcodes": [
        ":enraged_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😠",
    "emoticons": [
        "3:(",
        ">:("
    ],
    "keywords": [
        "` + _lt("anger") + `",
        "` + _lt("angry") + `",
        "` + _lt("face") + `",
        "` + _lt("mad") + `"
    ],
    "name": "` + _lt("angry face") + `",
    "shortcodes": [
        ":angry_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤬",
    "emoticons": [],
    "keywords": [
        "` + _lt("face with symbols on mouth") + `",
        "` + _lt("swearing") + `"
    ],
    "name": "` + _lt("face with symbols on mouth") + `",
    "shortcodes": [
        ":face_with_symbols_on_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😈",
    "emoticons": [
        "3:)",
        ">:)"
    ],
    "keywords": [
        "` + _lt("devil") + `",
        "` + _lt("face") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("horns") + `",
        "` + _lt("smile") + `",
        "` + _lt("smiling face with horns") + `",
        "` + _lt("fairy tale") + `"
    ],
    "name": "` + _lt("smiling face with horns") + `",
    "shortcodes": [
        ":smiling_face_with_horns:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👿",
    "emoticons": [],
    "keywords": [
        "` + _lt("angry face with horns") + `",
        "` + _lt("demon") + `",
        "` + _lt("devil") + `",
        "` + _lt("face") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("imp") + `"
    ],
    "name": "` + _lt("angry face with horns") + `",
    "shortcodes": [
        ":angry_face_with_horns:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💀",
    "emoticons": [
        ":skull"
    ],
    "keywords": [
        "` + _lt("death") + `",
        "` + _lt("face") + `",
        "` + _lt("fairy tale") + `",
        "` + _lt("monster") + `",
        "` + _lt("skull") + `"
    ],
    "name": "` + _lt("skull") + `",
    "shortcodes": [
        ":skull:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "☠️",
    "emoticons": [],
    "keywords": [
        "` + _lt("crossbones") + `",
        "` + _lt("death") + `",
        "` + _lt("face") + `",
        "` + _lt("monster") + `",
        "` + _lt("skull") + `",
        "` + _lt("skull and crossbones") + `"
    ],
    "name": "` + _lt("skull and crossbones") + `",
    "shortcodes": [
        ":skull_and_crossbones:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💩",
    "emoticons": [
        ":poop"
    ],
    "keywords": [
        "` + _lt("dung") + `",
        "` + _lt("face") + `",
        "` + _lt("monster") + `",
        "` + _lt("pile of poo") + `",
        "` + _lt("poo") + `",
        "` + _lt("poop") + `"
    ],
    "name": "` + _lt("pile of poo") + `",
    "shortcodes": [
        ":pile_of_poo:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤡",
    "emoticons": [],
    "keywords": [
        "` + _lt("clown") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("clown face") + `",
    "shortcodes": [
        ":clown_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👹",
    "emoticons": [],
    "keywords": [
        "` + _lt("creature") + `",
        "` + _lt("face") + `",
        "` + _lt("fairy tale") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("monster") + `",
        "` + _lt("ogre") + `"
    ],
    "name": "` + _lt("ogre") + `",
    "shortcodes": [
        ":ogre:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👺",
    "emoticons": [],
    "keywords": [
        "` + _lt("creature") + `",
        "` + _lt("face") + `",
        "` + _lt("fairy tale") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("goblin") + `",
        "` + _lt("monster") + `"
    ],
    "name": "` + _lt("goblin") + `",
    "shortcodes": [
        ":goblin:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👻",
    "emoticons": [
        ":ghost"
    ],
    "keywords": [
        "` + _lt("creature") + `",
        "` + _lt("face") + `",
        "` + _lt("fairy tale") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("ghost") + `",
        "` + _lt("monster") + `"
    ],
    "name": "` + _lt("ghost") + `",
    "shortcodes": [
        ":ghost:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👽",
    "emoticons": [
        ":et",
        ":alien"
    ],
    "keywords": [
        "` + _lt("alien") + `",
        "` + _lt("creature") + `",
        "` + _lt("extraterrestrial") + `",
        "` + _lt("face") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("ufo") + `"
    ],
    "name": "` + _lt("alien") + `",
    "shortcodes": [
        ":alien:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👾",
    "emoticons": [],
    "keywords": [
        "` + _lt("alien") + `",
        "` + _lt("creature") + `",
        "` + _lt("extraterrestrial") + `",
        "` + _lt("face") + `",
        "` + _lt("monster") + `",
        "` + _lt("ufo") + `"
    ],
    "name": "` + _lt("alien monster") + `",
    "shortcodes": [
        ":alien_monster:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤖",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("monster") + `",
        "` + _lt("robot") + `"
    ],
    "name": "` + _lt("robot") + `",
    "shortcodes": [
        ":robot:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😺",
    "emoticons": [
        ":kitten"
    ],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("face") + `",
        "` + _lt("grinning") + `",
        "` + _lt("mouth") + `",
        "` + _lt("open") + `",
        "` + _lt("smile") + `"
    ],
    "name": "` + _lt("grinning cat") + `",
    "shortcodes": [
        ":grinning_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😸",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("grin") + `",
        "` + _lt("grinning cat with smiling eyes") + `",
        "` + _lt("smile") + `"
    ],
    "name": "` + _lt("grinning cat with smiling eyes") + `",
    "shortcodes": [
        ":grinning_cat_with_smiling_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😹",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("cat with tears of joy") + `",
        "` + _lt("face") + `",
        "` + _lt("joy") + `",
        "` + _lt("tear") + `"
    ],
    "name": "` + _lt("cat with tears of joy") + `",
    "shortcodes": [
        ":cat_with_ltears_of_joy:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😻",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("heart") + `",
        "` + _lt("love") + `",
        "` + _lt("smile") + `",
        "` + _lt("smiling cat with heart-eyes") + `",
        "` + _lt("smiling cat face with heart eyes") + `",
        "` + _lt("smiling cat face with heart-eyes") + `"
    ],
    "name": "` + _lt("smiling cat with heart-eyes") + `",
    "shortcodes": [
        ":smiling_cat_with_heart-eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😼",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("cat with wry smile") + `",
        "` + _lt("face") + `",
        "` + _lt("ironic") + `",
        "` + _lt("smile") + `",
        "` + _lt("wry") + `"
    ],
    "name": "` + _lt("cat with wry smile") + `",
    "shortcodes": [
        ":cat_with_wry_smile:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😽",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("eye") + `",
        "` + _lt("face") + `",
        "` + _lt("kiss") + `",
        "` + _lt("kissing cat") + `"
    ],
    "name": "` + _lt("kissing cat") + `",
    "shortcodes": [
        ":kissing_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙀",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("face") + `",
        "` + _lt("oh") + `",
        "` + _lt("surprised") + `",
        "` + _lt("weary") + `"
    ],
    "name": "` + _lt("weary cat") + `",
    "shortcodes": [
        ":weary_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😿",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("cry") + `",
        "` + _lt("crying cat") + `",
        "` + _lt("face") + `",
        "` + _lt("sad") + `",
        "` + _lt("tear") + `"
    ],
    "name": "` + _lt("crying cat") + `",
    "shortcodes": [
        ":crying_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😾",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("face") + `",
        "` + _lt("pouting") + `"
    ],
    "name": "` + _lt("pouting cat") + `",
    "shortcodes": [
        ":pouting_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙈",
    "emoticons": [
        ":no_see"
    ],
    "keywords": [
        "` + _lt("evil") + `",
        "` + _lt("face") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("monkey") + `",
        "` + _lt("see") + `",
        "` + _lt("see-no-evil monkey") + `"
    ],
    "name": "` + _lt("see-no-evil monkey") + `",
    "shortcodes": [
        ":see-no-evil_monkey:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙉",
    "emoticons": [
        ":no_hear"
    ],
    "keywords": [
        "` + _lt("evil") + `",
        "` + _lt("face") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("hear") + `",
        "` + _lt("hear-no-evil monkey") + `",
        "` + _lt("monkey") + `"
    ],
    "name": "` + _lt("hear-no-evil monkey") + `",
    "shortcodes": [
        ":hear-no-evil_monkey:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙊",
    "emoticons": [
        ":no_speak"
    ],
    "keywords": [
        "` + _lt("evil") + `",
        "` + _lt("face") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("monkey") + `",
        "` + _lt("speak") + `",
        "` + _lt("speak-no-evil monkey") + `"
    ],
    "name": "` + _lt("speak-no-evil monkey") + `",
    "shortcodes": [
        ":speak-no-evil_monkey:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💋",
    "emoticons": [],
    "keywords": [
        "` + _lt("kiss") + `",
        "` + _lt("kiss mark") + `",
        "` + _lt("lips") + `"
    ],
    "name": "` + _lt("kiss mark") + `",
    "shortcodes": [
        ":kiss_mark:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💌",
    "emoticons": [],
    "keywords": [
        "` + _lt("heart") + `",
        "` + _lt("letter") + `",
        "` + _lt("love") + `",
        "` + _lt("mail") + `"
    ],
    "name": "` + _lt("love letter") + `",
    "shortcodes": [
        ":love_letter:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💘",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("cupid") + `",
        "` + _lt("heart with arrow") + `"
    ],
    "name": "` + _lt("heart with arrow") + `",
    "shortcodes": [
        ":heart_with_arrow:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💝",
    "emoticons": [],
    "keywords": [
        "` + _lt("heart with ribbon") + `",
        "` + _lt("ribbon") + `",
        "` + _lt("valentine") + `"
    ],
    "name": "` + _lt("heart with ribbon") + `",
    "shortcodes": [
        ":heart_with_ribbon:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💖",
    "emoticons": [],
    "keywords": [
        "` + _lt("excited") + `",
        "` + _lt("sparkle") + `",
        "` + _lt("sparkling heart") + `"
    ],
    "name": "` + _lt("sparkling heart") + `",
    "shortcodes": [
        ":sparkling_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💗",
    "emoticons": [],
    "keywords": [
        "` + _lt("excited") + `",
        "` + _lt("growing") + `",
        "` + _lt("growing heart") + `",
        "` + _lt("nervous") + `",
        "` + _lt("pulse") + `"
    ],
    "name": "` + _lt("growing heart") + `",
    "shortcodes": [
        ":growing_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💓",
    "emoticons": [],
    "keywords": [
        "` + _lt("beating") + `",
        "` + _lt("beating heart") + `",
        "` + _lt("heartbeat") + `",
        "` + _lt("pulsating") + `"
    ],
    "name": "` + _lt("beating heart") + `",
    "shortcodes": [
        ":beating_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💞",
    "emoticons": [],
    "keywords": [
        "` + _lt("revolving") + `",
        "` + _lt("revolving hearts") + `"
    ],
    "name": "` + _lt("revolving hearts") + `",
    "shortcodes": [
        ":revolving_hearts:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💕",
    "emoticons": [],
    "keywords": [
        "` + _lt("love") + `",
        "` + _lt("two hearts") + `"
    ],
    "name": "` + _lt("two hearts") + `",
    "shortcodes": [
        ":two_hearts:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💟",
    "emoticons": [],
    "keywords": [
        "` + _lt("heart") + `",
        "` + _lt("heart decoration") + `"
    ],
    "name": "` + _lt("heart decoration") + `",
    "shortcodes": [
        ":heart_decoration:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "❣️",
    "emoticons": [],
    "keywords": [
        "` + _lt("exclamation") + `",
        "` + _lt("heart exclamation") + `",
        "` + _lt("mark") + `",
        "` + _lt("punctuation") + `"
    ],
    "name": "` + _lt("heart exclamation") + `",
    "shortcodes": [
        ":heart_exclamation:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💔",
    "emoticons": [
        "</3",
        "&lt;/3"
    ],
    "keywords": [
        "` + _lt("break") + `",
        "` + _lt("broken") + `",
        "` + _lt("broken heart") + `"
    ],
    "name": "` + _lt("broken heart") + `",
    "shortcodes": [
        ":broken_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "❤️",
    "emoticons": [
        "<3",
        "&lt;3",
        ":heart"
    ],
    "keywords": [
        "` + _lt("heart") + `",
        "` + _lt("red heart") + `"
    ],
    "name": "` + _lt("red heart") + `",
    "shortcodes": [
        ":red_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🧡",
    "emoticons": [],
    "keywords": [
        "` + _lt("orange") + `",
        "` + _lt("orange heart") + `"
    ],
    "name": "` + _lt("orange heart") + `",
    "shortcodes": [
        ":orange_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💛",
    "emoticons": [],
    "keywords": [
        "` + _lt("yellow") + `",
        "` + _lt("yellow heart") + `"
    ],
    "name": "` + _lt("yellow heart") + `",
    "shortcodes": [
        ":yellow_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💚",
    "emoticons": [],
    "keywords": [
        "` + _lt("green") + `",
        "` + _lt("green heart") + `"
    ],
    "name": "` + _lt("green heart") + `",
    "shortcodes": [
        ":green_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💙",
    "emoticons": [],
    "keywords": [
        "` + _lt("blue") + `",
        "` + _lt("blue heart") + `"
    ],
    "name": "` + _lt("blue heart") + `",
    "shortcodes": [
        ":blue_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💜",
    "emoticons": [],
    "keywords": [
        "` + _lt("purple") + `",
        "` + _lt("purple heart") + `"
    ],
    "name": "` + _lt("purple heart") + `",
    "shortcodes": [
        ":purple_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤎",
    "emoticons": [],
    "keywords": [
        "` + _lt("brown") + `",
        "` + _lt("heart") + `"
    ],
    "name": "` + _lt("brown heart") + `",
    "shortcodes": [
        ":brown_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🖤",
    "emoticons": [],
    "keywords": [
        "` + _lt("black") + `",
        "` + _lt("black heart") + `",
        "` + _lt("evil") + `",
        "` + _lt("wicked") + `"
    ],
    "name": "` + _lt("black heart") + `",
    "shortcodes": [
        ":black_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤍",
    "emoticons": [],
    "keywords": [
        "` + _lt("heart") + `",
        "` + _lt("white") + `"
    ],
    "name": "` + _lt("white heart") + `",
    "shortcodes": [
        ":white_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💯",
    "emoticons": [],
    "keywords": [
        "` + _lt("100") + `",
        "` + _lt("full") + `",
        "` + _lt("hundred") + `",
        "` + _lt("hundred points") + `",
        "` + _lt("score") + `"
    ],
    "name": "` + _lt("hundred points") + `",
    "shortcodes": [
        ":hundred_points:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💢",
    "emoticons": [],
    "keywords": [
        "` + _lt("anger symbol") + `",
        "` + _lt("angry") + `",
        "` + _lt("comic") + `",
        "` + _lt("mad") + `"
    ],
    "name": "` + _lt("anger symbol") + `",
    "shortcodes": [
        ":anger_symbol:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💥",
    "emoticons": [],
    "keywords": [
        "` + _lt("boom") + `",
        "` + _lt("collision") + `",
        "` + _lt("comic") + `"
    ],
    "name": "` + _lt("collision") + `",
    "shortcodes": [
        ":collision:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💫",
    "emoticons": [],
    "keywords": [
        "` + _lt("comic") + `",
        "` + _lt("dizzy") + `",
        "` + _lt("star") + `"
    ],
    "name": "` + _lt("dizzy") + `",
    "shortcodes": [
        ":dizzy:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💦",
    "emoticons": [],
    "keywords": [
        "` + _lt("comic") + `",
        "` + _lt("splashing") + `",
        "` + _lt("sweat") + `",
        "` + _lt("sweat droplets") + `"
    ],
    "name": "` + _lt("sweat droplets") + `",
    "shortcodes": [
        ":sweat_droplets:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💨",
    "emoticons": [],
    "keywords": [
        "` + _lt("comic") + `",
        "` + _lt("dash") + `",
        "` + _lt("dashing away") + `",
        "` + _lt("running") + `"
    ],
    "name": "` + _lt("dashing away") + `",
    "shortcodes": [
        ":dashing_away:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🕳️",
    "emoticons": [],
    "keywords": [
        "` + _lt("hole") + `"
    ],
    "name": "` + _lt("hole") + `",
    "shortcodes": [
        ":hole:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💣",
    "emoticons": [],
    "keywords": [
        "` + _lt("bomb") + `",
        "` + _lt("comic") + `"
    ],
    "name": "` + _lt("bomb") + `",
    "shortcodes": [
        ":bomb:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💬",
    "emoticons": [],
    "keywords": [
        "` + _lt("balloon") + `",
        "` + _lt("bubble") + `",
        "` + _lt("comic") + `",
        "` + _lt("dialog") + `",
        "` + _lt("speech") + `"
    ],
    "name": "` + _lt("speech balloon") + `",
    "shortcodes": [
        ":speech_balloon:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👁️‍🗨️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("eye in speech bubble") + `",
    "shortcodes": [
        ":eye_in_speech_bubble:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🗨️",
    "emoticons": [],
    "keywords": [
        "` + _lt("balloon") + `",
        "` + _lt("bubble") + `",
        "` + _lt("dialog") + `",
        "` + _lt("left speech bubble") + `",
        "` + _lt("speech") + `",
        "` + _lt("dialogue") + `"
    ],
    "name": "` + _lt("left speech bubble") + `",
    "shortcodes": [
        ":left_speech_bubble:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🗯️",
    "emoticons": [],
    "keywords": [
        "` + _lt("angry") + `",
        "` + _lt("balloon") + `",
        "` + _lt("bubble") + `",
        "` + _lt("mad") + `",
        "` + _lt("right anger bubble") + `"
    ],
    "name": "` + _lt("right anger bubble") + `",
    "shortcodes": [
        ":right_anger_bubble:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💭",
    "emoticons": [],
    "keywords": [
        "` + _lt("balloon") + `",
        "` + _lt("bubble") + `",
        "` + _lt("comic") + `",
        "` + _lt("thought") + `"
    ],
    "name": "` + _lt("thought balloon") + `",
    "shortcodes": [
        ":thought_balloon:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💤",
    "emoticons": [],
    "keywords": [
        "` + _lt("comic") + `",
        "` + _lt("good night") + `",
        "` + _lt("sleep") + `",
        "` + _lt("ZZZ") + `"
    ],
    "name": "` + _lt("ZZZ") + `",
    "shortcodes": [
        ":ZZZ:"
    ]
},`;

const emojisData2 = `{
    "category": "People & Body",
    "codepoints": "👋",
    "emoticons": [],
    "keywords": [
        "` + _lt("hand") + `",
        "` + _lt("wave") + `",
        "` + _lt("waving") + `"
    ],
    "name": "` + _lt("waving hand") + `",
    "shortcodes": [
        ":waving_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤚",
    "emoticons": [],
    "keywords": [
        "` + _lt("backhand") + `",
        "` + _lt("raised") + `",
        "` + _lt("raised back of hand") + `"
    ],
    "name": "` + _lt("raised back of hand") + `",
    "shortcodes": [
        ":raised_back_of_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🖐️",
    "emoticons": [],
    "keywords": [
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("hand with fingers splayed") + `",
        "` + _lt("splayed") + `"
    ],
    "name": "` + _lt("hand with fingers splayed") + `",
    "shortcodes": [
        ":hand_with_fingers_splayed:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "✋",
    "emoticons": [],
    "keywords": [
        "` + _lt("hand") + `",
        "` + _lt("high 5") + `",
        "` + _lt("high five") + `",
        "` + _lt("raised hand") + `"
    ],
    "name": "` + _lt("raised hand") + `",
    "shortcodes": [
        ":raised_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🖖",
    "emoticons": [],
    "keywords": [
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("spock") + `",
        "` + _lt("vulcan") + `",
        "` + _lt("Vulcan salute") + `",
        "` + _lt("vulcan salute") + `"
    ],
    "name": "` + _lt("vulcan salute") + `",
    "shortcodes": [
        ":vulcan_salute:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👌",
    "emoticons": [
        ":ok"
    ],
    "keywords": [
        "` + _lt("hand") + `",
        "` + _lt("OK") + `",
        "` + _lt("perfect") + `"
    ],
    "name": "` + _lt("OK hand") + `",
    "shortcodes": [
        ":OK_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤏",
    "emoticons": [],
    "keywords": [
        "` + _lt("pinching hand") + `",
        "` + _lt("small amount") + `"
    ],
    "name": "` + _lt("pinching hand") + `",
    "shortcodes": [
        ":pinching_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "✌️",
    "emoticons": [],
    "keywords": [
        "` + _lt("hand") + `",
        "` + _lt("v") + `",
        "` + _lt("victory") + `"
    ],
    "name": "` + _lt("victory hand") + `",
    "shortcodes": [
        ":victory_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤞",
    "emoticons": [],
    "keywords": [
        "` + _lt("cross") + `",
        "` + _lt("crossed fingers") + `",
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("luck") + `",
        "` + _lt("good luck") + `"
    ],
    "name": "` + _lt("crossed fingers") + `",
    "shortcodes": [
        ":crossed_fingers:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤟",
    "emoticons": [],
    "keywords": [
        "` + _lt("hand") + `",
        "` + _lt("ILY") + `",
        "` + _lt("love-you gesture") + `",
        "` + _lt("love you gesture") + `"
    ],
    "name": "` + _lt("love-you gesture") + `",
    "shortcodes": [
        ":love-you_gesture:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤘",
    "emoticons": [],
    "keywords": [
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("horns") + `",
        "` + _lt("rock-on") + `",
        "` + _lt("sign of the horns") + `",
        "` + _lt("rock on") + `"
    ],
    "name": "` + _lt("sign of the horns") + `",
    "shortcodes": [
        ":sign_of_lthe_horns:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤙",
    "emoticons": [],
    "keywords": [
        "` + _lt("call") + `",
        "` + _lt("call me hand") + `",
        "` + _lt("call-me hand") + `",
        "` + _lt("hand") + `",
        "` + _lt("shaka") + `",
        "` + _lt("hang loose") + `",
        "` + _lt("Shaka") + `"
    ],
    "name": "` + _lt("call me hand") + `",
    "shortcodes": [
        ":call_me_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👈",
    "emoticons": [],
    "keywords": [
        "` + _lt("backhand") + `",
        "` + _lt("backhand index pointing left") + `",
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("index") + `",
        "` + _lt("point") + `"
    ],
    "name": "` + _lt("backhand index pointing left") + `",
    "shortcodes": [
        ":backhand_index_pointing_left:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👉",
    "emoticons": [],
    "keywords": [
        "` + _lt("backhand") + `",
        "` + _lt("backhand index pointing right") + `",
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("index") + `",
        "` + _lt("point") + `"
    ],
    "name": "` + _lt("backhand index pointing right") + `",
    "shortcodes": [
        ":backhand_index_pointing_right:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👆",
    "emoticons": [],
    "keywords": [
        "` + _lt("backhand") + `",
        "` + _lt("backhand index pointing up") + `",
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("point") + `",
        "` + _lt("up") + `"
    ],
    "name": "` + _lt("backhand index pointing up") + `",
    "shortcodes": [
        ":backhand_index_pointing_up:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🖕",
    "emoticons": [],
    "keywords": [
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("middle finger") + `"
    ],
    "name": "` + _lt("middle finger") + `",
    "shortcodes": [
        ":middle_finger:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👇",
    "emoticons": [],
    "keywords": [
        "` + _lt("backhand") + `",
        "` + _lt("backhand index pointing down") + `",
        "` + _lt("down") + `",
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("point") + `"
    ],
    "name": "` + _lt("backhand index pointing down") + `",
    "shortcodes": [
        ":backhand_index_pointing_down:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "☝️",
    "emoticons": [],
    "keywords": [
        "` + _lt("finger") + `",
        "` + _lt("hand") + `",
        "` + _lt("index") + `",
        "` + _lt("index pointing up") + `",
        "` + _lt("point") + `",
        "` + _lt("up") + `"
    ],
    "name": "` + _lt("index pointing up") + `",
    "shortcodes": [
        ":index_pointing_up:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👍",
    "emoticons": [
        ":+1"
    ],
    "keywords": [
        "` + _lt("+1") + `",
        "` + _lt("hand") + `",
        "` + _lt("thumb") + `",
        "` + _lt("thumbs up") + `",
        "` + _lt("up") + `"
    ],
    "name": "` + _lt("thumbs up") + `",
    "shortcodes": [
        ":thumbs_up:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👎",
    "emoticons": [
        ":-1"
    ],
    "keywords": [
        "` + _lt("-1") + `",
        "` + _lt("down") + `",
        "` + _lt("hand") + `",
        "` + _lt("thumb") + `",
        "` + _lt("thumbs down") + `"
    ],
    "name": "` + _lt("thumbs down") + `",
    "shortcodes": [
        ":thumbs_down:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "✊",
    "emoticons": [],
    "keywords": [
        "` + _lt("clenched") + `",
        "` + _lt("fist") + `",
        "` + _lt("hand") + `",
        "` + _lt("punch") + `",
        "` + _lt("raised fist") + `"
    ],
    "name": "` + _lt("raised fist") + `",
    "shortcodes": [
        ":raised_fist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👊",
    "emoticons": [],
    "keywords": [
        "` + _lt("clenched") + `",
        "` + _lt("fist") + `",
        "` + _lt("hand") + `",
        "` + _lt("oncoming fist") + `",
        "` + _lt("punch") + `"
    ],
    "name": "` + _lt("oncoming fist") + `",
    "shortcodes": [
        ":oncoming_fist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤛",
    "emoticons": [],
    "keywords": [
        "` + _lt("fist") + `",
        "` + _lt("left-facing fist") + `",
        "` + _lt("leftwards") + `",
        "` + _lt("leftward") + `"
    ],
    "name": "` + _lt("left-facing fist") + `",
    "shortcodes": [
        ":left-facing_fist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤜",
    "emoticons": [],
    "keywords": [
        "` + _lt("fist") + `",
        "` + _lt("right-facing fist") + `",
        "` + _lt("rightwards") + `",
        "` + _lt("rightward") + `"
    ],
    "name": "` + _lt("right-facing fist") + `",
    "shortcodes": [
        ":right-facing_fist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👏",
    "emoticons": [],
    "keywords": [
        "` + _lt("clap") + `",
        "` + _lt("clapping hands") + `",
        "` + _lt("hand") + `"
    ],
    "name": "` + _lt("clapping hands") + `",
    "shortcodes": [
        ":clapping_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙌",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("gesture") + `",
        "` + _lt("hand") + `",
        "` + _lt("hooray") + `",
        "` + _lt("raised") + `",
        "` + _lt("raising hands") + `",
        "` + _lt("woo hoo") + `",
        "` + _lt("yay") + `"
    ],
    "name": "` + _lt("raising hands") + `",
    "shortcodes": [
        ":raising_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👐",
    "emoticons": [],
    "keywords": [
        "` + _lt("hand") + `",
        "` + _lt("open") + `",
        "` + _lt("open hands") + `"
    ],
    "name": "` + _lt("open hands") + `",
    "shortcodes": [
        ":open_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤲",
    "emoticons": [],
    "keywords": [
        "` + _lt("palms up together") + `",
        "` + _lt("prayer") + `"
    ],
    "name": "` + _lt("palms up together") + `",
    "shortcodes": [
        ":palms_up_ltogether:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤝",
    "emoticons": [],
    "keywords": [
        "` + _lt("agreement") + `",
        "` + _lt("hand") + `",
        "` + _lt("handshake") + `",
        "` + _lt("meeting") + `",
        "` + _lt("shake") + `"
    ],
    "name": "` + _lt("handshake") + `",
    "shortcodes": [
        ":handshake:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙏",
    "emoticons": [],
    "keywords": [
        "` + _lt("ask") + `",
        "` + _lt("folded hands") + `",
        "` + _lt("hand") + `",
        "` + _lt("high 5") + `",
        "` + _lt("high five") + `",
        "` + _lt("please") + `",
        "` + _lt("pray") + `",
        "` + _lt("thanks") + `"
    ],
    "name": "` + _lt("folded hands") + `",
    "shortcodes": [
        ":folded_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "✍️",
    "emoticons": [],
    "keywords": [
        "` + _lt("hand") + `",
        "` + _lt("write") + `",
        "` + _lt("writing hand") + `"
    ],
    "name": "` + _lt("writing hand") + `",
    "shortcodes": [
        ":writing_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💅",
    "emoticons": [],
    "keywords": [
        "` + _lt("care") + `",
        "` + _lt("cosmetics") + `",
        "` + _lt("manicure") + `",
        "` + _lt("nail") + `",
        "` + _lt("polish") + `"
    ],
    "name": "` + _lt("nail polish") + `",
    "shortcodes": [
        ":nail_polish:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤳",
    "emoticons": [],
    "keywords": [
        "` + _lt("camera") + `",
        "` + _lt("phone") + `",
        "` + _lt("selfie") + `"
    ],
    "name": "` + _lt("selfie") + `",
    "shortcodes": [
        ":selfie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💪",
    "emoticons": [],
    "keywords": [
        "` + _lt("biceps") + `",
        "` + _lt("comic") + `",
        "` + _lt("flex") + `",
        "` + _lt("flexed biceps") + `",
        "` + _lt("muscle") + `"
    ],
    "name": "` + _lt("flexed biceps") + `",
    "shortcodes": [
        ":flexed_biceps:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦾",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("mechanical arm") + `",
        "` + _lt("prosthetic") + `"
    ],
    "name": "` + _lt("mechanical arm") + `",
    "shortcodes": [
        ":mechanical_arm:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦿",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("mechanical leg") + `",
        "` + _lt("prosthetic") + `"
    ],
    "name": "` + _lt("mechanical leg") + `",
    "shortcodes": [
        ":mechanical_leg:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦵",
    "emoticons": [],
    "keywords": [
        "` + _lt("kick") + `",
        "` + _lt("leg") + `",
        "` + _lt("limb") + `"
    ],
    "name": "` + _lt("leg") + `",
    "shortcodes": [
        ":leg:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦶",
    "emoticons": [],
    "keywords": [
        "` + _lt("foot") + `",
        "` + _lt("kick") + `",
        "` + _lt("stomp") + `"
    ],
    "name": "` + _lt("foot") + `",
    "shortcodes": [
        ":foot:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👂",
    "emoticons": [],
    "keywords": [
        "` + _lt("body") + `",
        "` + _lt("ear") + `"
    ],
    "name": "` + _lt("ear") + `",
    "shortcodes": [
        ":ear:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦻",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("ear with hearing aid") + `",
        "` + _lt("hard of hearing") + `",
        "` + _lt("hearing impaired") + `"
    ],
    "name": "` + _lt("ear with hearing aid") + `",
    "shortcodes": [
        ":ear_with_hearing_aid:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👃",
    "emoticons": [],
    "keywords": [
        "` + _lt("body") + `",
        "` + _lt("nose") + `"
    ],
    "name": "` + _lt("nose") + `",
    "shortcodes": [
        ":nose:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧠",
    "emoticons": [],
    "keywords": [
        "` + _lt("brain") + `",
        "` + _lt("intelligent") + `"
    ],
    "name": "` + _lt("brain") + `",
    "shortcodes": [
        ":brain:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦷",
    "emoticons": [],
    "keywords": [
        "` + _lt("dentist") + `",
        "` + _lt("tooth") + `"
    ],
    "name": "` + _lt("tooth") + `",
    "shortcodes": [
        ":tooth:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦴",
    "emoticons": [],
    "keywords": [
        "` + _lt("bone") + `",
        "` + _lt("skeleton") + `"
    ],
    "name": "` + _lt("bone") + `",
    "shortcodes": [
        ":bone:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👀",
    "emoticons": [],
    "keywords": [
        "` + _lt("eye") + `",
        "` + _lt("eyes") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("eyes") + `",
    "shortcodes": [
        ":eyes:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👁️",
    "emoticons": [],
    "keywords": [
        "` + _lt("body") + `",
        "` + _lt("eye") + `"
    ],
    "name": "` + _lt("eye") + `",
    "shortcodes": [
        ":eye:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👅",
    "emoticons": [],
    "keywords": [
        "` + _lt("body") + `",
        "` + _lt("tongue") + `"
    ],
    "name": "` + _lt("tongue") + `",
    "shortcodes": [
        ":tongue:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👄",
    "emoticons": [],
    "keywords": [
        "` + _lt("lips") + `",
        "` + _lt("mouth") + `"
    ],
    "name": "` + _lt("mouth") + `",
    "shortcodes": [
        ":mouth:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👶",
    "emoticons": [],
    "keywords": [
        "` + _lt("baby") + `",
        "` + _lt("young") + `"
    ],
    "name": "` + _lt("baby") + `",
    "shortcodes": [
        ":baby:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧒",
    "emoticons": [],
    "keywords": [
        "` + _lt("child") + `",
        "` + _lt("gender-neutral") + `",
        "` + _lt("unspecified gender") + `",
        "` + _lt("young") + `"
    ],
    "name": "` + _lt("child") + `",
    "shortcodes": [
        ":child:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("young") + `",
        "` + _lt("young person") + `"
    ],
    "name": "` + _lt("boy") + `",
    "shortcodes": [
        ":boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("girl") + `",
        "` + _lt("Virgo") + `",
        "` + _lt("young person") + `",
        "` + _lt("zodiac") + `",
        "` + _lt("young") + `"
    ],
    "name": "` + _lt("girl") + `",
    "shortcodes": [
        ":girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧑",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("gender-neutral") + `",
        "` + _lt("person") + `",
        "` + _lt("unspecified gender") + `"
    ],
    "name": "` + _lt("person") + `",
    "shortcodes": [
        ":person:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👱",
    "emoticons": [],
    "keywords": [
        "` + _lt("blond") + `",
        "` + _lt("blond-haired person") + `",
        "` + _lt("hair") + `",
        "` + _lt("person: blond hair") + `"
    ],
    "name": "` + _lt("person: blond hair") + `",
    "shortcodes": [
        ":person:_blond_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("man") + `",
    "shortcodes": [
        ":man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧔",
    "emoticons": [],
    "keywords": [
        "` + _lt("beard") + `",
        "` + _lt("person") + `",
        "` + _lt("person: beard") + `"
    ],
    "name": "` + _lt("person: beard") + `",
    "shortcodes": [
        ":person:_beard:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦰",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("man") + `",
        "` + _lt("red hair") + `"
    ],
    "name": "` + _lt("man: red hair") + `",
    "shortcodes": [
        ":man:_red_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦱",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("curly hair") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("man: curly hair") + `",
    "shortcodes": [
        ":man:_curly_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦳",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("man") + `",
        "` + _lt("white hair") + `"
    ],
    "name": "` + _lt("man: white hair") + `",
    "shortcodes": [
        ":man:_white_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦲",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("bald") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("man: bald") + `",
    "shortcodes": [
        ":man:_bald:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman") + `",
    "shortcodes": [
        ":woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦰",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("red hair") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman: red hair") + `",
    "shortcodes": [
        ":woman:_red_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦱",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("curly hair") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman: curly hair") + `",
    "shortcodes": [
        ":woman:_curly_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦳",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("white hair") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman: white hair") + `",
    "shortcodes": [
        ":woman:_white_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦲",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("bald") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman: bald") + `",
    "shortcodes": [
        ":woman:_bald:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👱‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("blond-haired woman") + `",
        "` + _lt("blonde") + `",
        "` + _lt("hair") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman: blond hair") + `"
    ],
    "name": "` + _lt("woman: blond hair") + `",
    "shortcodes": [
        ":woman:_blond_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👱‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("blond") + `",
        "` + _lt("blond-haired man") + `",
        "` + _lt("hair") + `",
        "` + _lt("man") + `",
        "` + _lt("man: blond hair") + `"
    ],
    "name": "` + _lt("man: blond hair") + `",
    "shortcodes": [
        ":man:_blond_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧓",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("gender-neutral") + `",
        "` + _lt("old") + `",
        "` + _lt("older person") + `",
        "` + _lt("unspecified gender") + `"
    ],
    "name": "` + _lt("older person") + `",
    "shortcodes": [
        ":older_person:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👴",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("man") + `",
        "` + _lt("old") + `"
    ],
    "name": "` + _lt("old man") + `",
    "shortcodes": [
        ":old_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👵",
    "emoticons": [],
    "keywords": [
        "` + _lt("adult") + `",
        "` + _lt("old") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("old woman") + `",
    "shortcodes": [
        ":old_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙍",
    "emoticons": [],
    "keywords": [
        "` + _lt("frown") + `",
        "` + _lt("gesture") + `",
        "` + _lt("person frowning") + `"
    ],
    "name": "` + _lt("person frowning") + `",
    "shortcodes": [
        ":person_frowning:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙍‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("frowning") + `",
        "` + _lt("gesture") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("man frowning") + `",
    "shortcodes": [
        ":man_frowning:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙍‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("frowning") + `",
        "` + _lt("gesture") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman frowning") + `",
    "shortcodes": [
        ":woman_frowning:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙎",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("person pouting") + `",
        "` + _lt("pouting") + `"
    ],
    "name": "` + _lt("person pouting") + `",
    "shortcodes": [
        ":person_pouting:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙎‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("man") + `",
        "` + _lt("pouting") + `"
    ],
    "name": "` + _lt("man pouting") + `",
    "shortcodes": [
        ":man_pouting:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙎‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("pouting") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman pouting") + `",
    "shortcodes": [
        ":woman_pouting:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙅",
    "emoticons": [],
    "keywords": [
        "` + _lt("forbidden") + `",
        "` + _lt("gesture") + `",
        "` + _lt("hand") + `",
        "` + _lt("person gesturing NO") + `",
        "` + _lt("prohibited") + `"
    ],
    "name": "` + _lt("person gesturing NO") + `",
    "shortcodes": [
        ":person_gesturing_NO:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙅‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("forbidden") + `",
        "` + _lt("gesture") + `",
        "` + _lt("hand") + `",
        "` + _lt("man") + `",
        "` + _lt("man gesturing NO") + `",
        "` + _lt("prohibited") + `"
    ],
    "name": "` + _lt("man gesturing NO") + `",
    "shortcodes": [
        ":man_gesturing_NO:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙅‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("forbidden") + `",
        "` + _lt("gesture") + `",
        "` + _lt("hand") + `",
        "` + _lt("prohibited") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman gesturing NO") + `"
    ],
    "name": "` + _lt("woman gesturing NO") + `",
    "shortcodes": [
        ":woman_gesturing_NO:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙆",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("hand") + `",
        "` + _lt("OK") + `",
        "` + _lt("person gesturing OK") + `"
    ],
    "name": "` + _lt("person gesturing OK") + `",
    "shortcodes": [
        ":person_gesturing_OK:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙆‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("hand") + `",
        "` + _lt("man") + `",
        "` + _lt("man gesturing OK") + `",
        "` + _lt("OK") + `"
    ],
    "name": "` + _lt("man gesturing OK") + `",
    "shortcodes": [
        ":man_gesturing_OK:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙆‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("hand") + `",
        "` + _lt("OK") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman gesturing OK") + `"
    ],
    "name": "` + _lt("woman gesturing OK") + `",
    "shortcodes": [
        ":woman_gesturing_OK:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💁",
    "emoticons": [],
    "keywords": [
        "` + _lt("hand") + `",
        "` + _lt("help") + `",
        "` + _lt("information") + `",
        "` + _lt("person tipping hand") + `",
        "` + _lt("sassy") + `",
        "` + _lt("tipping") + `"
    ],
    "name": "` + _lt("person tipping hand") + `",
    "shortcodes": [
        ":person_ltipping_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💁‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man") + `",
        "` + _lt("man tipping hand") + `",
        "` + _lt("sassy") + `",
        "` + _lt("tipping hand") + `"
    ],
    "name": "` + _lt("man tipping hand") + `",
    "shortcodes": [
        ":man_ltipping_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💁‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("sassy") + `",
        "` + _lt("tipping hand") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman tipping hand") + `"
    ],
    "name": "` + _lt("woman tipping hand") + `",
    "shortcodes": [
        ":woman_ltipping_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙋",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("hand") + `",
        "` + _lt("happy") + `",
        "` + _lt("person raising hand") + `",
        "` + _lt("raised") + `"
    ],
    "name": "` + _lt("person raising hand") + `",
    "shortcodes": [
        ":person_raising_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙋‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("man") + `",
        "` + _lt("man raising hand") + `",
        "` + _lt("raising hand") + `"
    ],
    "name": "` + _lt("man raising hand") + `",
    "shortcodes": [
        ":man_raising_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙋‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("gesture") + `",
        "` + _lt("raising hand") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman raising hand") + `"
    ],
    "name": "` + _lt("woman raising hand") + `",
    "shortcodes": [
        ":woman_raising_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧏",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("deaf") + `",
        "` + _lt("deaf person") + `",
        "` + _lt("ear") + `",
        "` + _lt("hear") + `",
        "` + _lt("hearing impaired") + `"
    ],
    "name": "` + _lt("deaf person") + `",
    "shortcodes": [
        ":deaf_person:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧏‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("deaf") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("deaf man") + `",
    "shortcodes": [
        ":deaf_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧏‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("deaf") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("deaf woman") + `",
    "shortcodes": [
        ":deaf_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙇",
    "emoticons": [],
    "keywords": [
        "` + _lt("apology") + `",
        "` + _lt("bow") + `",
        "` + _lt("gesture") + `",
        "` + _lt("person bowing") + `",
        "` + _lt("sorry") + `"
    ],
    "name": "` + _lt("person bowing") + `",
    "shortcodes": [
        ":person_bowing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙇‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("apology") + `",
        "` + _lt("bowing") + `",
        "` + _lt("favor") + `",
        "` + _lt("gesture") + `",
        "` + _lt("man") + `",
        "` + _lt("sorry") + `"
    ],
    "name": "` + _lt("man bowing") + `",
    "shortcodes": [
        ":man_bowing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙇‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("apology") + `",
        "` + _lt("bowing") + `",
        "` + _lt("favor") + `",
        "` + _lt("gesture") + `",
        "` + _lt("sorry") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman bowing") + `",
    "shortcodes": [
        ":woman_bowing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤦",
    "emoticons": [],
    "keywords": [
        "` + _lt("disbelief") + `",
        "` + _lt("exasperation") + `",
        "` + _lt("face") + `",
        "` + _lt("palm") + `",
        "` + _lt("person facepalming") + `"
    ],
    "name": "` + _lt("person facepalming") + `",
    "shortcodes": [
        ":person_facepalming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤦‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("disbelief") + `",
        "` + _lt("exasperation") + `",
        "` + _lt("facepalm") + `",
        "` + _lt("man") + `",
        "` + _lt("man facepalming") + `"
    ],
    "name": "` + _lt("man facepalming") + `",
    "shortcodes": [
        ":man_facepalming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤦‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("disbelief") + `",
        "` + _lt("exasperation") + `",
        "` + _lt("facepalm") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman facepalming") + `"
    ],
    "name": "` + _lt("woman facepalming") + `",
    "shortcodes": [
        ":woman_facepalming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤷",
    "emoticons": [],
    "keywords": [
        "` + _lt("doubt") + `",
        "` + _lt("ignorance") + `",
        "` + _lt("indifference") + `",
        "` + _lt("person shrugging") + `",
        "` + _lt("shrug") + `"
    ],
    "name": "` + _lt("person shrugging") + `",
    "shortcodes": [
        ":person_shrugging:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤷‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("doubt") + `",
        "` + _lt("ignorance") + `",
        "` + _lt("indifference") + `",
        "` + _lt("man") + `",
        "` + _lt("man shrugging") + `",
        "` + _lt("shrug") + `"
    ],
    "name": "` + _lt("man shrugging") + `",
    "shortcodes": [
        ":man_shrugging:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤷‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("doubt") + `",
        "` + _lt("ignorance") + `",
        "` + _lt("indifference") + `",
        "` + _lt("shrug") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman shrugging") + `"
    ],
    "name": "` + _lt("woman shrugging") + `",
    "shortcodes": [
        ":woman_shrugging:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍⚕️",
    "emoticons": [],
    "keywords": [
        "` + _lt("doctor") + `",
        "` + _lt("healthcare") + `",
        "` + _lt("man") + `",
        "` + _lt("man health worker") + `",
        "` + _lt("nurse") + `",
        "` + _lt("therapist") + `",
        "` + _lt("health care") + `"
    ],
    "name": "` + _lt("man health worker") + `",
    "shortcodes": [
        ":man_health_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍⚕️",
    "emoticons": [],
    "keywords": [
        "` + _lt("doctor") + `",
        "` + _lt("healthcare") + `",
        "` + _lt("nurse") + `",
        "` + _lt("therapist") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman health worker") + `",
        "` + _lt("health care") + `"
    ],
    "name": "` + _lt("woman health worker") + `",
    "shortcodes": [
        ":woman_health_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🎓",
    "emoticons": [],
    "keywords": [
        "` + _lt("graduate") + `",
        "` + _lt("man") + `",
        "` + _lt("student") + `"
    ],
    "name": "` + _lt("man student") + `",
    "shortcodes": [
        ":man_student:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🎓",
    "emoticons": [],
    "keywords": [
        "` + _lt("graduate") + `",
        "` + _lt("student") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman student") + `",
    "shortcodes": [
        ":woman_student:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🏫",
    "emoticons": [],
    "keywords": [
        "` + _lt("instructor") + `",
        "` + _lt("man") + `",
        "` + _lt("professor") + `",
        "` + _lt("teacher") + `"
    ],
    "name": "` + _lt("man teacher") + `",
    "shortcodes": [
        ":man_lteacher:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🏫",
    "emoticons": [],
    "keywords": [
        "` + _lt("instructor") + `",
        "` + _lt("professor") + `",
        "` + _lt("teacher") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman teacher") + `",
    "shortcodes": [
        ":woman_lteacher:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍⚖️",
    "emoticons": [],
    "keywords": [
        "` + _lt("judge") + `",
        "` + _lt("justice") + `",
        "` + _lt("man") + `",
        "` + _lt("scales") + `"
    ],
    "name": "` + _lt("man judge") + `",
    "shortcodes": [
        ":man_judge:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍⚖️",
    "emoticons": [],
    "keywords": [
        "` + _lt("judge") + `",
        "` + _lt("justice") + `",
        "` + _lt("scales") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman judge") + `",
    "shortcodes": [
        ":woman_judge:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🌾",
    "emoticons": [],
    "keywords": [
        "` + _lt("farmer") + `",
        "` + _lt("gardener") + `",
        "` + _lt("man") + `",
        "` + _lt("rancher") + `"
    ],
    "name": "` + _lt("man farmer") + `",
    "shortcodes": [
        ":man_farmer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🌾",
    "emoticons": [],
    "keywords": [
        "` + _lt("farmer") + `",
        "` + _lt("gardener") + `",
        "` + _lt("rancher") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman farmer") + `",
    "shortcodes": [
        ":woman_farmer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🍳",
    "emoticons": [],
    "keywords": [
        "` + _lt("chef") + `",
        "` + _lt("cook") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("man cook") + `",
    "shortcodes": [
        ":man_cook:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🍳",
    "emoticons": [],
    "keywords": [
        "` + _lt("chef") + `",
        "` + _lt("cook") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman cook") + `",
    "shortcodes": [
        ":woman_cook:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🔧",
    "emoticons": [],
    "keywords": [
        "` + _lt("electrician") + `",
        "` + _lt("man") + `",
        "` + _lt("mechanic") + `",
        "` + _lt("plumber") + `",
        "` + _lt("tradesperson") + `"
    ],
    "name": "` + _lt("man mechanic") + `",
    "shortcodes": [
        ":man_mechanic:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🔧",
    "emoticons": [],
    "keywords": [
        "` + _lt("electrician") + `",
        "` + _lt("mechanic") + `",
        "` + _lt("plumber") + `",
        "` + _lt("tradesperson") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman mechanic") + `",
    "shortcodes": [
        ":woman_mechanic:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🏭",
    "emoticons": [],
    "keywords": [
        "` + _lt("assembly") + `",
        "` + _lt("factory") + `",
        "` + _lt("industrial") + `",
        "` + _lt("man") + `",
        "` + _lt("worker") + `"
    ],
    "name": "` + _lt("man factory worker") + `",
    "shortcodes": [
        ":man_factory_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🏭",
    "emoticons": [],
    "keywords": [
        "` + _lt("assembly") + `",
        "` + _lt("factory") + `",
        "` + _lt("industrial") + `",
        "` + _lt("woman") + `",
        "` + _lt("worker") + `"
    ],
    "name": "` + _lt("woman factory worker") + `",
    "shortcodes": [
        ":woman_factory_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍💼",
    "emoticons": [],
    "keywords": [
        "` + _lt("business man") + `",
        "` + _lt("man office worker") + `",
        "` + _lt("manager") + `",
        "` + _lt("office worker") + `",
        "` + _lt("white collar") + `",
        "` + _lt("architect") + `",
        "` + _lt("business") + `",
        "` + _lt("man") + `",
        "` + _lt("white-collar") + `"
    ],
    "name": "` + _lt("man office worker") + `",
    "shortcodes": [
        ":man_office_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍💼",
    "emoticons": [],
    "keywords": [
        "` + _lt("business woman") + `",
        "` + _lt("manager") + `",
        "` + _lt("office worker") + `",
        "` + _lt("white collar") + `",
        "` + _lt("woman office worker") + `",
        "` + _lt("architect") + `",
        "` + _lt("business") + `",
        "` + _lt("white-collar") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman office worker") + `",
    "shortcodes": [
        ":woman_office_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🔬",
    "emoticons": [],
    "keywords": [
        "` + _lt("biologist") + `",
        "` + _lt("chemist") + `",
        "` + _lt("engineer") + `",
        "` + _lt("man") + `",
        "` + _lt("physicist") + `",
        "` + _lt("scientist") + `"
    ],
    "name": "` + _lt("man scientist") + `",
    "shortcodes": [
        ":man_scientist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🔬",
    "emoticons": [],
    "keywords": [
        "` + _lt("biologist") + `",
        "` + _lt("chemist") + `",
        "` + _lt("engineer") + `",
        "` + _lt("physicist") + `",
        "` + _lt("scientist") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman scientist") + `",
    "shortcodes": [
        ":woman_scientist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍💻",
    "emoticons": [],
    "keywords": [
        "` + _lt("coder") + `",
        "` + _lt("developer") + `",
        "` + _lt("inventor") + `",
        "` + _lt("man") + `",
        "` + _lt("software") + `",
        "` + _lt("technologist") + `"
    ],
    "name": "` + _lt("man technologist") + `",
    "shortcodes": [
        ":man_ltechnologist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍💻",
    "emoticons": [],
    "keywords": [
        "` + _lt("coder") + `",
        "` + _lt("developer") + `",
        "` + _lt("inventor") + `",
        "` + _lt("software") + `",
        "` + _lt("technologist") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman technologist") + `",
    "shortcodes": [
        ":woman_ltechnologist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🎤",
    "emoticons": [],
    "keywords": [
        "` + _lt("entertainer") + `",
        "` + _lt("man") + `",
        "` + _lt("man singer") + `",
        "` + _lt("performer") + `",
        "` + _lt("rock singer") + `",
        "` + _lt("star") + `",
        "` + _lt("actor") + `",
        "` + _lt("rock") + `",
        "` + _lt("singer") + `"
    ],
    "name": "` + _lt("man singer") + `",
    "shortcodes": [
        ":man_singer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🎤",
    "emoticons": [],
    "keywords": [
        "` + _lt("entertainer") + `",
        "` + _lt("performer") + `",
        "` + _lt("rock singer") + `",
        "` + _lt("star") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman singer") + `",
        "` + _lt("actor") + `",
        "` + _lt("rock") + `",
        "` + _lt("singer") + `"
    ],
    "name": "` + _lt("woman singer") + `",
    "shortcodes": [
        ":woman_singer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🎨",
    "emoticons": [],
    "keywords": [
        "` + _lt("artist") + `",
        "` + _lt("man") + `",
        "` + _lt("painter") + `",
        "` + _lt("palette") + `"
    ],
    "name": "` + _lt("man artist") + `",
    "shortcodes": [
        ":man_artist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🎨",
    "emoticons": [],
    "keywords": [
        "` + _lt("artist") + `",
        "` + _lt("painter") + `",
        "` + _lt("palette") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman artist") + `",
    "shortcodes": [
        ":woman_artist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍✈️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man") + `",
        "` + _lt("pilot") + `",
        "` + _lt("plane") + `"
    ],
    "name": "` + _lt("man pilot") + `",
    "shortcodes": [
        ":man_pilot:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍✈️",
    "emoticons": [],
    "keywords": [
        "` + _lt("pilot") + `",
        "` + _lt("plane") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman pilot") + `",
    "shortcodes": [
        ":woman_pilot:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🚀",
    "emoticons": [],
    "keywords": [
        "` + _lt("astronaut") + `",
        "` + _lt("man") + `",
        "` + _lt("rocket") + `"
    ],
    "name": "` + _lt("man astronaut") + `",
    "shortcodes": [
        ":man_astronaut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🚀",
    "emoticons": [],
    "keywords": [
        "` + _lt("astronaut") + `",
        "` + _lt("rocket") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman astronaut") + `",
    "shortcodes": [
        ":woman_astronaut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🚒",
    "emoticons": [],
    "keywords": [
        "` + _lt("fire truck") + `",
        "` + _lt("firefighter") + `",
        "` + _lt("man") + `",
        "` + _lt("firetruck") + `",
        "` + _lt("fireman") + `"
    ],
    "name": "` + _lt("man firefighter") + `",
    "shortcodes": [
        ":man_firefighter:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🚒",
    "emoticons": [],
    "keywords": [
        "` + _lt("fire truck") + `",
        "` + _lt("firefighter") + `",
        "` + _lt("woman") + `",
        "` + _lt("firetruck") + `",
        "` + _lt("engine") + `",
        "` + _lt("fire") + `",
        "` + _lt("firewoman") + `",
        "` + _lt("truck") + `"
    ],
    "name": "` + _lt("woman firefighter") + `",
    "shortcodes": [
        ":woman_firefighter:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👮",
    "emoticons": [],
    "keywords": [
        "` + _lt("cop") + `",
        "` + _lt("officer") + `",
        "` + _lt("police") + `"
    ],
    "name": "` + _lt("police officer") + `",
    "shortcodes": [
        ":police_officer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👮‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cop") + `",
        "` + _lt("man") + `",
        "` + _lt("officer") + `",
        "` + _lt("police") + `"
    ],
    "name": "` + _lt("man police officer") + `",
    "shortcodes": [
        ":man_police_officer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👮‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cop") + `",
        "` + _lt("officer") + `",
        "` + _lt("police") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman police officer") + `",
    "shortcodes": [
        ":woman_police_officer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕵️",
    "emoticons": [],
    "keywords": [
        "` + _lt("detective") + `",
        "` + _lt("investigator") + `",
        "` + _lt("sleuth") + `",
        "` + _lt("spy") + `"
    ],
    "name": "` + _lt("detective") + `",
    "shortcodes": [
        ":detective:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕵️‍♂️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("man detective") + `",
    "shortcodes": [
        ":man_detective:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕵️‍♀️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("woman detective") + `",
    "shortcodes": [
        ":woman_detective:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💂",
    "emoticons": [],
    "keywords": [
        "` + _lt("guard") + `"
    ],
    "name": "` + _lt("guard") + `",
    "shortcodes": [
        ":guard:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💂‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("guard") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("man guard") + `",
    "shortcodes": [
        ":man_guard:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💂‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("guard") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman guard") + `",
    "shortcodes": [
        ":woman_guard:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👷",
    "emoticons": [],
    "keywords": [
        "` + _lt("construction") + `",
        "` + _lt("hat") + `",
        "` + _lt("worker") + `"
    ],
    "name": "` + _lt("construction worker") + `",
    "shortcodes": [
        ":construction_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👷‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("construction") + `",
        "` + _lt("man") + `",
        "` + _lt("worker") + `"
    ],
    "name": "` + _lt("man construction worker") + `",
    "shortcodes": [
        ":man_construction_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👷‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("construction") + `",
        "` + _lt("woman") + `",
        "` + _lt("worker") + `"
    ],
    "name": "` + _lt("woman construction worker") + `",
    "shortcodes": [
        ":woman_construction_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤴",
    "emoticons": [],
    "keywords": [
        "` + _lt("prince") + `"
    ],
    "name": "` + _lt("prince") + `",
    "shortcodes": [
        ":prince:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👸",
    "emoticons": [],
    "keywords": [
        "` + _lt("fairy tale") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("princess") + `"
    ],
    "name": "` + _lt("princess") + `",
    "shortcodes": [
        ":princess:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👳",
    "emoticons": [
        ":turban"
    ],
    "keywords": [
        "` + _lt("person wearing turban") + `",
        "` + _lt("turban") + `"
    ],
    "name": "` + _lt("person wearing turban") + `",
    "shortcodes": [
        ":person_wearing_lturban:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👳‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man") + `",
        "` + _lt("man wearing turban") + `",
        "` + _lt("turban") + `"
    ],
    "name": "` + _lt("man wearing turban") + `",
    "shortcodes": [
        ":man_wearing_lturban:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👳‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("turban") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman wearing turban") + `"
    ],
    "name": "` + _lt("woman wearing turban") + `",
    "shortcodes": [
        ":woman_wearing_lturban:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👲",
    "emoticons": [],
    "keywords": [
        "` + _lt("cap") + `",
        "` + _lt("gua pi mao") + `",
        "` + _lt("hat") + `",
        "` + _lt("person") + `",
        "` + _lt("person with skullcap") + `",
        "` + _lt("skullcap") + `"
    ],
    "name": "` + _lt("person with skullcap") + `",
    "shortcodes": [
        ":person_with_skullcap:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧕",
    "emoticons": [],
    "keywords": [
        "` + _lt("headscarf") + `",
        "` + _lt("hijab") + `",
        "` + _lt("mantilla") + `",
        "` + _lt("tichel") + `",
        "` + _lt("woman with headscarf") + `"
    ],
    "name": "` + _lt("woman with headscarf") + `",
    "shortcodes": [
        ":woman_with_headscarf:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤵",
    "emoticons": [],
    "keywords": [
        "` + _lt("groom") + `",
        "` + _lt("person") + `",
        "` + _lt("person in tux") + `",
        "` + _lt("person in tuxedo") + `",
        "` + _lt("tuxedo") + `"
    ],
    "name": "` + _lt("person in tuxedo") + `",
    "shortcodes": [
        ":person_in_ltuxedo:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👰",
    "emoticons": [],
    "keywords": [
        "` + _lt("bride") + `",
        "` + _lt("person") + `",
        "` + _lt("person with veil") + `",
        "` + _lt("veil") + `",
        "` + _lt("wedding") + `"
    ],
    "name": "` + _lt("person with veil") + `",
    "shortcodes": [
        ":person_with_veil:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤰",
    "emoticons": [],
    "keywords": [
        "` + _lt("pregnant") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("pregnant woman") + `",
    "shortcodes": [
        ":pregnant_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤱",
    "emoticons": [],
    "keywords": [
        "` + _lt("baby") + `",
        "` + _lt("breast") + `",
        "` + _lt("breast-feeding") + `",
        "` + _lt("nursing") + `"
    ],
    "name": "` + _lt("breast-feeding") + `",
    "shortcodes": [
        ":breast-feeding:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👼",
    "emoticons": [],
    "keywords": [
        "` + _lt("angel") + `",
        "` + _lt("baby") + `",
        "` + _lt("face") + `",
        "` + _lt("fairy tale") + `",
        "` + _lt("fantasy") + `"
    ],
    "name": "` + _lt("baby angel") + `",
    "shortcodes": [
        ":baby_angel:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🎅",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("Christmas") + `",
        "` + _lt("Father Christmas") + `",
        "` + _lt("Santa") + `",
        "` + _lt("Santa Claus") + `",
        "` + _lt("claus") + `",
        "` + _lt("father") + `",
        "` + _lt("santa") + `",
        "` + _lt("Claus") + `",
        "` + _lt("Father") + `"
    ],
    "name": "` + _lt("Santa Claus") + `",
    "shortcodes": [
        ":Santa_Claus:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤶",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("Christmas") + `",
        "` + _lt("Mrs Claus") + `",
        "` + _lt("Mrs Santa Claus") + `",
        "` + _lt("Mrs. Claus") + `",
        "` + _lt("claus") + `",
        "` + _lt("mother") + `",
        "` + _lt("Mrs.") + `",
        "` + _lt("Claus") + `",
        "` + _lt("Mother") + `"
    ],
    "name": "` + _lt("Mrs. Claus") + `",
    "shortcodes": [
        ":Mrs._Claus:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦸",
    "emoticons": [],
    "keywords": [
        "` + _lt("good") + `",
        "` + _lt("hero") + `",
        "` + _lt("heroine") + `",
        "` + _lt("superhero") + `",
        "` + _lt("superpower") + `"
    ],
    "name": "` + _lt("superhero") + `",
    "shortcodes": [
        ":superhero:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦸‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("good") + `",
        "` + _lt("hero") + `",
        "` + _lt("man") + `",
        "` + _lt("man superhero") + `",
        "` + _lt("superpower") + `"
    ],
    "name": "` + _lt("man superhero") + `",
    "shortcodes": [
        ":man_superhero:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦸‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("good") + `",
        "` + _lt("hero") + `",
        "` + _lt("heroine") + `",
        "` + _lt("superpower") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman superhero") + `"
    ],
    "name": "` + _lt("woman superhero") + `",
    "shortcodes": [
        ":woman_superhero:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦹",
    "emoticons": [],
    "keywords": [
        "` + _lt("criminal") + `",
        "` + _lt("evil") + `",
        "` + _lt("superpower") + `",
        "` + _lt("supervillain") + `",
        "` + _lt("villain") + `"
    ],
    "name": "` + _lt("supervillain") + `",
    "shortcodes": [
        ":supervillain:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦹‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("criminal") + `",
        "` + _lt("evil") + `",
        "` + _lt("man") + `",
        "` + _lt("man supervillain") + `",
        "` + _lt("superpower") + `",
        "` + _lt("villain") + `"
    ],
    "name": "` + _lt("man supervillain") + `",
    "shortcodes": [
        ":man_supervillain:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦹‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("criminal") + `",
        "` + _lt("evil") + `",
        "` + _lt("superpower") + `",
        "` + _lt("villain") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman supervillain") + `"
    ],
    "name": "` + _lt("woman supervillain") + `",
    "shortcodes": [
        ":woman_supervillain:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧙",
    "emoticons": [],
    "keywords": [
        "` + _lt("mage") + `",
        "` + _lt("sorcerer") + `",
        "` + _lt("sorceress") + `",
        "` + _lt("witch") + `",
        "` + _lt("wizard") + `"
    ],
    "name": "` + _lt("mage") + `",
    "shortcodes": [
        ":mage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧙‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man mage") + `",
        "` + _lt("sorcerer") + `",
        "` + _lt("wizard") + `"
    ],
    "name": "` + _lt("man mage") + `",
    "shortcodes": [
        ":man_mage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧙‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("sorceress") + `",
        "` + _lt("witch") + `",
        "` + _lt("woman mage") + `"
    ],
    "name": "` + _lt("woman mage") + `",
    "shortcodes": [
        ":woman_mage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧚",
    "emoticons": [],
    "keywords": [
        "` + _lt("fairy") + `",
        "` + _lt("Oberon") + `",
        "` + _lt("Puck") + `",
        "` + _lt("Titania") + `"
    ],
    "name": "` + _lt("fairy") + `",
    "shortcodes": [
        ":fairy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧚‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man fairy") + `",
        "` + _lt("Oberon") + `",
        "` + _lt("Puck") + `"
    ],
    "name": "` + _lt("man fairy") + `",
    "shortcodes": [
        ":man_fairy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧚‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("Titania") + `",
        "` + _lt("woman fairy") + `"
    ],
    "name": "` + _lt("woman fairy") + `",
    "shortcodes": [
        ":woman_fairy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧛",
    "emoticons": [],
    "keywords": [
        "` + _lt("Dracula") + `",
        "` + _lt("undead") + `",
        "` + _lt("vampire") + `"
    ],
    "name": "` + _lt("vampire") + `",
    "shortcodes": [
        ":vampire:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧛‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("Dracula") + `",
        "` + _lt("man vampire") + `",
        "` + _lt("undead") + `"
    ],
    "name": "` + _lt("man vampire") + `",
    "shortcodes": [
        ":man_vampire:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧛‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("undead") + `",
        "` + _lt("woman vampire") + `"
    ],
    "name": "` + _lt("woman vampire") + `",
    "shortcodes": [
        ":woman_vampire:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧜",
    "emoticons": [],
    "keywords": [
        "` + _lt("mermaid") + `",
        "` + _lt("merman") + `",
        "` + _lt("merperson") + `",
        "` + _lt("merwoman") + `"
    ],
    "name": "` + _lt("merperson") + `",
    "shortcodes": [
        ":merperson:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧜‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("merman") + `",
        "` + _lt("Triton") + `"
    ],
    "name": "` + _lt("merman") + `",
    "shortcodes": [
        ":merman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧜‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("mermaid") + `",
        "` + _lt("merwoman") + `"
    ],
    "name": "` + _lt("mermaid") + `",
    "shortcodes": [
        ":mermaid:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧝",
    "emoticons": [],
    "keywords": [
        "` + _lt("elf") + `",
        "` + _lt("magical") + `"
    ],
    "name": "` + _lt("elf") + `",
    "shortcodes": [
        ":elf:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧝‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("magical") + `",
        "` + _lt("man elf") + `"
    ],
    "name": "` + _lt("man elf") + `",
    "shortcodes": [
        ":man_elf:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧝‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("magical") + `",
        "` + _lt("woman elf") + `"
    ],
    "name": "` + _lt("woman elf") + `",
    "shortcodes": [
        ":woman_elf:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧞",
    "emoticons": [],
    "keywords": [
        "` + _lt("djinn") + `",
        "` + _lt("genie") + `"
    ],
    "name": "` + _lt("genie") + `",
    "shortcodes": [
        ":genie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧞‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("djinn") + `",
        "` + _lt("man genie") + `"
    ],
    "name": "` + _lt("man genie") + `",
    "shortcodes": [
        ":man_genie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧞‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("djinn") + `",
        "` + _lt("woman genie") + `"
    ],
    "name": "` + _lt("woman genie") + `",
    "shortcodes": [
        ":woman_genie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧟",
    "emoticons": [],
    "keywords": [
        "` + _lt("undead") + `",
        "` + _lt("walking dead") + `",
        "` + _lt("zombie") + `"
    ],
    "name": "` + _lt("zombie") + `",
    "shortcodes": [
        ":zombie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧟‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man zombie") + `",
        "` + _lt("undead") + `",
        "` + _lt("walking dead") + `"
    ],
    "name": "` + _lt("man zombie") + `",
    "shortcodes": [
        ":man_zombie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧟‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("undead") + `",
        "` + _lt("walking dead") + `",
        "` + _lt("woman zombie") + `"
    ],
    "name": "` + _lt("woman zombie") + `",
    "shortcodes": [
        ":woman_zombie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💆",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("massage") + `",
        "` + _lt("person getting massage") + `",
        "` + _lt("salon") + `"
    ],
    "name": "` + _lt("person getting massage") + `",
    "shortcodes": [
        ":person_getting_massage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💆‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("man") + `",
        "` + _lt("man getting massage") + `",
        "` + _lt("massage") + `"
    ],
    "name": "` + _lt("man getting massage") + `",
    "shortcodes": [
        ":man_getting_massage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💆‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("massage") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman getting massage") + `"
    ],
    "name": "` + _lt("woman getting massage") + `",
    "shortcodes": [
        ":woman_getting_massage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💇",
    "emoticons": [],
    "keywords": [
        "` + _lt("barber") + `",
        "` + _lt("beauty") + `",
        "` + _lt("haircut") + `",
        "` + _lt("parlor") + `",
        "` + _lt("person getting haircut") + `",
        "` + _lt("parlour") + `"
    ],
    "name": "` + _lt("person getting haircut") + `",
    "shortcodes": [
        ":person_getting_haircut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💇‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("haircut") + `",
        "` + _lt("hairdresser") + `",
        "` + _lt("man") + `",
        "` + _lt("man getting haircut") + `"
    ],
    "name": "` + _lt("man getting haircut") + `",
    "shortcodes": [
        ":man_getting_haircut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💇‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("haircut") + `",
        "` + _lt("hairdresser") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman getting haircut") + `"
    ],
    "name": "` + _lt("woman getting haircut") + `",
    "shortcodes": [
        ":woman_getting_haircut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚶",
    "emoticons": [],
    "keywords": [
        "` + _lt("hike") + `",
        "` + _lt("person walking") + `",
        "` + _lt("walk") + `",
        "` + _lt("walking") + `"
    ],
    "name": "` + _lt("person walking") + `",
    "shortcodes": [
        ":person_walking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚶‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("hike") + `",
        "` + _lt("man") + `",
        "` + _lt("man walking") + `",
        "` + _lt("walk") + `"
    ],
    "name": "` + _lt("man walking") + `",
    "shortcodes": [
        ":man_walking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚶‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("hike") + `",
        "` + _lt("walk") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman walking") + `"
    ],
    "name": "` + _lt("woman walking") + `",
    "shortcodes": [
        ":woman_walking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧍",
    "emoticons": [],
    "keywords": [
        "` + _lt("person standing") + `",
        "` + _lt("stand") + `",
        "` + _lt("standing") + `"
    ],
    "name": "` + _lt("person standing") + `",
    "shortcodes": [
        ":person_standing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧍‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man") + `",
        "` + _lt("standing") + `"
    ],
    "name": "` + _lt("man standing") + `",
    "shortcodes": [
        ":man_standing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧍‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("standing") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman standing") + `",
    "shortcodes": [
        ":woman_standing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧎",
    "emoticons": [],
    "keywords": [
        "` + _lt("kneel") + `",
        "` + _lt("kneeling") + `",
        "` + _lt("person kneeling") + `"
    ],
    "name": "` + _lt("person kneeling") + `",
    "shortcodes": [
        ":person_kneeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧎‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("kneeling") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("man kneeling") + `",
    "shortcodes": [
        ":man_kneeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧎‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("kneeling") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman kneeling") + `",
    "shortcodes": [
        ":woman_kneeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦯",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("blind") + `",
        "` + _lt("man") + `",
        "` + _lt("man with white cane") + `",
        "` + _lt("man with guide cane") + `"
    ],
    "name": "` + _lt("man with white cane") + `",
    "shortcodes": [
        ":man_with_white_cane:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦯",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("blind") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman with white cane") + `",
        "` + _lt("woman with guide cane") + `"
    ],
    "name": "` + _lt("woman with white cane") + `",
    "shortcodes": [
        ":woman_with_white_cane:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦼",
    "emoticons": [],
    "keywords": [
        "` + _lt("man in motorised wheelchair") + `",
        "` + _lt("accessibility") + `",
        "` + _lt("man") + `",
        "` + _lt("man in motorized wheelchair") + `",
        "` + _lt("wheelchair") + `",
        "` + _lt("man in powered wheelchair") + `"
    ],
    "name": "` + _lt("man in motorized wheelchair") + `",
    "shortcodes": [
        ":man_in_motorized_wheelchair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦼",
    "emoticons": [],
    "keywords": [
        "` + _lt("woman in motorised wheelchair") + `",
        "` + _lt("accessibility") + `",
        "` + _lt("wheelchair") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman in motorized wheelchair") + `",
        "` + _lt("woman in powered wheelchair") + `"
    ],
    "name": "` + _lt("woman in motorized wheelchair") + `",
    "shortcodes": [
        ":woman_in_motorized_wheelchair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦽",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("man") + `",
        "` + _lt("man in manual wheelchair") + `",
        "` + _lt("wheelchair") + `"
    ],
    "name": "` + _lt("man in manual wheelchair") + `",
    "shortcodes": [
        ":man_in_manual_wheelchair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦽",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("wheelchair") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman in manual wheelchair") + `"
    ],
    "name": "` + _lt("woman in manual wheelchair") + `",
    "shortcodes": [
        ":woman_in_manual_wheelchair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏃",
    "emoticons": [
        ":run"
    ],
    "keywords": [
        "` + _lt("marathon") + `",
        "` + _lt("person running") + `",
        "` + _lt("running") + `"
    ],
    "name": "` + _lt("person running") + `",
    "shortcodes": [
        ":person_running:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏃‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man") + `",
        "` + _lt("marathon") + `",
        "` + _lt("racing") + `",
        "` + _lt("running") + `"
    ],
    "name": "` + _lt("man running") + `",
    "shortcodes": [
        ":man_running:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏃‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("marathon") + `",
        "` + _lt("racing") + `",
        "` + _lt("running") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman running") + `",
    "shortcodes": [
        ":woman_running:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💃",
    "emoticons": [],
    "keywords": [
        "` + _lt("dance") + `",
        "` + _lt("dancing") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman dancing") + `",
    "shortcodes": [
        ":woman_dancing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕺",
    "emoticons": [],
    "keywords": [
        "` + _lt("dance") + `",
        "` + _lt("dancing") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("man dancing") + `",
    "shortcodes": [
        ":man_dancing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕴️",
    "emoticons": [],
    "keywords": [
        "` + _lt("business") + `",
        "` + _lt("person") + `",
        "` + _lt("person in suit levitating") + `",
        "` + _lt("suit") + `"
    ],
    "name": "` + _lt("person in suit levitating") + `",
    "shortcodes": [
        ":person_in_suit_levitating:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👯",
    "emoticons": [],
    "keywords": [
        "` + _lt("bunny ear") + `",
        "` + _lt("dancer") + `",
        "` + _lt("partying") + `",
        "` + _lt("people with bunny ears") + `"
    ],
    "name": "` + _lt("people with bunny ears") + `",
    "shortcodes": [
        ":people_with_bunny_ears:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👯‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bunny ear") + `",
        "` + _lt("dancer") + `",
        "` + _lt("men") + `",
        "` + _lt("men with bunny ears") + `",
        "` + _lt("partying") + `"
    ],
    "name": "` + _lt("men with bunny ears") + `",
    "shortcodes": [
        ":men_with_bunny_ears:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👯‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bunny ear") + `",
        "` + _lt("dancer") + `",
        "` + _lt("partying") + `",
        "` + _lt("women") + `",
        "` + _lt("women with bunny ears") + `"
    ],
    "name": "` + _lt("women with bunny ears") + `",
    "shortcodes": [
        ":women_with_bunny_ears:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧖",
    "emoticons": [],
    "keywords": [
        "` + _lt("person in steamy room") + `",
        "` + _lt("sauna") + `",
        "` + _lt("steam room") + `"
    ],
    "name": "` + _lt("person in steamy room") + `",
    "shortcodes": [
        ":person_in_steamy_room:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧖‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man in steam room") + `",
        "` + _lt("man in steamy room") + `",
        "` + _lt("sauna") + `",
        "` + _lt("steam room") + `"
    ],
    "name": "` + _lt("man in steamy room") + `",
    "shortcodes": [
        ":man_in_steamy_room:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧖‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("sauna") + `",
        "` + _lt("steam room") + `",
        "` + _lt("woman in steam room") + `",
        "` + _lt("woman in steamy room") + `"
    ],
    "name": "` + _lt("woman in steamy room") + `",
    "shortcodes": [
        ":woman_in_steamy_room:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧗",
    "emoticons": [],
    "keywords": [
        "` + _lt("climber") + `",
        "` + _lt("person climbing") + `"
    ],
    "name": "` + _lt("person climbing") + `",
    "shortcodes": [
        ":person_climbing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧗‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("climber") + `",
        "` + _lt("man climbing") + `"
    ],
    "name": "` + _lt("man climbing") + `",
    "shortcodes": [
        ":man_climbing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧗‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("climber") + `",
        "` + _lt("woman climbing") + `"
    ],
    "name": "` + _lt("woman climbing") + `",
    "shortcodes": [
        ":woman_climbing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤺",
    "emoticons": [],
    "keywords": [
        "` + _lt("fencer") + `",
        "` + _lt("fencing") + `",
        "` + _lt("person fencing") + `",
        "` + _lt("sword") + `"
    ],
    "name": "` + _lt("person fencing") + `",
    "shortcodes": [
        ":person_fencing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏇",
    "emoticons": [],
    "keywords": [
        "` + _lt("horse") + `",
        "` + _lt("jockey") + `",
        "` + _lt("racehorse") + `",
        "` + _lt("racing") + `"
    ],
    "name": "` + _lt("horse racing") + `",
    "shortcodes": [
        ":horse_racing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "⛷️",
    "emoticons": [],
    "keywords": [
        "` + _lt("ski") + `",
        "` + _lt("skier") + `",
        "` + _lt("snow") + `"
    ],
    "name": "` + _lt("skier") + `",
    "shortcodes": [
        ":skier:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏂",
    "emoticons": [],
    "keywords": [
        "` + _lt("ski") + `",
        "` + _lt("snow") + `",
        "` + _lt("snowboard") + `",
        "` + _lt("snowboarder") + `"
    ],
    "name": "` + _lt("snowboarder") + `",
    "shortcodes": [
        ":snowboarder:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏌️",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("golf") + `",
        "` + _lt("golfer") + `",
        "` + _lt("person golfing") + `"
    ],
    "name": "` + _lt("person golfing") + `",
    "shortcodes": [
        ":person_golfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏌️‍♂️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("man golfing") + `",
    "shortcodes": [
        ":man_golfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏌️‍♀️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("woman golfing") + `",
    "shortcodes": [
        ":woman_golfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏄",
    "emoticons": [],
    "keywords": [
        "` + _lt("person surfing") + `",
        "` + _lt("surfer") + `",
        "` + _lt("surfing") + `"
    ],
    "name": "` + _lt("person surfing") + `",
    "shortcodes": [
        ":person_surfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏄‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man") + `",
        "` + _lt("surfer") + `",
        "` + _lt("surfing") + `"
    ],
    "name": "` + _lt("man surfing") + `",
    "shortcodes": [
        ":man_surfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏄‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("surfer") + `",
        "` + _lt("surfing") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman surfing") + `",
    "shortcodes": [
        ":woman_surfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚣",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("person") + `",
        "` + _lt("person rowing boat") + `",
        "` + _lt("rowboat") + `"
    ],
    "name": "` + _lt("person rowing boat") + `",
    "shortcodes": [
        ":person_rowing_boat:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚣‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("man") + `",
        "` + _lt("man rowing boat") + `",
        "` + _lt("rowboat") + `"
    ],
    "name": "` + _lt("man rowing boat") + `",
    "shortcodes": [
        ":man_rowing_boat:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚣‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("rowboat") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman rowing boat") + `"
    ],
    "name": "` + _lt("woman rowing boat") + `",
    "shortcodes": [
        ":woman_rowing_boat:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏊",
    "emoticons": [],
    "keywords": [
        "` + _lt("person swimming") + `",
        "` + _lt("swim") + `",
        "` + _lt("swimmer") + `"
    ],
    "name": "` + _lt("person swimming") + `",
    "shortcodes": [
        ":person_swimming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏊‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man") + `",
        "` + _lt("man swimming") + `",
        "` + _lt("swim") + `",
        "` + _lt("swimmer") + `"
    ],
    "name": "` + _lt("man swimming") + `",
    "shortcodes": [
        ":man_swimming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏊‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("swim") + `",
        "` + _lt("swimmer") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman swimming") + `"
    ],
    "name": "` + _lt("woman swimming") + `",
    "shortcodes": [
        ":woman_swimming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "⛹️",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("person bouncing ball") + `"
    ],
    "name": "` + _lt("person bouncing ball") + `",
    "shortcodes": [
        ":person_bouncing_ball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "⛹️‍♂️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("man bouncing ball") + `",
    "shortcodes": [
        ":man_bouncing_ball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "⛹️‍♀️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("woman bouncing ball") + `",
    "shortcodes": [
        ":woman_bouncing_ball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏋️",
    "emoticons": [],
    "keywords": [
        "` + _lt("lifter") + `",
        "` + _lt("person lifting weights") + `",
        "` + _lt("weight") + `",
        "` + _lt("weightlifter") + `"
    ],
    "name": "` + _lt("person lifting weights") + `",
    "shortcodes": [
        ":person_lifting_weights:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏋️‍♂️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("man lifting weights") + `",
    "shortcodes": [
        ":man_lifting_weights:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏋️‍♀️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _lt("woman lifting weights") + `",
    "shortcodes": [
        ":woman_lifting_weights:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚴",
    "emoticons": [],
    "keywords": [
        "` + _lt("bicycle") + `",
        "` + _lt("biking") + `",
        "` + _lt("cyclist") + `",
        "` + _lt("person biking") + `",
        "` + _lt("person riding a bike") + `"
    ],
    "name": "` + _lt("person biking") + `",
    "shortcodes": [
        ":person_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚴‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bicycle") + `",
        "` + _lt("biking") + `",
        "` + _lt("cyclist") + `",
        "` + _lt("man") + `",
        "` + _lt("man riding a bike") + `"
    ],
    "name": "` + _lt("man biking") + `",
    "shortcodes": [
        ":man_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚴‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bicycle") + `",
        "` + _lt("biking") + `",
        "` + _lt("cyclist") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman riding a bike") + `"
    ],
    "name": "` + _lt("woman biking") + `",
    "shortcodes": [
        ":woman_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚵",
    "emoticons": [],
    "keywords": [
        "` + _lt("bicycle") + `",
        "` + _lt("bicyclist") + `",
        "` + _lt("bike") + `",
        "` + _lt("cyclist") + `",
        "` + _lt("mountain") + `",
        "` + _lt("person mountain biking") + `"
    ],
    "name": "` + _lt("person mountain biking") + `",
    "shortcodes": [
        ":person_mountain_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚵‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bicycle") + `",
        "` + _lt("bike") + `",
        "` + _lt("cyclist") + `",
        "` + _lt("man") + `",
        "` + _lt("man mountain biking") + `",
        "` + _lt("mountain") + `"
    ],
    "name": "` + _lt("man mountain biking") + `",
    "shortcodes": [
        ":man_mountain_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚵‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bicycle") + `",
        "` + _lt("bike") + `",
        "` + _lt("biking") + `",
        "` + _lt("cyclist") + `",
        "` + _lt("mountain") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("woman mountain biking") + `",
    "shortcodes": [
        ":woman_mountain_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤸",
    "emoticons": [],
    "keywords": [
        "` + _lt("cartwheel") + `",
        "` + _lt("gymnastics") + `",
        "` + _lt("person cartwheeling") + `"
    ],
    "name": "` + _lt("person cartwheeling") + `",
    "shortcodes": [
        ":person_cartwheeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤸‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cartwheel") + `",
        "` + _lt("gymnastics") + `",
        "` + _lt("man") + `",
        "` + _lt("man cartwheeling") + `"
    ],
    "name": "` + _lt("man cartwheeling") + `",
    "shortcodes": [
        ":man_cartwheeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤸‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cartwheel") + `",
        "` + _lt("gymnastics") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman cartwheeling") + `"
    ],
    "name": "` + _lt("woman cartwheeling") + `",
    "shortcodes": [
        ":woman_cartwheeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤼",
    "emoticons": [],
    "keywords": [
        "` + _lt("people wrestling") + `",
        "` + _lt("wrestle") + `",
        "` + _lt("wrestler") + `"
    ],
    "name": "` + _lt("people wrestling") + `",
    "shortcodes": [
        ":people_wrestling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤼‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("men") + `",
        "` + _lt("men wrestling") + `",
        "` + _lt("wrestle") + `"
    ],
    "name": "` + _lt("men wrestling") + `",
    "shortcodes": [
        ":men_wrestling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤼‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("women") + `",
        "` + _lt("women wrestling") + `",
        "` + _lt("wrestle") + `"
    ],
    "name": "` + _lt("women wrestling") + `",
    "shortcodes": [
        ":women_wrestling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤽",
    "emoticons": [],
    "keywords": [
        "` + _lt("person playing water polo") + `",
        "` + _lt("polo") + `",
        "` + _lt("water") + `"
    ],
    "name": "` + _lt("person playing water polo") + `",
    "shortcodes": [
        ":person_playing_water_polo:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤽‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man") + `",
        "` + _lt("man playing water polo") + `",
        "` + _lt("water polo") + `"
    ],
    "name": "` + _lt("man playing water polo") + `",
    "shortcodes": [
        ":man_playing_water_polo:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤽‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("water polo") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman playing water polo") + `"
    ],
    "name": "` + _lt("woman playing water polo") + `",
    "shortcodes": [
        ":woman_playing_water_polo:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤾",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("handball") + `",
        "` + _lt("person playing handball") + `"
    ],
    "name": "` + _lt("person playing handball") + `",
    "shortcodes": [
        ":person_playing_handball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤾‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("handball") + `",
        "` + _lt("man") + `",
        "` + _lt("man playing handball") + `"
    ],
    "name": "` + _lt("man playing handball") + `",
    "shortcodes": [
        ":man_playing_handball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤾‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("handball") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman playing handball") + `"
    ],
    "name": "` + _lt("woman playing handball") + `",
    "shortcodes": [
        ":woman_playing_handball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤹",
    "emoticons": [],
    "keywords": [
        "` + _lt("balance") + `",
        "` + _lt("juggle") + `",
        "` + _lt("multi-task") + `",
        "` + _lt("person juggling") + `",
        "` + _lt("skill") + `",
        "` + _lt("multitask") + `"
    ],
    "name": "` + _lt("person juggling") + `",
    "shortcodes": [
        ":person_juggling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤹‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("juggling") + `",
        "` + _lt("man") + `",
        "` + _lt("multi-task") + `",
        "` + _lt("multitask") + `"
    ],
    "name": "` + _lt("man juggling") + `",
    "shortcodes": [
        ":man_juggling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤹‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("juggling") + `",
        "` + _lt("multi-task") + `",
        "` + _lt("woman") + `",
        "` + _lt("multitask") + `"
    ],
    "name": "` + _lt("woman juggling") + `",
    "shortcodes": [
        ":woman_juggling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧘",
    "emoticons": [],
    "keywords": [
        "` + _lt("meditation") + `",
        "` + _lt("person in lotus position") + `",
        "` + _lt("yoga") + `"
    ],
    "name": "` + _lt("person in lotus position") + `",
    "shortcodes": [
        ":person_in_lotus_position:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧘‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("man in lotus position") + `",
        "` + _lt("meditation") + `",
        "` + _lt("yoga") + `"
    ],
    "name": "` + _lt("man in lotus position") + `",
    "shortcodes": [
        ":man_in_lotus_position:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧘‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("meditation") + `",
        "` + _lt("woman in lotus position") + `",
        "` + _lt("yoga") + `"
    ],
    "name": "` + _lt("woman in lotus position") + `",
    "shortcodes": [
        ":woman_in_lotus_position:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🛀",
    "emoticons": [],
    "keywords": [
        "` + _lt("bath") + `",
        "` + _lt("bathtub") + `",
        "` + _lt("person taking bath") + `",
        "` + _lt("tub") + `"
    ],
    "name": "` + _lt("person taking bath") + `",
    "shortcodes": [
        ":person_ltaking_bath:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🛌",
    "emoticons": [],
    "keywords": [
        "` + _lt("hotel") + `",
        "` + _lt("person in bed") + `",
        "` + _lt("sleep") + `",
        "` + _lt("sleeping") + `",
        "` + _lt("good night") + `"
    ],
    "name": "` + _lt("person in bed") + `",
    "shortcodes": [
        ":person_in_bed:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧑‍🤝‍🧑",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("hand") + `",
        "` + _lt("hold") + `",
        "` + _lt("holding hands") + `",
        "` + _lt("people holding hands") + `",
        "` + _lt("person") + `"
    ],
    "name": "` + _lt("people holding hands") + `",
    "shortcodes": [
        ":people_holding_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👭",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("hand") + `",
        "` + _lt("holding hands") + `",
        "` + _lt("women") + `",
        "` + _lt("women holding hands") + `",
        "` + _lt("two women holding hands") + `"
    ],
    "name": "` + _lt("women holding hands") + `",
    "shortcodes": [
        ":women_holding_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👫",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("hand") + `",
        "` + _lt("hold") + `",
        "` + _lt("holding hands") + `",
        "` + _lt("man") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman and man holding hands") + `",
        "` + _lt("man and woman holding hands") + `"
    ],
    "name": "` + _lt("woman and man holding hands") + `",
    "shortcodes": [
        ":woman_and_man_holding_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👬",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("Gemini") + `",
        "` + _lt("holding hands") + `",
        "` + _lt("man") + `",
        "` + _lt("men") + `",
        "` + _lt("men holding hands") + `",
        "` + _lt("twins") + `",
        "` + _lt("zodiac") + `",
        "` + _lt("two men holding hands") + `"
    ],
    "name": "` + _lt("men holding hands") + `",
    "shortcodes": [
        ":men_holding_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💏",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("kiss") + `"
    ],
    "name": "` + _lt("kiss") + `",
    "shortcodes": [
        ":kiss:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍❤️‍💋‍👨",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("kiss") + `",
        "` + _lt("man") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("kiss: woman, man") + `",
    "shortcodes": [
        ":kiss:_woman,_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍❤️‍💋‍👨",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("kiss") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("kiss: man, man") + `",
    "shortcodes": [
        ":kiss:_man,_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍❤️‍💋‍👩",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("kiss") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("kiss: woman, woman") + `",
    "shortcodes": [
        ":kiss:_woman,_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💑",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("couple with heart") + `",
        "` + _lt("love") + `"
    ],
    "name": "` + _lt("couple with heart") + `",
    "shortcodes": [
        ":couple_with_heart:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍❤️‍👨",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("couple with heart") + `",
        "` + _lt("love") + `",
        "` + _lt("man") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("couple with heart: woman, man") + `",
    "shortcodes": [
        ":couple_with_heart:_woman,_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍❤️‍👨",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("couple with heart") + `",
        "` + _lt("love") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("couple with heart: man, man") + `",
    "shortcodes": [
        ":couple_with_heart:_man,_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍❤️‍👩",
    "emoticons": [],
    "keywords": [
        "` + _lt("couple") + `",
        "` + _lt("couple with heart") + `",
        "` + _lt("love") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("couple with heart: woman, woman") + `",
    "shortcodes": [
        ":couple_with_heart:_woman,_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👪",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `"
    ],
    "name": "` + _lt("family") + `",
    "shortcodes": [
        ":family:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("man") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: man, woman, boy") + `",
    "shortcodes": [
        ":family:_man,_woman,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: man, woman, girl") + `",
    "shortcodes": [
        ":family:_man,_woman,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: man, woman, girl, boy") + `",
    "shortcodes": [
        ":family:_man,_woman,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("man") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: man, woman, boy, boy") + `",
    "shortcodes": [
        ":family:_man,_woman,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: man, woman, girl, girl") + `",
    "shortcodes": [
        ":family:_man,_woman,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, man, boy") + `",
    "shortcodes": [
        ":family:_man,_man,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, man, girl") + `",
    "shortcodes": [
        ":family:_man,_man,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, man, girl, boy") + `",
    "shortcodes": [
        ":family:_man,_man,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, man, boy, boy") + `",
    "shortcodes": [
        ":family:_man,_man,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, man, girl, girl") + `",
    "shortcodes": [
        ":family:_man,_man,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, woman, boy") + `",
    "shortcodes": [
        ":family:_woman,_woman,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, woman, girl") + `",
    "shortcodes": [
        ":family:_woman,_woman,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, woman, girl, boy") + `",
    "shortcodes": [
        ":family:_woman,_woman,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, woman, boy, boy") + `",
    "shortcodes": [
        ":family:_woman,_woman,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, woman, girl, girl") + `",
    "shortcodes": [
        ":family:_woman,_woman,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, boy") + `",
    "shortcodes": [
        ":family:_man,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, boy, boy") + `",
    "shortcodes": [
        ":family:_man,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, girl") + `",
    "shortcodes": [
        ":family:_man,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, girl, boy") + `",
    "shortcodes": [
        ":family:_man,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("family: man, girl, girl") + `",
    "shortcodes": [
        ":family:_man,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, boy") + `",
    "shortcodes": [
        ":family:_woman,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, boy, boy") + `",
    "shortcodes": [
        ":family:_woman,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, girl") + `",
    "shortcodes": [
        ":family:_woman,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _lt("boy") + `",
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, girl, boy") + `",
    "shortcodes": [
        ":family:_woman,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _lt("family") + `",
        "` + _lt("girl") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("family: woman, girl, girl") + `",
    "shortcodes": [
        ":family:_woman,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🗣️",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("head") + `",
        "` + _lt("silhouette") + `",
        "` + _lt("speak") + `",
        "` + _lt("speaking") + `"
    ],
    "name": "` + _lt("speaking head") + `",
    "shortcodes": [
        ":speaking_head:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👤",
    "emoticons": [],
    "keywords": [
        "` + _lt("bust") + `",
        "` + _lt("bust in silhouette") + `",
        "` + _lt("silhouette") + `"
    ],
    "name": "` + _lt("bust in silhouette") + `",
    "shortcodes": [
        ":bust_in_silhouette:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👥",
    "emoticons": [],
    "keywords": [
        "` + _lt("bust") + `",
        "` + _lt("busts in silhouette") + `",
        "` + _lt("silhouette") + `"
    ],
    "name": "` + _lt("busts in silhouette") + `",
    "shortcodes": [
        ":busts_in_silhouette:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👣",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("footprint") + `",
        "` + _lt("footprints") + `",
        "` + _lt("print") + `"
    ],
    "name": "` + _lt("footprints") + `",
    "shortcodes": [
        ":footprints:"
    ]
},`;

const emojisData3 = `{
    "category": "Animals & Nature",
    "codepoints": "🐵",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("monkey") + `"
    ],
    "name": "` + _lt("monkey face") + `",
    "shortcodes": [
        ":monkey_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐒",
    "emoticons": [],
    "keywords": [
        "` + _lt("monkey") + `"
    ],
    "name": "` + _lt("monkey") + `",
    "shortcodes": [
        ":monkey:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦍",
    "emoticons": [],
    "keywords": [
        "` + _lt("gorilla") + `"
    ],
    "name": "` + _lt("gorilla") + `",
    "shortcodes": [
        ":gorilla:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦧",
    "emoticons": [],
    "keywords": [
        "` + _lt("ape") + `",
        "` + _lt("orangutan") + `"
    ],
    "name": "` + _lt("orangutan") + `",
    "shortcodes": [
        ":orangutan:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐶",
    "emoticons": [],
    "keywords": [
        "` + _lt("dog") + `",
        "` + _lt("face") + `",
        "` + _lt("pet") + `"
    ],
    "name": "` + _lt("dog face") + `",
    "shortcodes": [
        ":dog_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐕",
    "emoticons": [],
    "keywords": [
        "` + _lt("dog") + `",
        "` + _lt("pet") + `"
    ],
    "name": "` + _lt("dog") + `",
    "shortcodes": [
        ":dog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦮",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("blind") + `",
        "` + _lt("guide") + `",
        "` + _lt("guide dog") + `"
    ],
    "name": "` + _lt("guide dog") + `",
    "shortcodes": [
        ":guide_dog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐕‍🦺",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("assistance") + `",
        "` + _lt("dog") + `",
        "` + _lt("service") + `"
    ],
    "name": "` + _lt("service dog") + `",
    "shortcodes": [
        ":service_dog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐩",
    "emoticons": [],
    "keywords": [
        "` + _lt("dog") + `",
        "` + _lt("poodle") + `"
    ],
    "name": "` + _lt("poodle") + `",
    "shortcodes": [
        ":poodle:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐺",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("wolf") + `"
    ],
    "name": "` + _lt("wolf") + `",
    "shortcodes": [
        ":wolf:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦊",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("fox") + `"
    ],
    "name": "` + _lt("fox") + `",
    "shortcodes": [
        ":fox:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦝",
    "emoticons": [],
    "keywords": [
        "` + _lt("curious") + `",
        "` + _lt("raccoon") + `",
        "` + _lt("sly") + `"
    ],
    "name": "` + _lt("raccoon") + `",
    "shortcodes": [
        ":raccoon:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐱",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("face") + `",
        "` + _lt("pet") + `"
    ],
    "name": "` + _lt("cat face") + `",
    "shortcodes": [
        ":cat_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐈",
    "emoticons": [],
    "keywords": [
        "` + _lt("cat") + `",
        "` + _lt("pet") + `"
    ],
    "name": "` + _lt("cat") + `",
    "shortcodes": [
        ":cat:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦁",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("Leo") + `",
        "` + _lt("lion") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("lion") + `",
    "shortcodes": [
        ":lion:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐯",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("tiger") + `"
    ],
    "name": "` + _lt("tiger face") + `",
    "shortcodes": [
        ":tiger_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐅",
    "emoticons": [],
    "keywords": [
        "` + _lt("tiger") + `"
    ],
    "name": "` + _lt("tiger") + `",
    "shortcodes": [
        ":tiger:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐆",
    "emoticons": [],
    "keywords": [
        "` + _lt("leopard") + `"
    ],
    "name": "` + _lt("leopard") + `",
    "shortcodes": [
        ":leopard:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐴",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("horse") + `"
    ],
    "name": "` + _lt("horse face") + `",
    "shortcodes": [
        ":horse_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐎",
    "emoticons": [],
    "keywords": [
        "` + _lt("equestrian") + `",
        "` + _lt("horse") + `",
        "` + _lt("racehorse") + `",
        "` + _lt("racing") + `"
    ],
    "name": "` + _lt("horse") + `",
    "shortcodes": [
        ":horse:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦄",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("unicorn") + `"
    ],
    "name": "` + _lt("unicorn") + `",
    "shortcodes": [
        ":unicorn:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦓",
    "emoticons": [],
    "keywords": [
        "` + _lt("stripe") + `",
        "` + _lt("zebra") + `"
    ],
    "name": "` + _lt("zebra") + `",
    "shortcodes": [
        ":zebra:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦌",
    "emoticons": [],
    "keywords": [
        "` + _lt("deer") + `",
        "` + _lt("stag") + `"
    ],
    "name": "` + _lt("deer") + `",
    "shortcodes": [
        ":deer:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐮",
    "emoticons": [],
    "keywords": [
        "` + _lt("cow") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("cow face") + `",
    "shortcodes": [
        ":cow_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐂",
    "emoticons": [],
    "keywords": [
        "` + _lt("bull") + `",
        "` + _lt("ox") + `",
        "` + _lt("Taurus") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("ox") + `",
    "shortcodes": [
        ":ox:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐃",
    "emoticons": [],
    "keywords": [
        "` + _lt("buffalo") + `",
        "` + _lt("water") + `"
    ],
    "name": "` + _lt("water buffalo") + `",
    "shortcodes": [
        ":water_buffalo:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐄",
    "emoticons": [],
    "keywords": [
        "` + _lt("cow") + `"
    ],
    "name": "` + _lt("cow") + `",
    "shortcodes": [
        ":cow:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐷",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("pig") + `"
    ],
    "name": "` + _lt("pig face") + `",
    "shortcodes": [
        ":pig_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐖",
    "emoticons": [],
    "keywords": [
        "` + _lt("pig") + `",
        "` + _lt("sow") + `"
    ],
    "name": "` + _lt("pig") + `",
    "shortcodes": [
        ":pig:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐗",
    "emoticons": [
        ":boar"
    ],
    "keywords": [
        "` + _lt("boar") + `",
        "` + _lt("pig") + `"
    ],
    "name": "` + _lt("boar") + `",
    "shortcodes": [
        ":boar:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐽",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("nose") + `",
        "` + _lt("pig") + `"
    ],
    "name": "` + _lt("pig nose") + `",
    "shortcodes": [
        ":pig_nose:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐏",
    "emoticons": [],
    "keywords": [
        "` + _lt("Aries") + `",
        "` + _lt("male") + `",
        "` + _lt("ram") + `",
        "` + _lt("sheep") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("ram") + `",
    "shortcodes": [
        ":ram:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐑",
    "emoticons": [],
    "keywords": [
        "` + _lt("ewe") + `",
        "` + _lt("female") + `",
        "` + _lt("sheep") + `"
    ],
    "name": "` + _lt("ewe") + `",
    "shortcodes": [
        ":ewe:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐐",
    "emoticons": [],
    "keywords": [
        "` + _lt("Capricorn") + `",
        "` + _lt("goat") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("goat") + `",
    "shortcodes": [
        ":goat:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐪",
    "emoticons": [],
    "keywords": [
        "` + _lt("camel") + `",
        "` + _lt("dromedary") + `",
        "` + _lt("hump") + `"
    ],
    "name": "` + _lt("camel") + `",
    "shortcodes": [
        ":camel:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐫",
    "emoticons": [],
    "keywords": [
        "` + _lt("bactrian") + `",
        "` + _lt("camel") + `",
        "` + _lt("hump") + `",
        "` + _lt("two-hump camel") + `",
        "` + _lt("Bactrian") + `"
    ],
    "name": "` + _lt("two-hump camel") + `",
    "shortcodes": [
        ":two-hump_camel:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦙",
    "emoticons": [],
    "keywords": [
        "` + _lt("alpaca") + `",
        "` + _lt("guanaco") + `",
        "` + _lt("llama") + `",
        "` + _lt("vicuña") + `",
        "` + _lt("wool") + `"
    ],
    "name": "` + _lt("llama") + `",
    "shortcodes": [
        ":llama:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦒",
    "emoticons": [],
    "keywords": [
        "` + _lt("giraffe") + `",
        "` + _lt("spots") + `"
    ],
    "name": "` + _lt("giraffe") + `",
    "shortcodes": [
        ":giraffe:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐘",
    "emoticons": [],
    "keywords": [
        "` + _lt("elephant") + `"
    ],
    "name": "` + _lt("elephant") + `",
    "shortcodes": [
        ":elephant:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦏",
    "emoticons": [],
    "keywords": [
        "` + _lt("rhino") + `",
        "` + _lt("rhinoceros") + `"
    ],
    "name": "` + _lt("rhinoceros") + `",
    "shortcodes": [
        ":rhinoceros:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦛",
    "emoticons": [],
    "keywords": [
        "` + _lt("hippo") + `",
        "` + _lt("hippopotamus") + `"
    ],
    "name": "` + _lt("hippopotamus") + `",
    "shortcodes": [
        ":hippopotamus:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐭",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("mouse") + `",
        "` + _lt("pet") + `"
    ],
    "name": "` + _lt("mouse face") + `",
    "shortcodes": [
        ":mouse_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐁",
    "emoticons": [],
    "keywords": [
        "` + _lt("mouse") + `",
        "` + _lt("pet") + `",
        "` + _lt("rodent") + `"
    ],
    "name": "` + _lt("mouse") + `",
    "shortcodes": [
        ":mouse:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐀",
    "emoticons": [],
    "keywords": [
        "` + _lt("pet") + `",
        "` + _lt("rat") + `",
        "` + _lt("rodent") + `"
    ],
    "name": "` + _lt("rat") + `",
    "shortcodes": [
        ":rat:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐹",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("hamster") + `",
        "` + _lt("pet") + `"
    ],
    "name": "` + _lt("hamster") + `",
    "shortcodes": [
        ":hamster:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐰",
    "emoticons": [],
    "keywords": [
        "` + _lt("bunny") + `",
        "` + _lt("face") + `",
        "` + _lt("pet") + `",
        "` + _lt("rabbit") + `"
    ],
    "name": "` + _lt("rabbit face") + `",
    "shortcodes": [
        ":rabbit_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐇",
    "emoticons": [],
    "keywords": [
        "` + _lt("bunny") + `",
        "` + _lt("pet") + `",
        "` + _lt("rabbit") + `"
    ],
    "name": "` + _lt("rabbit") + `",
    "shortcodes": [
        ":rabbit:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐿️",
    "emoticons": [],
    "keywords": [
        "` + _lt("chipmunk") + `",
        "` + _lt("squirrel") + `"
    ],
    "name": "` + _lt("chipmunk") + `",
    "shortcodes": [
        ":chipmunk:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦔",
    "emoticons": [],
    "keywords": [
        "` + _lt("hedgehog") + `",
        "` + _lt("spiny") + `"
    ],
    "name": "` + _lt("hedgehog") + `",
    "shortcodes": [
        ":hedgehog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦇",
    "emoticons": [],
    "keywords": [
        "` + _lt("bat") + `",
        "` + _lt("vampire") + `"
    ],
    "name": "` + _lt("bat") + `",
    "shortcodes": [
        ":bat:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐻",
    "emoticons": [
        ":bear"
    ],
    "keywords": [
        "` + _lt("bear") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("bear") + `",
    "shortcodes": [
        ":bear:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐨",
    "emoticons": [],
    "keywords": [
        "` + _lt("koala") + `",
        "` + _lt("marsupial") + `",
        "` + _lt("face") + `"
    ],
    "name": "` + _lt("koala") + `",
    "shortcodes": [
        ":koala:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐼",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("panda") + `"
    ],
    "name": "` + _lt("panda") + `",
    "shortcodes": [
        ":panda:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦥",
    "emoticons": [],
    "keywords": [
        "` + _lt("lazy") + `",
        "` + _lt("sloth") + `",
        "` + _lt("slow") + `"
    ],
    "name": "` + _lt("sloth") + `",
    "shortcodes": [
        ":sloth:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦦",
    "emoticons": [],
    "keywords": [
        "` + _lt("fishing") + `",
        "` + _lt("otter") + `",
        "` + _lt("playful") + `"
    ],
    "name": "` + _lt("otter") + `",
    "shortcodes": [
        ":otter:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦨",
    "emoticons": [],
    "keywords": [
        "` + _lt("skunk") + `",
        "` + _lt("stink") + `"
    ],
    "name": "` + _lt("skunk") + `",
    "shortcodes": [
        ":skunk:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦘",
    "emoticons": [],
    "keywords": [
        "` + _lt("Australia") + `",
        "` + _lt("joey") + `",
        "` + _lt("jump") + `",
        "` + _lt("kangaroo") + `",
        "` + _lt("marsupial") + `"
    ],
    "name": "` + _lt("kangaroo") + `",
    "shortcodes": [
        ":kangaroo:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦡",
    "emoticons": [],
    "keywords": [
        "` + _lt("badger") + `",
        "` + _lt("honey badger") + `",
        "` + _lt("pester") + `"
    ],
    "name": "` + _lt("badger") + `",
    "shortcodes": [
        ":badger:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐾",
    "emoticons": [],
    "keywords": [
        "` + _lt("feet") + `",
        "` + _lt("paw") + `",
        "` + _lt("paw prints") + `",
        "` + _lt("print") + `"
    ],
    "name": "` + _lt("paw prints") + `",
    "shortcodes": [
        ":paw_prints:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦃",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("poultry") + `",
        "` + _lt("turkey") + `"
    ],
    "name": "` + _lt("turkey") + `",
    "shortcodes": [
        ":turkey:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐔",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("chicken") + `",
        "` + _lt("poultry") + `"
    ],
    "name": "` + _lt("chicken") + `",
    "shortcodes": [
        ":chicken:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐓",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("rooster") + `"
    ],
    "name": "` + _lt("rooster") + `",
    "shortcodes": [
        ":rooster:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐣",
    "emoticons": [],
    "keywords": [
        "` + _lt("baby") + `",
        "` + _lt("bird") + `",
        "` + _lt("chick") + `",
        "` + _lt("hatching") + `"
    ],
    "name": "` + _lt("hatching chick") + `",
    "shortcodes": [
        ":hatching_chick:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐤",
    "emoticons": [],
    "keywords": [
        "` + _lt("baby") + `",
        "` + _lt("bird") + `",
        "` + _lt("chick") + `"
    ],
    "name": "` + _lt("baby chick") + `",
    "shortcodes": [
        ":baby_chick:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐥",
    "emoticons": [],
    "keywords": [
        "` + _lt("baby") + `",
        "` + _lt("bird") + `",
        "` + _lt("chick") + `",
        "` + _lt("front-facing baby chick") + `"
    ],
    "name": "` + _lt("front-facing baby chick") + `",
    "shortcodes": [
        ":front-facing_baby_chick:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐦",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `"
    ],
    "name": "` + _lt("bird") + `",
    "shortcodes": [
        ":bird:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐧",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("penguin") + `"
    ],
    "name": "` + _lt("penguin") + `",
    "shortcodes": [
        ":penguin:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🕊️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("dove") + `",
        "` + _lt("fly") + `",
        "` + _lt("peace") + `"
    ],
    "name": "` + _lt("dove") + `",
    "shortcodes": [
        ":dove:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦅",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird of prey") + `",
        "` + _lt("eagle") + `",
        "` + _lt("bird") + `"
    ],
    "name": "` + _lt("eagle") + `",
    "shortcodes": [
        ":eagle:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦆",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("duck") + `"
    ],
    "name": "` + _lt("duck") + `",
    "shortcodes": [
        ":duck:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦢",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("cygnet") + `",
        "` + _lt("swan") + `",
        "` + _lt("ugly duckling") + `"
    ],
    "name": "` + _lt("swan") + `",
    "shortcodes": [
        ":swan:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦉",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird of prey") + `",
        "` + _lt("owl") + `",
        "` + _lt("wise") + `",
        "` + _lt("bird") + `"
    ],
    "name": "` + _lt("owl") + `",
    "shortcodes": [
        ":owl:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦩",
    "emoticons": [],
    "keywords": [
        "` + _lt("flamboyant") + `",
        "` + _lt("flamingo") + `",
        "` + _lt("tropical") + `"
    ],
    "name": "` + _lt("flamingo") + `",
    "shortcodes": [
        ":flamingo:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦚",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("ostentatious") + `",
        "` + _lt("peacock") + `",
        "` + _lt("peahen") + `",
        "` + _lt("proud") + `"
    ],
    "name": "` + _lt("peacock") + `",
    "shortcodes": [
        ":peacock:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦜",
    "emoticons": [],
    "keywords": [
        "` + _lt("bird") + `",
        "` + _lt("parrot") + `",
        "` + _lt("pirate") + `",
        "` + _lt("talk") + `"
    ],
    "name": "` + _lt("parrot") + `",
    "shortcodes": [
        ":parrot:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐸",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("frog") + `"
    ],
    "name": "` + _lt("frog") + `",
    "shortcodes": [
        ":frog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐊",
    "emoticons": [],
    "keywords": [
        "` + _lt("crocodile") + `"
    ],
    "name": "` + _lt("crocodile") + `",
    "shortcodes": [
        ":crocodile:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐢",
    "emoticons": [],
    "keywords": [
        "` + _lt("terrapin") + `",
        "` + _lt("tortoise") + `",
        "` + _lt("turtle") + `"
    ],
    "name": "` + _lt("turtle") + `",
    "shortcodes": [
        ":turtle:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦎",
    "emoticons": [],
    "keywords": [
        "` + _lt("lizard") + `",
        "` + _lt("reptile") + `"
    ],
    "name": "` + _lt("lizard") + `",
    "shortcodes": [
        ":lizard:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐍",
    "emoticons": [],
    "keywords": [
        "` + _lt("bearer") + `",
        "` + _lt("Ophiuchus") + `",
        "` + _lt("serpent") + `",
        "` + _lt("snake") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("snake") + `",
    "shortcodes": [
        ":snake:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐲",
    "emoticons": [],
    "keywords": [
        "` + _lt("dragon") + `",
        "` + _lt("face") + `",
        "` + _lt("fairy tale") + `"
    ],
    "name": "` + _lt("dragon face") + `",
    "shortcodes": [
        ":dragon_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐉",
    "emoticons": [],
    "keywords": [
        "` + _lt("dragon") + `",
        "` + _lt("fairy tale") + `"
    ],
    "name": "` + _lt("dragon") + `",
    "shortcodes": [
        ":dragon:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦕",
    "emoticons": [],
    "keywords": [
        "` + _lt("brachiosaurus") + `",
        "` + _lt("brontosaurus") + `",
        "` + _lt("diplodocus") + `",
        "` + _lt("sauropod") + `"
    ],
    "name": "` + _lt("sauropod") + `",
    "shortcodes": [
        ":sauropod:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦖",
    "emoticons": [],
    "keywords": [
        "` + _lt("T-Rex") + `",
        "` + _lt("Tyrannosaurus Rex") + `"
    ],
    "name": "` + _lt("T-Rex") + `",
    "shortcodes": [
        ":T-Rex:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐳",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("spouting") + `",
        "` + _lt("whale") + `"
    ],
    "name": "` + _lt("spouting whale") + `",
    "shortcodes": [
        ":spouting_whale:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐋",
    "emoticons": [],
    "keywords": [
        "` + _lt("whale") + `"
    ],
    "name": "` + _lt("whale") + `",
    "shortcodes": [
        ":whale:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐬",
    "emoticons": [],
    "keywords": [
        "` + _lt("dolphin") + `",
        "` + _lt("porpoise") + `",
        "` + _lt("flipper") + `"
    ],
    "name": "` + _lt("dolphin") + `",
    "shortcodes": [
        ":dolphin:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐟",
    "emoticons": [],
    "keywords": [
        "` + _lt("fish") + `",
        "` + _lt("Pisces") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("fish") + `",
    "shortcodes": [
        ":fish:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐠",
    "emoticons": [],
    "keywords": [
        "` + _lt("fish") + `",
        "` + _lt("reef fish") + `",
        "` + _lt("tropical") + `"
    ],
    "name": "` + _lt("tropical fish") + `",
    "shortcodes": [
        ":tropical_fish:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐡",
    "emoticons": [],
    "keywords": [
        "` + _lt("blowfish") + `",
        "` + _lt("fish") + `"
    ],
    "name": "` + _lt("blowfish") + `",
    "shortcodes": [
        ":blowfish:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦈",
    "emoticons": [],
    "keywords": [
        "` + _lt("fish") + `",
        "` + _lt("shark") + `"
    ],
    "name": "` + _lt("shark") + `",
    "shortcodes": [
        ":shark:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐙",
    "emoticons": [],
    "keywords": [
        "` + _lt("octopus") + `"
    ],
    "name": "` + _lt("octopus") + `",
    "shortcodes": [
        ":octopus:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐚",
    "emoticons": [],
    "keywords": [
        "` + _lt("shell") + `",
        "` + _lt("spiral") + `"
    ],
    "name": "` + _lt("spiral shell") + `",
    "shortcodes": [
        ":spiral_shell:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐌",
    "emoticons": [
        ":snail"
    ],
    "keywords": [
        "` + _lt("mollusc") + `",
        "` + _lt("snail") + `"
    ],
    "name": "` + _lt("snail") + `",
    "shortcodes": [
        ":snail:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦋",
    "emoticons": [],
    "keywords": [
        "` + _lt("butterfly") + `",
        "` + _lt("insect") + `",
        "` + _lt("moth") + `",
        "` + _lt("pretty") + `"
    ],
    "name": "` + _lt("butterfly") + `",
    "shortcodes": [
        ":butterfly:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐛",
    "emoticons": [],
    "keywords": [
        "` + _lt("bug") + `",
        "` + _lt("caterpillar") + `",
        "` + _lt("insect") + `",
        "` + _lt("worm") + `"
    ],
    "name": "` + _lt("bug") + `",
    "shortcodes": [
        ":bug:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐜",
    "emoticons": [],
    "keywords": [
        "` + _lt("ant") + `",
        "` + _lt("insect") + `"
    ],
    "name": "` + _lt("ant") + `",
    "shortcodes": [
        ":ant:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐝",
    "emoticons": [],
    "keywords": [
        "` + _lt("bee") + `",
        "` + _lt("honeybee") + `",
        "` + _lt("insect") + `"
    ],
    "name": "` + _lt("honeybee") + `",
    "shortcodes": [
        ":honeybee:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐞",
    "emoticons": [
        ":bug"
    ],
    "keywords": [
        "` + _lt("beetle") + `",
        "` + _lt("insect") + `",
        "` + _lt("lady beetle") + `",
        "` + _lt("ladybird") + `",
        "` + _lt("ladybug") + `"
    ],
    "name": "` + _lt("lady beetle") + `",
    "shortcodes": [
        ":lady_beetle:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦗",
    "emoticons": [],
    "keywords": [
        "` + _lt("cricket") + `",
        "` + _lt("grasshopper") + `"
    ],
    "name": "` + _lt("cricket") + `",
    "shortcodes": [
        ":cricket:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🕷️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arachnid") + `",
        "` + _lt("spider") + `",
        "` + _lt("insect") + `"
    ],
    "name": "` + _lt("spider") + `",
    "shortcodes": [
        ":spider:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🕸️",
    "emoticons": [],
    "keywords": [
        "` + _lt("spider") + `",
        "` + _lt("web") + `"
    ],
    "name": "` + _lt("spider web") + `",
    "shortcodes": [
        ":spider_web:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦂",
    "emoticons": [],
    "keywords": [
        "` + _lt("scorpio") + `",
        "` + _lt("Scorpio") + `",
        "` + _lt("scorpion") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("scorpion") + `",
    "shortcodes": [
        ":scorpion:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦟",
    "emoticons": [],
    "keywords": [
        "` + _lt("dengue") + `",
        "` + _lt("fever") + `",
        "` + _lt("insect") + `",
        "` + _lt("malaria") + `",
        "` + _lt("mosquito") + `",
        "` + _lt("mozzie") + `",
        "` + _lt("virus") + `",
        "` + _lt("disease") + `",
        "` + _lt("pest") + `"
    ],
    "name": "` + _lt("mosquito") + `",
    "shortcodes": [
        ":mosquito:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦠",
    "emoticons": [],
    "keywords": [
        "` + _lt("amoeba") + `",
        "` + _lt("bacteria") + `",
        "` + _lt("microbe") + `",
        "` + _lt("virus") + `"
    ],
    "name": "` + _lt("microbe") + `",
    "shortcodes": [
        ":microbe:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "💐",
    "emoticons": [],
    "keywords": [
        "` + _lt("bouquet") + `",
        "` + _lt("flower") + `"
    ],
    "name": "` + _lt("bouquet") + `",
    "shortcodes": [
        ":bouquet:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌸",
    "emoticons": [],
    "keywords": [
        "` + _lt("blossom") + `",
        "` + _lt("cherry") + `",
        "` + _lt("flower") + `"
    ],
    "name": "` + _lt("cherry blossom") + `",
    "shortcodes": [
        ":cherry_blossom:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "💮",
    "emoticons": [],
    "keywords": [
        "` + _lt("flower") + `",
        "` + _lt("white flower") + `"
    ],
    "name": "` + _lt("white flower") + `",
    "shortcodes": [
        ":white_flower:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🏵️",
    "emoticons": [],
    "keywords": [
        "` + _lt("plant") + `",
        "` + _lt("rosette") + `"
    ],
    "name": "` + _lt("rosette") + `",
    "shortcodes": [
        ":rosette:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌹",
    "emoticons": [
        ":sunflower"
    ],
    "keywords": [
        "` + _lt("flower") + `",
        "` + _lt("rose") + `"
    ],
    "name": "` + _lt("rose") + `",
    "shortcodes": [
        ":rose:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🥀",
    "emoticons": [],
    "keywords": [
        "` + _lt("flower") + `",
        "` + _lt("wilted") + `"
    ],
    "name": "` + _lt("wilted flower") + `",
    "shortcodes": [
        ":wilted_flower:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌺",
    "emoticons": [],
    "keywords": [
        "` + _lt("flower") + `",
        "` + _lt("hibiscus") + `"
    ],
    "name": "` + _lt("hibiscus") + `",
    "shortcodes": [
        ":hibiscus:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌻",
    "emoticons": [],
    "keywords": [
        "` + _lt("flower") + `",
        "` + _lt("sun") + `",
        "` + _lt("sunflower") + `"
    ],
    "name": "` + _lt("sunflower") + `",
    "shortcodes": [
        ":sunflower:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌼",
    "emoticons": [],
    "keywords": [
        "` + _lt("blossom") + `",
        "` + _lt("flower") + `"
    ],
    "name": "` + _lt("blossom") + `",
    "shortcodes": [
        ":blossom:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌷",
    "emoticons": [],
    "keywords": [
        "` + _lt("flower") + `",
        "` + _lt("tulip") + `"
    ],
    "name": "` + _lt("tulip") + `",
    "shortcodes": [
        ":tulip:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌱",
    "emoticons": [],
    "keywords": [
        "` + _lt("seedling") + `",
        "` + _lt("young") + `"
    ],
    "name": "` + _lt("seedling") + `",
    "shortcodes": [
        ":seedling:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌲",
    "emoticons": [],
    "keywords": [
        "` + _lt("evergreen tree") + `",
        "` + _lt("tree") + `"
    ],
    "name": "` + _lt("evergreen tree") + `",
    "shortcodes": [
        ":evergreen_ltree:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌳",
    "emoticons": [],
    "keywords": [
        "` + _lt("deciduous") + `",
        "` + _lt("shedding") + `",
        "` + _lt("tree") + `"
    ],
    "name": "` + _lt("deciduous tree") + `",
    "shortcodes": [
        ":deciduous_ltree:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌴",
    "emoticons": [],
    "keywords": [
        "` + _lt("palm") + `",
        "` + _lt("tree") + `"
    ],
    "name": "` + _lt("palm tree") + `",
    "shortcodes": [
        ":palm_ltree:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌵",
    "emoticons": [],
    "keywords": [
        "` + _lt("cactus") + `",
        "` + _lt("plant") + `"
    ],
    "name": "` + _lt("cactus") + `",
    "shortcodes": [
        ":cactus:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌾",
    "emoticons": [],
    "keywords": [
        "` + _lt("ear") + `",
        "` + _lt("grain") + `",
        "` + _lt("rice") + `",
        "` + _lt("sheaf of rice") + `",
        "` + _lt("sheaf") + `"
    ],
    "name": "` + _lt("sheaf of rice") + `",
    "shortcodes": [
        ":sheaf_of_rice:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌿",
    "emoticons": [],
    "keywords": [
        "` + _lt("herb") + `",
        "` + _lt("leaf") + `"
    ],
    "name": "` + _lt("herb") + `",
    "shortcodes": [
        ":herb:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "☘️",
    "emoticons": [],
    "keywords": [
        "` + _lt("plant") + `",
        "` + _lt("shamrock") + `"
    ],
    "name": "` + _lt("shamrock") + `",
    "shortcodes": [
        ":shamrock:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🍀",
    "emoticons": [
        ":clover"
    ],
    "keywords": [
        "` + _lt("4") + `",
        "` + _lt("clover") + `",
        "` + _lt("four") + `",
        "` + _lt("four-leaf clover") + `",
        "` + _lt("leaf") + `"
    ],
    "name": "` + _lt("four leaf clover") + `",
    "shortcodes": [
        ":four_leaf_clover:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🍁",
    "emoticons": [],
    "keywords": [
        "` + _lt("falling") + `",
        "` + _lt("leaf") + `",
        "` + _lt("maple") + `"
    ],
    "name": "` + _lt("maple leaf") + `",
    "shortcodes": [
        ":maple_leaf:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🍂",
    "emoticons": [],
    "keywords": [
        "` + _lt("fallen leaf") + `",
        "` + _lt("falling") + `",
        "` + _lt("leaf") + `"
    ],
    "name": "` + _lt("fallen leaf") + `",
    "shortcodes": [
        ":fallen_leaf:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🍃",
    "emoticons": [],
    "keywords": [
        "` + _lt("blow") + `",
        "` + _lt("flutter") + `",
        "` + _lt("leaf") + `",
        "` + _lt("leaf fluttering in wind") + `",
        "` + _lt("wind") + `"
    ],
    "name": "` + _lt("leaf fluttering in wind") + `",
    "shortcodes": [
        ":leaf_fluttering_in_wind:"
    ]
},`;

const emojisData4 = `{
    "category": "Food & Drink",
    "codepoints": "🍇",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("grape") + `",
        "` + _lt("grapes") + `"
    ],
    "name": "` + _lt("grapes") + `",
    "shortcodes": [
        ":grapes:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍈",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("melon") + `"
    ],
    "name": "` + _lt("melon") + `",
    "shortcodes": [
        ":melon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍉",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("watermelon") + `"
    ],
    "name": "` + _lt("watermelon") + `",
    "shortcodes": [
        ":watermelon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍊",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("mandarin") + `",
        "` + _lt("orange") + `",
        "` + _lt("tangerine") + `"
    ],
    "name": "` + _lt("tangerine") + `",
    "shortcodes": [
        ":tangerine:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍋",
    "emoticons": [],
    "keywords": [
        "` + _lt("citrus") + `",
        "` + _lt("fruit") + `",
        "` + _lt("lemon") + `"
    ],
    "name": "` + _lt("lemon") + `",
    "shortcodes": [
        ":lemon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍌",
    "emoticons": [
        ":banana"
    ],
    "keywords": [
        "` + _lt("banana") + `",
        "` + _lt("fruit") + `"
    ],
    "name": "` + _lt("banana") + `",
    "shortcodes": [
        ":banana:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍍",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("pineapple") + `"
    ],
    "name": "` + _lt("pineapple") + `",
    "shortcodes": [
        ":pineapple:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥭",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("mango") + `",
        "` + _lt("tropical") + `"
    ],
    "name": "` + _lt("mango") + `",
    "shortcodes": [
        ":mango:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍎",
    "emoticons": [],
    "keywords": [
        "` + _lt("apple") + `",
        "` + _lt("fruit") + `",
        "` + _lt("red") + `"
    ],
    "name": "` + _lt("red apple") + `",
    "shortcodes": [
        ":red_apple:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍏",
    "emoticons": [],
    "keywords": [
        "` + _lt("apple") + `",
        "` + _lt("fruit") + `",
        "` + _lt("green") + `"
    ],
    "name": "` + _lt("green apple") + `",
    "shortcodes": [
        ":green_apple:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍐",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("pear") + `"
    ],
    "name": "` + _lt("pear") + `",
    "shortcodes": [
        ":pear:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍑",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("peach") + `"
    ],
    "name": "` + _lt("peach") + `",
    "shortcodes": [
        ":peach:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍒",
    "emoticons": [],
    "keywords": [
        "` + _lt("berries") + `",
        "` + _lt("cherries") + `",
        "` + _lt("cherry") + `",
        "` + _lt("fruit") + `",
        "` + _lt("red") + `"
    ],
    "name": "` + _lt("cherries") + `",
    "shortcodes": [
        ":cherries:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍓",
    "emoticons": [],
    "keywords": [
        "` + _lt("berry") + `",
        "` + _lt("fruit") + `",
        "` + _lt("strawberry") + `"
    ],
    "name": "` + _lt("strawberry") + `",
    "shortcodes": [
        ":strawberry:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥝",
    "emoticons": [],
    "keywords": [
        "` + _lt("food") + `",
        "` + _lt("fruit") + `",
        "` + _lt("kiwi fruit") + `",
        "` + _lt("kiwi") + `"
    ],
    "name": "` + _lt("kiwi fruit") + `",
    "shortcodes": [
        ":kiwi_fruit:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍅",
    "emoticons": [],
    "keywords": [
        "` + _lt("fruit") + `",
        "` + _lt("tomato") + `",
        "` + _lt("vegetable") + `"
    ],
    "name": "` + _lt("tomato") + `",
    "shortcodes": [
        ":tomato:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥥",
    "emoticons": [],
    "keywords": [
        "` + _lt("coconut") + `",
        "` + _lt("palm") + `",
        "` + _lt("piña colada") + `"
    ],
    "name": "` + _lt("coconut") + `",
    "shortcodes": [
        ":coconut:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥑",
    "emoticons": [],
    "keywords": [
        "` + _lt("avocado") + `",
        "` + _lt("food") + `",
        "` + _lt("fruit") + `"
    ],
    "name": "` + _lt("avocado") + `",
    "shortcodes": [
        ":avocado:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍆",
    "emoticons": [],
    "keywords": [
        "` + _lt("aubergine") + `",
        "` + _lt("eggplant") + `",
        "` + _lt("vegetable") + `"
    ],
    "name": "` + _lt("eggplant") + `",
    "shortcodes": [
        ":eggplant:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥔",
    "emoticons": [],
    "keywords": [
        "` + _lt("food") + `",
        "` + _lt("potato") + `",
        "` + _lt("vegetable") + `"
    ],
    "name": "` + _lt("potato") + `",
    "shortcodes": [
        ":potato:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥕",
    "emoticons": [],
    "keywords": [
        "` + _lt("carrot") + `",
        "` + _lt("food") + `",
        "` + _lt("vegetable") + `"
    ],
    "name": "` + _lt("carrot") + `",
    "shortcodes": [
        ":carrot:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌽",
    "emoticons": [],
    "keywords": [
        "` + _lt("corn") + `",
        "` + _lt("corn on the cob") + `",
        "` + _lt("sweetcorn") + `",
        "` + _lt("ear") + `",
        "` + _lt("ear of corn") + `",
        "` + _lt("maize") + `",
        "` + _lt("maze") + `"
    ],
    "name": "` + _lt("ear of corn") + `",
    "shortcodes": [
        ":ear_of_corn:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌶️",
    "emoticons": [],
    "keywords": [
        "` + _lt("chilli") + `",
        "` + _lt("hot pepper") + `",
        "` + _lt("pepper") + `",
        "` + _lt("hot") + `"
    ],
    "name": "` + _lt("hot pepper") + `",
    "shortcodes": [
        ":hot_pepper:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥒",
    "emoticons": [],
    "keywords": [
        "` + _lt("cucumber") + `",
        "` + _lt("food") + `",
        "` + _lt("pickle") + `",
        "` + _lt("vegetable") + `"
    ],
    "name": "` + _lt("cucumber") + `",
    "shortcodes": [
        ":cucumber:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥬",
    "emoticons": [],
    "keywords": [
        "` + _lt("bok choy") + `",
        "` + _lt("leafy green") + `",
        "` + _lt("pak choi") + `",
        "` + _lt("cabbage") + `",
        "` + _lt("kale") + `",
        "` + _lt("lettuce") + `"
    ],
    "name": "` + _lt("leafy green") + `",
    "shortcodes": [
        ":leafy_green:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥦",
    "emoticons": [],
    "keywords": [
        "` + _lt("broccoli") + `",
        "` + _lt("wild cabbage") + `"
    ],
    "name": "` + _lt("broccoli") + `",
    "shortcodes": [
        ":broccoli:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧄",
    "emoticons": [],
    "keywords": [
        "` + _lt("flavouring") + `",
        "` + _lt("garlic") + `",
        "` + _lt("flavoring") + `"
    ],
    "name": "` + _lt("garlic") + `",
    "shortcodes": [
        ":garlic:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧅",
    "emoticons": [],
    "keywords": [
        "` + _lt("flavouring") + `",
        "` + _lt("onion") + `",
        "` + _lt("flavoring") + `"
    ],
    "name": "` + _lt("onion") + `",
    "shortcodes": [
        ":onion:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍄",
    "emoticons": [],
    "keywords": [
        "` + _lt("mushroom") + `",
        "` + _lt("toadstool") + `"
    ],
    "name": "` + _lt("mushroom") + `",
    "shortcodes": [
        ":mushroom:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥜",
    "emoticons": [],
    "keywords": [
        "` + _lt("food") + `",
        "` + _lt("nut") + `",
        "` + _lt("nuts") + `",
        "` + _lt("peanut") + `",
        "` + _lt("peanuts") + `",
        "` + _lt("vegetable") + `"
    ],
    "name": "` + _lt("peanuts") + `",
    "shortcodes": [
        ":peanuts:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌰",
    "emoticons": [],
    "keywords": [
        "` + _lt("chestnut") + `",
        "` + _lt("plant") + `",
        "` + _lt("nut") + `"
    ],
    "name": "` + _lt("chestnut") + `",
    "shortcodes": [
        ":chestnut:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍞",
    "emoticons": [],
    "keywords": [
        "` + _lt("bread") + `",
        "` + _lt("loaf") + `"
    ],
    "name": "` + _lt("bread") + `",
    "shortcodes": [
        ":bread:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥐",
    "emoticons": [],
    "keywords": [
        "` + _lt("bread") + `",
        "` + _lt("breakfast") + `",
        "` + _lt("croissant") + `",
        "` + _lt("food") + `",
        "` + _lt("french") + `",
        "` + _lt("roll") + `",
        "` + _lt("crescent roll") + `",
        "` + _lt("French") + `"
    ],
    "name": "` + _lt("croissant") + `",
    "shortcodes": [
        ":croissant:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥖",
    "emoticons": [],
    "keywords": [
        "` + _lt("baguette") + `",
        "` + _lt("bread") + `",
        "` + _lt("food") + `",
        "` + _lt("french") + `",
        "` + _lt("French stick") + `",
        "` + _lt("French") + `"
    ],
    "name": "` + _lt("baguette bread") + `",
    "shortcodes": [
        ":baguette_bread:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥨",
    "emoticons": [],
    "keywords": [
        "` + _lt("pretzel") + `",
        "` + _lt("twisted") + `"
    ],
    "name": "` + _lt("pretzel") + `",
    "shortcodes": [
        ":pretzel:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥯",
    "emoticons": [],
    "keywords": [
        "` + _lt("bagel") + `",
        "` + _lt("bakery") + `",
        "` + _lt("breakfast") + `",
        "` + _lt("schmear") + `"
    ],
    "name": "` + _lt("bagel") + `",
    "shortcodes": [
        ":bagel:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥞",
    "emoticons": [],
    "keywords": [
        "` + _lt("breakfast") + `",
        "` + _lt("crêpe") + `",
        "` + _lt("food") + `",
        "` + _lt("hotcake") + `",
        "` + _lt("pancake") + `",
        "` + _lt("pancakes") + `"
    ],
    "name": "` + _lt("pancakes") + `",
    "shortcodes": [
        ":pancakes:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧇",
    "emoticons": [],
    "keywords": [
        "` + _lt("waffle") + `",
        "` + _lt("waffle with butter") + `",
        "` + _lt("breakfast") + `",
        "` + _lt("indecisive") + `",
        "` + _lt("iron") + `",
        "` + _lt("unclear") + `",
        "` + _lt("vague") + `"
    ],
    "name": "` + _lt("waffle") + `",
    "shortcodes": [
        ":waffle:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧀",
    "emoticons": [
        ":cheese"
    ],
    "keywords": [
        "` + _lt("cheese") + `",
        "` + _lt("cheese wedge") + `"
    ],
    "name": "` + _lt("cheese wedge") + `",
    "shortcodes": [
        ":cheese_wedge:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍖",
    "emoticons": [],
    "keywords": [
        "` + _lt("bone") + `",
        "` + _lt("meat") + `",
        "` + _lt("meat on bone") + `"
    ],
    "name": "` + _lt("meat on bone") + `",
    "shortcodes": [
        ":meat_on_bone:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍗",
    "emoticons": [],
    "keywords": [
        "` + _lt("bone") + `",
        "` + _lt("chicken") + `",
        "` + _lt("drumstick") + `",
        "` + _lt("leg") + `",
        "` + _lt("poultry") + `"
    ],
    "name": "` + _lt("poultry leg") + `",
    "shortcodes": [
        ":poultry_leg:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥩",
    "emoticons": [],
    "keywords": [
        "` + _lt("chop") + `",
        "` + _lt("cut of meat") + `",
        "` + _lt("lambchop") + `",
        "` + _lt("porkchop") + `",
        "` + _lt("steak") + `",
        "` + _lt("lamb chop") + `",
        "` + _lt("pork chop") + `"
    ],
    "name": "` + _lt("cut of meat") + `",
    "shortcodes": [
        ":cut_of_meat:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥓",
    "emoticons": [],
    "keywords": [
        "` + _lt("bacon") + `",
        "` + _lt("breakfast") + `",
        "` + _lt("food") + `",
        "` + _lt("meat") + `"
    ],
    "name": "` + _lt("bacon") + `",
    "shortcodes": [
        ":bacon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍔",
    "emoticons": [
        ":hamburger"
    ],
    "keywords": [
        "` + _lt("beefburger") + `",
        "` + _lt("burger") + `",
        "` + _lt("hamburger") + `"
    ],
    "name": "` + _lt("hamburger") + `",
    "shortcodes": [
        ":hamburger:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍟",
    "emoticons": [
        ":fries"
    ],
    "keywords": [
        "` + _lt("chips") + `",
        "` + _lt("french fries") + `",
        "` + _lt("fries") + `",
        "` + _lt("french") + `",
        "` + _lt("French") + `"
    ],
    "name": "` + _lt("french fries") + `",
    "shortcodes": [
        ":french_fries:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍕",
    "emoticons": [
        ":pizza"
    ],
    "keywords": [
        "` + _lt("cheese") + `",
        "` + _lt("pizza") + `",
        "` + _lt("slice") + `"
    ],
    "name": "` + _lt("pizza") + `",
    "shortcodes": [
        ":pizza:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌭",
    "emoticons": [],
    "keywords": [
        "` + _lt("frankfurter") + `",
        "` + _lt("hot dog") + `",
        "` + _lt("hotdog") + `",
        "` + _lt("sausage") + `"
    ],
    "name": "` + _lt("hot dog") + `",
    "shortcodes": [
        ":hot_dog:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥪",
    "emoticons": [],
    "keywords": [
        "` + _lt("bread") + `",
        "` + _lt("sandwich") + `"
    ],
    "name": "` + _lt("sandwich") + `",
    "shortcodes": [
        ":sandwich:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌮",
    "emoticons": [],
    "keywords": [
        "` + _lt("mexican") + `",
        "` + _lt("taco") + `",
        "` + _lt("Mexican") + `"
    ],
    "name": "` + _lt("taco") + `",
    "shortcodes": [
        ":taco:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌯",
    "emoticons": [],
    "keywords": [
        "` + _lt("burrito") + `",
        "` + _lt("mexican") + `",
        "` + _lt("wrap") + `",
        "` + _lt("Mexican") + `"
    ],
    "name": "` + _lt("burrito") + `",
    "shortcodes": [
        ":burrito:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥙",
    "emoticons": [],
    "keywords": [
        "` + _lt("falafel") + `",
        "` + _lt("flatbread") + `",
        "` + _lt("food") + `",
        "` + _lt("gyro") + `",
        "` + _lt("kebab") + `",
        "` + _lt("pita") + `",
        "` + _lt("pita roll") + `",
        "` + _lt("stuffed") + `"
    ],
    "name": "` + _lt("stuffed flatbread") + `",
    "shortcodes": [
        ":stuffed_flatbread:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧆",
    "emoticons": [],
    "keywords": [
        "` + _lt("chickpea") + `",
        "` + _lt("falafel") + `",
        "` + _lt("meatball") + `",
        "` + _lt("chick pea") + `"
    ],
    "name": "` + _lt("falafel") + `",
    "shortcodes": [
        ":falafel:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥚",
    "emoticons": [],
    "keywords": [
        "` + _lt("breakfast") + `",
        "` + _lt("egg") + `",
        "` + _lt("food") + `"
    ],
    "name": "` + _lt("egg") + `",
    "shortcodes": [
        ":egg:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍳",
    "emoticons": [],
    "keywords": [
        "` + _lt("breakfast") + `",
        "` + _lt("cooking") + `",
        "` + _lt("egg") + `",
        "` + _lt("frying") + `",
        "` + _lt("pan") + `"
    ],
    "name": "` + _lt("cooking") + `",
    "shortcodes": [
        ":cooking:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥘",
    "emoticons": [],
    "keywords": [
        "` + _lt("casserole") + `",
        "` + _lt("food") + `",
        "` + _lt("paella") + `",
        "` + _lt("pan") + `",
        "` + _lt("shallow") + `",
        "` + _lt("shallow pan of food") + `"
    ],
    "name": "` + _lt("shallow pan of food") + `",
    "shortcodes": [
        ":shallow_pan_of_food:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍲",
    "emoticons": [],
    "keywords": [
        "` + _lt("pot") + `",
        "` + _lt("pot of food") + `",
        "` + _lt("stew") + `"
    ],
    "name": "` + _lt("pot of food") + `",
    "shortcodes": [
        ":pot_of_food:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥣",
    "emoticons": [],
    "keywords": [
        "` + _lt("bowl with spoon") + `",
        "` + _lt("breakfast") + `",
        "` + _lt("cereal") + `",
        "` + _lt("congee") + `"
    ],
    "name": "` + _lt("bowl with spoon") + `",
    "shortcodes": [
        ":bowl_with_spoon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥗",
    "emoticons": [],
    "keywords": [
        "` + _lt("food") + `",
        "` + _lt("garden") + `",
        "` + _lt("salad") + `",
        "` + _lt("green") + `"
    ],
    "name": "` + _lt("green salad") + `",
    "shortcodes": [
        ":green_salad:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍿",
    "emoticons": [],
    "keywords": [
        "` + _lt("popcorn") + `"
    ],
    "name": "` + _lt("popcorn") + `",
    "shortcodes": [
        ":popcorn:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧈",
    "emoticons": [],
    "keywords": [
        "` + _lt("butter") + `",
        "` + _lt("dairy") + `"
    ],
    "name": "` + _lt("butter") + `",
    "shortcodes": [
        ":butter:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧂",
    "emoticons": [],
    "keywords": [
        "` + _lt("condiment") + `",
        "` + _lt("salt") + `",
        "` + _lt("shaker") + `"
    ],
    "name": "` + _lt("salt") + `",
    "shortcodes": [
        ":salt:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥫",
    "emoticons": [],
    "keywords": [
        "` + _lt("can") + `",
        "` + _lt("canned food") + `"
    ],
    "name": "` + _lt("canned food") + `",
    "shortcodes": [
        ":canned_food:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍱",
    "emoticons": [],
    "keywords": [
        "` + _lt("bento") + `",
        "` + _lt("box") + `"
    ],
    "name": "` + _lt("bento box") + `",
    "shortcodes": [
        ":bento_box:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍘",
    "emoticons": [],
    "keywords": [
        "` + _lt("cracker") + `",
        "` + _lt("rice") + `"
    ],
    "name": "` + _lt("rice cracker") + `",
    "shortcodes": [
        ":rice_cracker:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍙",
    "emoticons": [
        ":rice_ball"
    ],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("rice") + `"
    ],
    "name": "` + _lt("rice ball") + `",
    "shortcodes": [
        ":rice_ball:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍚",
    "emoticons": [],
    "keywords": [
        "` + _lt("cooked") + `",
        "` + _lt("rice") + `"
    ],
    "name": "` + _lt("cooked rice") + `",
    "shortcodes": [
        ":cooked_rice:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍛",
    "emoticons": [],
    "keywords": [
        "` + _lt("curry") + `",
        "` + _lt("rice") + `"
    ],
    "name": "` + _lt("curry rice") + `",
    "shortcodes": [
        ":curry_rice:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍜",
    "emoticons": [],
    "keywords": [
        "` + _lt("bowl") + `",
        "` + _lt("noodle") + `",
        "` + _lt("ramen") + `",
        "` + _lt("steaming") + `"
    ],
    "name": "` + _lt("steaming bowl") + `",
    "shortcodes": [
        ":steaming_bowl:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍝",
    "emoticons": [],
    "keywords": [
        "` + _lt("pasta") + `",
        "` + _lt("spaghetti") + `"
    ],
    "name": "` + _lt("spaghetti") + `",
    "shortcodes": [
        ":spaghetti:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍠",
    "emoticons": [],
    "keywords": [
        "` + _lt("potato") + `",
        "` + _lt("roasted") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("roasted sweet potato") + `",
    "shortcodes": [
        ":roasted_sweet_potato:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍢",
    "emoticons": [],
    "keywords": [
        "` + _lt("kebab") + `",
        "` + _lt("oden") + `",
        "` + _lt("seafood") + `",
        "` + _lt("skewer") + `",
        "` + _lt("stick") + `"
    ],
    "name": "` + _lt("oden") + `",
    "shortcodes": [
        ":oden:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍣",
    "emoticons": [
        ":sushi"
    ],
    "keywords": [
        "` + _lt("sushi") + `"
    ],
    "name": "` + _lt("sushi") + `",
    "shortcodes": [
        ":sushi:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍤",
    "emoticons": [],
    "keywords": [
        "` + _lt("battered") + `",
        "` + _lt("fried") + `",
        "` + _lt("prawn") + `",
        "` + _lt("shrimp") + `",
        "` + _lt("tempura") + `"
    ],
    "name": "` + _lt("fried shrimp") + `",
    "shortcodes": [
        ":fried_shrimp:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍥",
    "emoticons": [],
    "keywords": [
        "` + _lt("cake") + `",
        "` + _lt("fish") + `",
        "` + _lt("fish cake with swirl") + `",
        "` + _lt("pastry") + `",
        "` + _lt("swirl") + `",
        "` + _lt("narutomaki") + `"
    ],
    "name": "` + _lt("fish cake with swirl") + `",
    "shortcodes": [
        ":fish_cake_with_swirl:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥮",
    "emoticons": [],
    "keywords": [
        "` + _lt("autumn") + `",
        "` + _lt("festival") + `",
        "` + _lt("moon cake") + `",
        "` + _lt("yuèbǐng") + `"
    ],
    "name": "` + _lt("moon cake") + `",
    "shortcodes": [
        ":moon_cake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍡",
    "emoticons": [],
    "keywords": [
        "` + _lt("dango") + `",
        "` + _lt("dessert") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("skewer") + `",
        "` + _lt("stick") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("dango") + `",
    "shortcodes": [
        ":dango:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥟",
    "emoticons": [],
    "keywords": [
        "` + _lt("dumpling") + `",
        "` + _lt("empanada") + `",
        "` + _lt("gyōza") + `",
        "` + _lt("pastie") + `",
        "` + _lt("samosa") + `",
        "` + _lt("jiaozi") + `",
        "` + _lt("pierogi") + `",
        "` + _lt("potsticker") + `"
    ],
    "name": "` + _lt("dumpling") + `",
    "shortcodes": [
        ":dumpling:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥠",
    "emoticons": [],
    "keywords": [
        "` + _lt("fortune cookie") + `",
        "` + _lt("prophecy") + `"
    ],
    "name": "` + _lt("fortune cookie") + `",
    "shortcodes": [
        ":fortune_cookie:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥡",
    "emoticons": [],
    "keywords": [
        "` + _lt("takeaway container") + `",
        "` + _lt("takeout") + `",
        "` + _lt("oyster pail") + `",
        "` + _lt("takeout box") + `",
        "` + _lt("takeaway box") + `"
    ],
    "name": "` + _lt("takeout box") + `",
    "shortcodes": [
        ":takeout_box:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦀",
    "emoticons": [],
    "keywords": [
        "` + _lt("crab") + `",
        "` + _lt("crustacean") + `",
        "` + _lt("seafood") + `",
        "` + _lt("shellfish") + `",
        "` + _lt("Cancer") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("crab") + `",
    "shortcodes": [
        ":crab:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦞",
    "emoticons": [],
    "keywords": [
        "` + _lt("bisque") + `",
        "` + _lt("claws") + `",
        "` + _lt("lobster") + `",
        "` + _lt("seafood") + `",
        "` + _lt("shellfish") + `"
    ],
    "name": "` + _lt("lobster") + `",
    "shortcodes": [
        ":lobster:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦐",
    "emoticons": [],
    "keywords": [
        "` + _lt("prawn") + `",
        "` + _lt("seafood") + `",
        "` + _lt("shellfish") + `",
        "` + _lt("shrimp") + `",
        "` + _lt("food") + `",
        "` + _lt("small") + `"
    ],
    "name": "` + _lt("shrimp") + `",
    "shortcodes": [
        ":shrimp:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦑",
    "emoticons": [],
    "keywords": [
        "` + _lt("decapod") + `",
        "` + _lt("seafood") + `",
        "` + _lt("squid") + `",
        "` + _lt("food") + `",
        "` + _lt("molusc") + `"
    ],
    "name": "` + _lt("squid") + `",
    "shortcodes": [
        ":squid:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦪",
    "emoticons": [],
    "keywords": [
        "` + _lt("diving") + `",
        "` + _lt("oyster") + `",
        "` + _lt("pearl") + `"
    ],
    "name": "` + _lt("oyster") + `",
    "shortcodes": [
        ":oyster:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍦",
    "emoticons": [],
    "keywords": [
        "` + _lt("cream") + `",
        "` + _lt("dessert") + `",
        "` + _lt("ice cream") + `",
        "` + _lt("soft serve") + `",
        "` + _lt("sweet") + `",
        "` + _lt("ice") + `",
        "` + _lt("icecream") + `",
        "` + _lt("soft") + `"
    ],
    "name": "` + _lt("soft ice cream") + `",
    "shortcodes": [
        ":soft_ice_cream:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍧",
    "emoticons": [],
    "keywords": [
        "` + _lt("dessert") + `",
        "` + _lt("granita") + `",
        "` + _lt("ice") + `",
        "` + _lt("sweet") + `",
        "` + _lt("shaved") + `"
    ],
    "name": "` + _lt("shaved ice") + `",
    "shortcodes": [
        ":shaved_ice:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍨",
    "emoticons": [],
    "keywords": [
        "` + _lt("cream") + `",
        "` + _lt("dessert") + `",
        "` + _lt("ice cream") + `",
        "` + _lt("sweet") + `",
        "` + _lt("ice") + `"
    ],
    "name": "` + _lt("ice cream") + `",
    "shortcodes": [
        ":ice_cream:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍩",
    "emoticons": [],
    "keywords": [
        "` + _lt("breakfast") + `",
        "` + _lt("dessert") + `",
        "` + _lt("donut") + `",
        "` + _lt("doughnut") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("doughnut") + `",
    "shortcodes": [
        ":doughnut:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍪",
    "emoticons": [
        ":cookie"
    ],
    "keywords": [
        "` + _lt("biscuit") + `",
        "` + _lt("cookie") + `",
        "` + _lt("dessert") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("cookie") + `",
    "shortcodes": [
        ":cookie:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🎂",
    "emoticons": [
        ":cake"
    ],
    "keywords": [
        "` + _lt("birthday") + `",
        "` + _lt("cake") + `",
        "` + _lt("celebration") + `",
        "` + _lt("dessert") + `",
        "` + _lt("pastry") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("birthday cake") + `",
    "shortcodes": [
        ":birthday_cake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍰",
    "emoticons": [
        ":cake_part"
    ],
    "keywords": [
        "` + _lt("cake") + `",
        "` + _lt("dessert") + `",
        "` + _lt("pastry") + `",
        "` + _lt("shortcake") + `",
        "` + _lt("slice") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("shortcake") + `",
    "shortcodes": [
        ":shortcake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧁",
    "emoticons": [],
    "keywords": [
        "` + _lt("bakery") + `",
        "` + _lt("cupcake") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("cupcake") + `",
    "shortcodes": [
        ":cupcake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥧",
    "emoticons": [],
    "keywords": [
        "` + _lt("filling") + `",
        "` + _lt("pastry") + `",
        "` + _lt("pie") + `"
    ],
    "name": "` + _lt("pie") + `",
    "shortcodes": [
        ":pie:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍫",
    "emoticons": [],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("chocolate") + `",
        "` + _lt("dessert") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("chocolate bar") + `",
    "shortcodes": [
        ":chocolate_bar:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍬",
    "emoticons": [],
    "keywords": [
        "` + _lt("candy") + `",
        "` + _lt("dessert") + `",
        "` + _lt("sweet") + `",
        "` + _lt("sweets") + `"
    ],
    "name": "` + _lt("candy") + `",
    "shortcodes": [
        ":candy:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍭",
    "emoticons": [],
    "keywords": [
        "` + _lt("candy") + `",
        "` + _lt("dessert") + `",
        "` + _lt("lollipop") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("lollipop") + `",
    "shortcodes": [
        ":lollipop:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍮",
    "emoticons": [],
    "keywords": [
        "` + _lt("baked custard") + `",
        "` + _lt("dessert") + `",
        "` + _lt("pudding") + `",
        "` + _lt("sweet") + `",
        "` + _lt("custard") + `"
    ],
    "name": "` + _lt("custard") + `",
    "shortcodes": [
        ":custard:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍯",
    "emoticons": [],
    "keywords": [
        "` + _lt("honey") + `",
        "` + _lt("honeypot") + `",
        "` + _lt("pot") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("honey pot") + `",
    "shortcodes": [
        ":honey_pot:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍼",
    "emoticons": [],
    "keywords": [
        "` + _lt("baby") + `",
        "` + _lt("bottle") + `",
        "` + _lt("drink") + `",
        "` + _lt("milk") + `"
    ],
    "name": "` + _lt("baby bottle") + `",
    "shortcodes": [
        ":baby_bottle:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥛",
    "emoticons": [],
    "keywords": [
        "` + _lt("drink") + `",
        "` + _lt("glass") + `",
        "` + _lt("glass of milk") + `",
        "` + _lt("milk") + `"
    ],
    "name": "` + _lt("glass of milk") + `",
    "shortcodes": [
        ":glass_of_milk:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "☕",
    "emoticons": [
        ":coffee"
    ],
    "keywords": [
        "` + _lt("beverage") + `",
        "` + _lt("coffee") + `",
        "` + _lt("drink") + `",
        "` + _lt("hot") + `",
        "` + _lt("steaming") + `",
        "` + _lt("tea") + `"
    ],
    "name": "` + _lt("hot beverage") + `",
    "shortcodes": [
        ":hot_beverage:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍵",
    "emoticons": [],
    "keywords": [
        "` + _lt("beverage") + `",
        "` + _lt("cup") + `",
        "` + _lt("drink") + `",
        "` + _lt("tea") + `",
        "` + _lt("teacup") + `",
        "` + _lt("teacup without handle") + `"
    ],
    "name": "` + _lt("teacup without handle") + `",
    "shortcodes": [
        ":teacup_without_handle:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍶",
    "emoticons": [],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("beverage") + `",
        "` + _lt("bottle") + `",
        "` + _lt("cup") + `",
        "` + _lt("drink") + `",
        "` + _lt("sake") + `",
        "` + _lt("saké") + `"
    ],
    "name": "` + _lt("sake") + `",
    "shortcodes": [
        ":sake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍾",
    "emoticons": [],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("bottle") + `",
        "` + _lt("bottle with popping cork") + `",
        "` + _lt("cork") + `",
        "` + _lt("drink") + `",
        "` + _lt("popping") + `"
    ],
    "name": "` + _lt("bottle with popping cork") + `",
    "shortcodes": [
        ":bottle_with_popping_cork:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍷",
    "emoticons": [
        ":wine"
    ],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("beverage") + `",
        "` + _lt("drink") + `",
        "` + _lt("glass") + `",
        "` + _lt("wine") + `"
    ],
    "name": "` + _lt("wine glass") + `",
    "shortcodes": [
        ":wine_glass:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍸",
    "emoticons": [
        ":cocktail"
    ],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("cocktail") + `",
        "` + _lt("drink") + `",
        "` + _lt("glass") + `"
    ],
    "name": "` + _lt("cocktail glass") + `",
    "shortcodes": [
        ":cocktail_glass:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍹",
    "emoticons": [
        ":tropical"
    ],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("drink") + `",
        "` + _lt("tropical") + `"
    ],
    "name": "` + _lt("tropical drink") + `",
    "shortcodes": [
        ":tropical_drink:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍺",
    "emoticons": [
        ":beer"
    ],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("beer") + `",
        "` + _lt("drink") + `",
        "` + _lt("mug") + `"
    ],
    "name": "` + _lt("beer mug") + `",
    "shortcodes": [
        ":beer_mug:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍻",
    "emoticons": [
        ":beers"
    ],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("beer") + `",
        "` + _lt("clink") + `",
        "` + _lt("clinking beer mugs") + `",
        "` + _lt("drink") + `",
        "` + _lt("mug") + `"
    ],
    "name": "` + _lt("clinking beer mugs") + `",
    "shortcodes": [
        ":clinking_beer_mugs:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥂",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebrate") + `",
        "` + _lt("clink") + `",
        "` + _lt("clinking glasses") + `",
        "` + _lt("drink") + `",
        "` + _lt("glass") + `"
    ],
    "name": "` + _lt("clinking glasses") + `",
    "shortcodes": [
        ":clinking_glasses:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥃",
    "emoticons": [],
    "keywords": [
        "` + _lt("glass") + `",
        "` + _lt("liquor") + `",
        "` + _lt("shot") + `",
        "` + _lt("tumbler") + `",
        "` + _lt("whisky") + `"
    ],
    "name": "` + _lt("tumbler glass") + `",
    "shortcodes": [
        ":tumbler_glass:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥤",
    "emoticons": [],
    "keywords": [
        "` + _lt("cup with straw") + `",
        "` + _lt("juice") + `",
        "` + _lt("soda") + `"
    ],
    "name": "` + _lt("cup with straw") + `",
    "shortcodes": [
        ":cup_with_straw:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧃",
    "emoticons": [],
    "keywords": [
        "` + _lt("drink carton") + `",
        "` + _lt("juice box") + `",
        "` + _lt("popper") + `",
        "` + _lt("beverage") + `",
        "` + _lt("box") + `",
        "` + _lt("juice") + `",
        "` + _lt("straw") + `",
        "` + _lt("sweet") + `"
    ],
    "name": "` + _lt("beverage box") + `",
    "shortcodes": [
        ":beverage_box:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧉",
    "emoticons": [],
    "keywords": [
        "` + _lt("drink") + `",
        "` + _lt("mate") + `",
        "` + _lt("maté") + `"
    ],
    "name": "` + _lt("mate") + `",
    "shortcodes": [
        ":mate:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧊",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("ice") + `",
        "` + _lt("ice cube") + `",
        "` + _lt("iceberg") + `"
    ],
    "name": "` + _lt("ice") + `",
    "shortcodes": [
        ":ice:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥢",
    "emoticons": [],
    "keywords": [
        "` + _lt("chopsticks") + `",
        "` + _lt("pair of chopsticks") + `",
        "` + _lt("hashi") + `"
    ],
    "name": "` + _lt("chopsticks") + `",
    "shortcodes": [
        ":chopsticks:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍽️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cooking") + `",
        "` + _lt("fork") + `",
        "` + _lt("fork and knife with plate") + `",
        "` + _lt("knife") + `",
        "` + _lt("plate") + `"
    ],
    "name": "` + _lt("fork and knife with plate") + `",
    "shortcodes": [
        ":fork_and_knife_with_plate:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍴",
    "emoticons": [],
    "keywords": [
        "` + _lt("cooking") + `",
        "` + _lt("cutlery") + `",
        "` + _lt("fork") + `",
        "` + _lt("fork and knife") + `",
        "` + _lt("knife") + `",
        "` + _lt("knife and fork") + `"
    ],
    "name": "` + _lt("fork and knife") + `",
    "shortcodes": [
        ":fork_and_knife:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥄",
    "emoticons": [],
    "keywords": [
        "` + _lt("spoon") + `",
        "` + _lt("tableware") + `"
    ],
    "name": "` + _lt("spoon") + `",
    "shortcodes": [
        ":spoon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🔪",
    "emoticons": [],
    "keywords": [
        "` + _lt("cooking") + `",
        "` + _lt("hocho") + `",
        "` + _lt("kitchen knife") + `",
        "` + _lt("knife") + `",
        "` + _lt("tool") + `",
        "` + _lt("weapon") + `"
    ],
    "name": "` + _lt("kitchen knife") + `",
    "shortcodes": [
        ":kitchen_knife:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🏺",
    "emoticons": [],
    "keywords": [
        "` + _lt("amphora") + `",
        "` + _lt("Aquarius") + `",
        "` + _lt("cooking") + `",
        "` + _lt("drink") + `",
        "` + _lt("jug") + `",
        "` + _lt("zodiac") + `",
        "` + _lt("jar") + `"
    ],
    "name": "` + _lt("amphora") + `",
    "shortcodes": [
        ":amphora:"
    ]
},`;

const emojisData5 = `{
    "category": "Travel & Places",
    "codepoints": "🌍",
    "emoticons": [],
    "keywords": [
        "` + _lt("Africa") + `",
        "` + _lt("earth") + `",
        "` + _lt("Europe") + `",
        "` + _lt("globe") + `",
        "` + _lt("globe showing Europe-Africa") + `",
        "` + _lt("world") + `"
    ],
    "name": "` + _lt("globe showing Europe-Africa") + `",
    "shortcodes": [
        ":globe_showing_Europe-Africa:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌎",
    "emoticons": [],
    "keywords": [
        "` + _lt("Americas") + `",
        "` + _lt("earth") + `",
        "` + _lt("globe") + `",
        "` + _lt("globe showing Americas") + `",
        "` + _lt("world") + `"
    ],
    "name": "` + _lt("globe showing Americas") + `",
    "shortcodes": [
        ":globe_showing_Americas:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌏",
    "emoticons": [],
    "keywords": [
        "` + _lt("Asia") + `",
        "` + _lt("Australia") + `",
        "` + _lt("earth") + `",
        "` + _lt("globe") + `",
        "` + _lt("globe showing Asia-Australia") + `",
        "` + _lt("world") + `"
    ],
    "name": "` + _lt("globe showing Asia-Australia") + `",
    "shortcodes": [
        ":globe_showing_Asia-Australia:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌐",
    "emoticons": [],
    "keywords": [
        "` + _lt("earth") + `",
        "` + _lt("globe") + `",
        "` + _lt("globe with meridians") + `",
        "` + _lt("meridians") + `",
        "` + _lt("world") + `"
    ],
    "name": "` + _lt("globe with meridians") + `",
    "shortcodes": [
        ":globe_with_meridians:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗺️",
    "emoticons": [],
    "keywords": [
        "` + _lt("map") + `",
        "` + _lt("world") + `"
    ],
    "name": "` + _lt("world map") + `",
    "shortcodes": [
        ":world_map:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗾",
    "emoticons": [],
    "keywords": [
        "` + _lt("Japan") + `",
        "` + _lt("map") + `",
        "` + _lt("map of Japan") + `"
    ],
    "name": "` + _lt("map of Japan") + `",
    "shortcodes": [
        ":map_of_Japan:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🧭",
    "emoticons": [],
    "keywords": [
        "` + _lt("compass") + `",
        "` + _lt("magnetic") + `",
        "` + _lt("navigation") + `",
        "` + _lt("orienteering") + `"
    ],
    "name": "` + _lt("compass") + `",
    "shortcodes": [
        ":compass:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏔️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("mountain") + `",
        "` + _lt("snow") + `",
        "` + _lt("snow-capped mountain") + `"
    ],
    "name": "` + _lt("snow-capped mountain") + `",
    "shortcodes": [
        ":snow-capped_mountain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛰️",
    "emoticons": [],
    "keywords": [
        "` + _lt("mountain") + `"
    ],
    "name": "` + _lt("mountain") + `",
    "shortcodes": [
        ":mountain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌋",
    "emoticons": [],
    "keywords": [
        "` + _lt("eruption") + `",
        "` + _lt("mountain") + `",
        "` + _lt("volcano") + `"
    ],
    "name": "` + _lt("volcano") + `",
    "shortcodes": [
        ":volcano:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗻",
    "emoticons": [],
    "keywords": [
        "` + _lt("Fuji") + `",
        "` + _lt("mount Fuji") + `",
        "` + _lt("mountain") + `",
        "` + _lt("fuji") + `",
        "` + _lt("mount fuji") + `",
        "` + _lt("Mount Fuji") + `"
    ],
    "name": "` + _lt("mount fuji") + `",
    "shortcodes": [
        ":mount_fuji:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏕️",
    "emoticons": [],
    "keywords": [
        "` + _lt("camping") + `"
    ],
    "name": "` + _lt("camping") + `",
    "shortcodes": [
        ":camping:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏖️",
    "emoticons": [],
    "keywords": [
        "` + _lt("beach") + `",
        "` + _lt("beach with umbrella") + `",
        "` + _lt("umbrella") + `"
    ],
    "name": "` + _lt("beach with umbrella") + `",
    "shortcodes": [
        ":beach_with_umbrella:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏜️",
    "emoticons": [],
    "keywords": [
        "` + _lt("desert") + `"
    ],
    "name": "` + _lt("desert") + `",
    "shortcodes": [
        ":desert:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏝️",
    "emoticons": [],
    "keywords": [
        "` + _lt("desert") + `",
        "` + _lt("island") + `"
    ],
    "name": "` + _lt("desert island") + `",
    "shortcodes": [
        ":desert_island:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏞️",
    "emoticons": [],
    "keywords": [
        "` + _lt("national park") + `",
        "` + _lt("park") + `"
    ],
    "name": "` + _lt("national park") + `",
    "shortcodes": [
        ":national_park:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏟️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arena") + `",
        "` + _lt("stadium") + `"
    ],
    "name": "` + _lt("stadium") + `",
    "shortcodes": [
        ":stadium:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏛️",
    "emoticons": [],
    "keywords": [
        "` + _lt("classical") + `",
        "` + _lt("classical building") + `",
        "` + _lt("column") + `"
    ],
    "name": "` + _lt("classical building") + `",
    "shortcodes": [
        ":classical_building:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏗️",
    "emoticons": [],
    "keywords": [
        "` + _lt("building construction") + `",
        "` + _lt("construction") + `"
    ],
    "name": "` + _lt("building construction") + `",
    "shortcodes": [
        ":building_construction:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🧱",
    "emoticons": [],
    "keywords": [
        "` + _lt("brick") + `",
        "` + _lt("bricks") + `",
        "` + _lt("clay") + `",
        "` + _lt("mortar") + `",
        "` + _lt("wall") + `"
    ],
    "name": "` + _lt("brick") + `",
    "shortcodes": [
        ":brick:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏘️",
    "emoticons": [],
    "keywords": [
        "` + _lt("houses") + `"
    ],
    "name": "` + _lt("houses") + `",
    "shortcodes": [
        ":houses:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏚️",
    "emoticons": [],
    "keywords": [
        "` + _lt("derelict") + `",
        "` + _lt("house") + `"
    ],
    "name": "` + _lt("derelict house") + `",
    "shortcodes": [
        ":derelict_house:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏠",
    "emoticons": [],
    "keywords": [
        "` + _lt("home") + `",
        "` + _lt("house") + `"
    ],
    "name": "` + _lt("house") + `",
    "shortcodes": [
        ":house:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏡",
    "emoticons": [],
    "keywords": [
        "` + _lt("garden") + `",
        "` + _lt("home") + `",
        "` + _lt("house") + `",
        "` + _lt("house with garden") + `"
    ],
    "name": "` + _lt("house with garden") + `",
    "shortcodes": [
        ":house_with_garden:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏢",
    "emoticons": [],
    "keywords": [
        "` + _lt("building") + `",
        "` + _lt("office building") + `"
    ],
    "name": "` + _lt("office building") + `",
    "shortcodes": [
        ":office_building:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏣",
    "emoticons": [],
    "keywords": [
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese post office") + `",
        "` + _lt("post") + `"
    ],
    "name": "` + _lt("Japanese post office") + `",
    "shortcodes": [
        ":Japanese_post_office:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏤",
    "emoticons": [],
    "keywords": [
        "` + _lt("European") + `",
        "` + _lt("post") + `",
        "` + _lt("post office") + `"
    ],
    "name": "` + _lt("post office") + `",
    "shortcodes": [
        ":post_office:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏥",
    "emoticons": [],
    "keywords": [
        "` + _lt("doctor") + `",
        "` + _lt("hospital") + `",
        "` + _lt("medicine") + `"
    ],
    "name": "` + _lt("hospital") + `",
    "shortcodes": [
        ":hospital:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏦",
    "emoticons": [],
    "keywords": [
        "` + _lt("bank") + `",
        "` + _lt("building") + `"
    ],
    "name": "` + _lt("bank") + `",
    "shortcodes": [
        ":bank:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏨",
    "emoticons": [],
    "keywords": [
        "` + _lt("building") + `",
        "` + _lt("hotel") + `"
    ],
    "name": "` + _lt("hotel") + `",
    "shortcodes": [
        ":hotel:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏩",
    "emoticons": [],
    "keywords": [
        "` + _lt("hotel") + `",
        "` + _lt("love") + `"
    ],
    "name": "` + _lt("love hotel") + `",
    "shortcodes": [
        ":love_hotel:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏪",
    "emoticons": [],
    "keywords": [
        "` + _lt("convenience") + `",
        "` + _lt("store") + `",
        "` + _lt("dépanneur") + `"
    ],
    "name": "` + _lt("convenience store") + `",
    "shortcodes": [
        ":convenience_store:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏫",
    "emoticons": [],
    "keywords": [
        "` + _lt("building") + `",
        "` + _lt("school") + `"
    ],
    "name": "` + _lt("school") + `",
    "shortcodes": [
        ":school:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏬",
    "emoticons": [],
    "keywords": [
        "` + _lt("department") + `",
        "` + _lt("store") + `"
    ],
    "name": "` + _lt("department store") + `",
    "shortcodes": [
        ":department_store:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏭",
    "emoticons": [],
    "keywords": [
        "` + _lt("building") + `",
        "` + _lt("factory") + `"
    ],
    "name": "` + _lt("factory") + `",
    "shortcodes": [
        ":factory:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏯",
    "emoticons": [],
    "keywords": [
        "` + _lt("castle") + `",
        "` + _lt("Japanese") + `"
    ],
    "name": "` + _lt("Japanese castle") + `",
    "shortcodes": [
        ":Japanese_castle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏰",
    "emoticons": [],
    "keywords": [
        "` + _lt("castle") + `",
        "` + _lt("European") + `"
    ],
    "name": "` + _lt("castle") + `",
    "shortcodes": [
        ":castle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "💒",
    "emoticons": [],
    "keywords": [
        "` + _lt("chapel") + `",
        "` + _lt("romance") + `",
        "` + _lt("wedding") + `"
    ],
    "name": "` + _lt("wedding") + `",
    "shortcodes": [
        ":wedding:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗼",
    "emoticons": [],
    "keywords": [
        "` + _lt("Tokyo") + `",
        "` + _lt("tower") + `",
        "` + _lt("Tower") + `"
    ],
    "name": "` + _lt("Tokyo tower") + `",
    "shortcodes": [
        ":Tokyo_ltower:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗽",
    "emoticons": [],
    "keywords": [
        "` + _lt("liberty") + `",
        "` + _lt("statue") + `",
        "` + _lt("Statue of Liberty") + `",
        "` + _lt("Liberty") + `",
        "` + _lt("Statue") + `"
    ],
    "name": "` + _lt("Statue of Liberty") + `",
    "shortcodes": [
        ":Statue_of_Liberty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛪",
    "emoticons": [],
    "keywords": [
        "` + _lt("Christian") + `",
        "` + _lt("church") + `",
        "` + _lt("cross") + `",
        "` + _lt("religion") + `"
    ],
    "name": "` + _lt("church") + `",
    "shortcodes": [
        ":church:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕌",
    "emoticons": [],
    "keywords": [
        "` + _lt("Islam") + `",
        "` + _lt("mosque") + `",
        "` + _lt("Muslim") + `",
        "` + _lt("religion") + `",
        "` + _lt("islam") + `"
    ],
    "name": "` + _lt("mosque") + `",
    "shortcodes": [
        ":mosque:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛕",
    "emoticons": [],
    "keywords": [
        "` + _lt("hindu") + `",
        "` + _lt("temple") + `",
        "` + _lt("Hindu") + `"
    ],
    "name": "` + _lt("hindu temple") + `",
    "shortcodes": [
        ":hindu_ltemple:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕍",
    "emoticons": [],
    "keywords": [
        "` + _lt("Jew") + `",
        "` + _lt("Jewish") + `",
        "` + _lt("religion") + `",
        "` + _lt("synagogue") + `",
        "` + _lt("temple") + `",
        "` + _lt("shul") + `"
    ],
    "name": "` + _lt("synagogue") + `",
    "shortcodes": [
        ":synagogue:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛩️",
    "emoticons": [],
    "keywords": [
        "` + _lt("religion") + `",
        "` + _lt("Shinto") + `",
        "` + _lt("shrine") + `",
        "` + _lt("shinto") + `"
    ],
    "name": "` + _lt("shinto shrine") + `",
    "shortcodes": [
        ":shinto_shrine:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕋",
    "emoticons": [],
    "keywords": [
        "` + _lt("Islam") + `",
        "` + _lt("Kaaba") + `",
        "` + _lt("Muslim") + `",
        "` + _lt("religion") + `",
        "` + _lt("islam") + `",
        "` + _lt("kaaba") + `"
    ],
    "name": "` + _lt("kaaba") + `",
    "shortcodes": [
        ":kaaba:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛲",
    "emoticons": [],
    "keywords": [
        "` + _lt("fountain") + `"
    ],
    "name": "` + _lt("fountain") + `",
    "shortcodes": [
        ":fountain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛺",
    "emoticons": [],
    "keywords": [
        "` + _lt("camping") + `",
        "` + _lt("tent") + `"
    ],
    "name": "` + _lt("tent") + `",
    "shortcodes": [
        ":tent:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌁",
    "emoticons": [],
    "keywords": [
        "` + _lt("fog") + `",
        "` + _lt("foggy") + `"
    ],
    "name": "` + _lt("foggy") + `",
    "shortcodes": [
        ":foggy:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌃",
    "emoticons": [],
    "keywords": [
        "` + _lt("night") + `",
        "` + _lt("night with stars") + `",
        "` + _lt("star") + `"
    ],
    "name": "` + _lt("night with stars") + `",
    "shortcodes": [
        ":night_with_stars:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏙️",
    "emoticons": [],
    "keywords": [
        "` + _lt("city") + `",
        "` + _lt("cityscape") + `"
    ],
    "name": "` + _lt("cityscape") + `",
    "shortcodes": [
        ":cityscape:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌄",
    "emoticons": [],
    "keywords": [
        "` + _lt("morning") + `",
        "` + _lt("mountain") + `",
        "` + _lt("sun") + `",
        "` + _lt("sunrise") + `",
        "` + _lt("sunrise over mountains") + `"
    ],
    "name": "` + _lt("sunrise over mountains") + `",
    "shortcodes": [
        ":sunrise_over_mountains:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌅",
    "emoticons": [],
    "keywords": [
        "` + _lt("morning") + `",
        "` + _lt("sun") + `",
        "` + _lt("sunrise") + `"
    ],
    "name": "` + _lt("sunrise") + `",
    "shortcodes": [
        ":sunrise:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌆",
    "emoticons": [],
    "keywords": [
        "` + _lt("city") + `",
        "` + _lt("cityscape at dusk") + `",
        "` + _lt("dusk") + `",
        "` + _lt("evening") + `",
        "` + _lt("landscape") + `",
        "` + _lt("sunset") + `"
    ],
    "name": "` + _lt("cityscape at dusk") + `",
    "shortcodes": [
        ":cityscape_at_dusk:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌇",
    "emoticons": [],
    "keywords": [
        "` + _lt("dusk") + `",
        "` + _lt("sun") + `",
        "` + _lt("sunset") + `"
    ],
    "name": "` + _lt("sunset") + `",
    "shortcodes": [
        ":sunset:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌉",
    "emoticons": [],
    "keywords": [
        "` + _lt("bridge") + `",
        "` + _lt("bridge at night") + `",
        "` + _lt("night") + `"
    ],
    "name": "` + _lt("bridge at night") + `",
    "shortcodes": [
        ":bridge_at_night:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "♨️",
    "emoticons": [],
    "keywords": [
        "` + _lt("hot") + `",
        "` + _lt("hotsprings") + `",
        "` + _lt("springs") + `",
        "` + _lt("steaming") + `"
    ],
    "name": "` + _lt("hot springs") + `",
    "shortcodes": [
        ":hot_springs:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🎠",
    "emoticons": [],
    "keywords": [
        "` + _lt("carousel") + `",
        "` + _lt("horse") + `",
        "` + _lt("merry-go-round") + `"
    ],
    "name": "` + _lt("carousel horse") + `",
    "shortcodes": [
        ":carousel_horse:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🎡",
    "emoticons": [],
    "keywords": [
        "` + _lt("amusement park") + `",
        "` + _lt("ferris") + `",
        "` + _lt("wheel") + `",
        "` + _lt("Ferris") + `",
        "` + _lt("theme park") + `"
    ],
    "name": "` + _lt("ferris wheel") + `",
    "shortcodes": [
        ":ferris_wheel:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🎢",
    "emoticons": [],
    "keywords": [
        "` + _lt("amusement park") + `",
        "` + _lt("coaster") + `",
        "` + _lt("roller") + `"
    ],
    "name": "` + _lt("roller coaster") + `",
    "shortcodes": [
        ":roller_coaster:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "💈",
    "emoticons": [],
    "keywords": [
        "` + _lt("barber") + `",
        "` + _lt("haircut") + `",
        "` + _lt("pole") + `"
    ],
    "name": "` + _lt("barber pole") + `",
    "shortcodes": [
        ":barber_pole:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🎪",
    "emoticons": [],
    "keywords": [
        "` + _lt("big top") + `",
        "` + _lt("circus") + `",
        "` + _lt("tent") + `"
    ],
    "name": "` + _lt("circus tent") + `",
    "shortcodes": [
        ":circus_ltent:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚂",
    "emoticons": [],
    "keywords": [
        "` + _lt("engine") + `",
        "` + _lt("locomotive") + `",
        "` + _lt("railway") + `",
        "` + _lt("steam") + `",
        "` + _lt("train") + `"
    ],
    "name": "` + _lt("locomotive") + `",
    "shortcodes": [
        ":locomotive:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚃",
    "emoticons": [],
    "keywords": [
        "` + _lt("car") + `",
        "` + _lt("electric") + `",
        "` + _lt("railway") + `",
        "` + _lt("train") + `",
        "` + _lt("tram") + `",
        "` + _lt("trolley bus") + `",
        "` + _lt("trolleybus") + `",
        "` + _lt("railway carriage") + `"
    ],
    "name": "` + _lt("railway car") + `",
    "shortcodes": [
        ":railway_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚄",
    "emoticons": [],
    "keywords": [
        "` + _lt("high-speed train") + `",
        "` + _lt("railway") + `",
        "` + _lt("shinkansen") + `",
        "` + _lt("speed") + `",
        "` + _lt("train") + `",
        "` + _lt("Shinkansen") + `"
    ],
    "name": "` + _lt("high-speed train") + `",
    "shortcodes": [
        ":high-speed_ltrain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚅",
    "emoticons": [],
    "keywords": [
        "` + _lt("bullet") + `",
        "` + _lt("railway") + `",
        "` + _lt("shinkansen") + `",
        "` + _lt("speed") + `",
        "` + _lt("train") + `",
        "` + _lt("Shinkansen") + `"
    ],
    "name": "` + _lt("bullet train") + `",
    "shortcodes": [
        ":bullet_ltrain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚆",
    "emoticons": [],
    "keywords": [
        "` + _lt("railway") + `",
        "` + _lt("train") + `"
    ],
    "name": "` + _lt("train") + `",
    "shortcodes": [
        ":train:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚇",
    "emoticons": [],
    "keywords": [
        "` + _lt("metro") + `",
        "` + _lt("subway") + `"
    ],
    "name": "` + _lt("metro") + `",
    "shortcodes": [
        ":metro:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚈",
    "emoticons": [],
    "keywords": [
        "` + _lt("light rail") + `",
        "` + _lt("railway") + `"
    ],
    "name": "` + _lt("light rail") + `",
    "shortcodes": [
        ":light_rail:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚉",
    "emoticons": [],
    "keywords": [
        "` + _lt("railway") + `",
        "` + _lt("station") + `",
        "` + _lt("train") + `"
    ],
    "name": "` + _lt("station") + `",
    "shortcodes": [
        ":station:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚊",
    "emoticons": [],
    "keywords": [
        "` + _lt("light rail") + `",
        "` + _lt("oncoming") + `",
        "` + _lt("oncoming light rail") + `",
        "` + _lt("tram") + `",
        "` + _lt("trolleybus") + `",
        "` + _lt("car") + `",
        "` + _lt("streetcar") + `",
        "` + _lt("tramcar") + `",
        "` + _lt("trolley") + `",
        "` + _lt("trolley bus") + `"
    ],
    "name": "` + _lt("tram") + `",
    "shortcodes": [
        ":tram:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚝",
    "emoticons": [],
    "keywords": [
        "` + _lt("monorail") + `",
        "` + _lt("vehicle") + `"
    ],
    "name": "` + _lt("monorail") + `",
    "shortcodes": [
        ":monorail:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚞",
    "emoticons": [],
    "keywords": [
        "` + _lt("car") + `",
        "` + _lt("mountain") + `",
        "` + _lt("railway") + `"
    ],
    "name": "` + _lt("mountain railway") + `",
    "shortcodes": [
        ":mountain_railway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚋",
    "emoticons": [],
    "keywords": [
        "` + _lt("car") + `",
        "` + _lt("tram") + `",
        "` + _lt("trolley bus") + `",
        "` + _lt("trolleybus") + `",
        "` + _lt("streetcar") + `",
        "` + _lt("tramcar") + `",
        "` + _lt("trolley") + `"
    ],
    "name": "` + _lt("tram car") + `",
    "shortcodes": [
        ":tram_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚌",
    "emoticons": [],
    "keywords": [
        "` + _lt("bus") + `",
        "` + _lt("vehicle") + `"
    ],
    "name": "` + _lt("bus") + `",
    "shortcodes": [
        ":bus:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚍",
    "emoticons": [],
    "keywords": [
        "` + _lt("bus") + `",
        "` + _lt("oncoming") + `"
    ],
    "name": "` + _lt("oncoming bus") + `",
    "shortcodes": [
        ":oncoming_bus:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚎",
    "emoticons": [],
    "keywords": [
        "` + _lt("bus") + `",
        "` + _lt("tram") + `",
        "` + _lt("trolley") + `",
        "` + _lt("trolleybus") + `",
        "` + _lt("streetcar") + `"
    ],
    "name": "` + _lt("trolleybus") + `",
    "shortcodes": [
        ":trolleybus:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚐",
    "emoticons": [],
    "keywords": [
        "` + _lt("bus") + `",
        "` + _lt("minibus") + `"
    ],
    "name": "` + _lt("minibus") + `",
    "shortcodes": [
        ":minibus:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚑",
    "emoticons": [],
    "keywords": [
        "` + _lt("ambulance") + `",
        "` + _lt("vehicle") + `"
    ],
    "name": "` + _lt("ambulance") + `",
    "shortcodes": [
        ":ambulance:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚒",
    "emoticons": [],
    "keywords": [
        "` + _lt("engine") + `",
        "` + _lt("fire") + `",
        "` + _lt("truck") + `"
    ],
    "name": "` + _lt("fire engine") + `",
    "shortcodes": [
        ":fire_engine:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚓",
    "emoticons": [],
    "keywords": [
        "` + _lt("car") + `",
        "` + _lt("patrol") + `",
        "` + _lt("police") + `"
    ],
    "name": "` + _lt("police car") + `",
    "shortcodes": [
        ":police_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚔",
    "emoticons": [],
    "keywords": [
        "` + _lt("car") + `",
        "` + _lt("oncoming") + `",
        "` + _lt("police") + `"
    ],
    "name": "` + _lt("oncoming police car") + `",
    "shortcodes": [
        ":oncoming_police_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚕",
    "emoticons": [],
    "keywords": [
        "` + _lt("taxi") + `",
        "` + _lt("vehicle") + `"
    ],
    "name": "` + _lt("taxi") + `",
    "shortcodes": [
        ":taxi:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚖",
    "emoticons": [],
    "keywords": [
        "` + _lt("oncoming") + `",
        "` + _lt("taxi") + `"
    ],
    "name": "` + _lt("oncoming taxi") + `",
    "shortcodes": [
        ":oncoming_ltaxi:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚗",
    "emoticons": [],
    "keywords": [
        "` + _lt("automobile") + `",
        "` + _lt("car") + `"
    ],
    "name": "` + _lt("automobile") + `",
    "shortcodes": [
        ":automobile:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚘",
    "emoticons": [],
    "keywords": [
        "` + _lt("automobile") + `",
        "` + _lt("car") + `",
        "` + _lt("oncoming") + `"
    ],
    "name": "` + _lt("oncoming automobile") + `",
    "shortcodes": [
        ":oncoming_automobile:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚙",
    "emoticons": [],
    "keywords": [
        "` + _lt("4WD") + `",
        "` + _lt("four-wheel drive") + `",
        "` + _lt("recreational") + `",
        "` + _lt("sport utility") + `",
        "` + _lt("sport utility vehicle") + `",
        "` + _lt("4x4") + `",
        "` + _lt("off-road vehicle") + `",
        "` + _lt("SUV") + `"
    ],
    "name": "` + _lt("sport utility vehicle") + `",
    "shortcodes": [
        ":sport_utility_vehicle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚚",
    "emoticons": [],
    "keywords": [
        "` + _lt("delivery") + `",
        "` + _lt("truck") + `"
    ],
    "name": "` + _lt("delivery truck") + `",
    "shortcodes": [
        ":delivery_ltruck:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚛",
    "emoticons": [],
    "keywords": [
        "` + _lt("articulated truck") + `",
        "` + _lt("lorry") + `",
        "` + _lt("semi") + `",
        "` + _lt("truck") + `",
        "` + _lt("articulated lorry") + `"
    ],
    "name": "` + _lt("articulated lorry") + `",
    "shortcodes": [
        ":articulated_lorry:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚜",
    "emoticons": [],
    "keywords": [
        "` + _lt("tractor") + `",
        "` + _lt("vehicle") + `"
    ],
    "name": "` + _lt("tractor") + `",
    "shortcodes": [
        ":tractor:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏎️",
    "emoticons": [],
    "keywords": [
        "` + _lt("car") + `",
        "` + _lt("racing") + `"
    ],
    "name": "` + _lt("racing car") + `",
    "shortcodes": [
        ":racing_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏍️",
    "emoticons": [],
    "keywords": [
        "` + _lt("motorcycle") + `",
        "` + _lt("racing") + `"
    ],
    "name": "` + _lt("motorcycle") + `",
    "shortcodes": [
        ":motorcycle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛵",
    "emoticons": [],
    "keywords": [
        "` + _lt("motor") + `",
        "` + _lt("scooter") + `"
    ],
    "name": "` + _lt("motor scooter") + `",
    "shortcodes": [
        ":motor_scooter:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🦽",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("manual wheelchair") + `"
    ],
    "name": "` + _lt("manual wheelchair") + `",
    "shortcodes": [
        ":manual_wheelchair:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🦼",
    "emoticons": [],
    "keywords": [
        "` + _lt("mobility scooter") + `",
        "` + _lt("accessibility") + `",
        "` + _lt("motorized wheelchair") + `",
        "` + _lt("powered wheelchair") + `"
    ],
    "name": "` + _lt("motorized wheelchair") + `",
    "shortcodes": [
        ":motorized_wheelchair:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛺",
    "emoticons": [],
    "keywords": [
        "` + _lt("auto rickshaw") + `",
        "` + _lt("tuk tuk") + `",
        "` + _lt("tuk-tuk") + `",
        "` + _lt("tuktuk") + `"
    ],
    "name": "` + _lt("auto rickshaw") + `",
    "shortcodes": [
        ":auto_rickshaw:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚲",
    "emoticons": [
        ":bike"
    ],
    "keywords": [
        "` + _lt("bicycle") + `",
        "` + _lt("bike") + `"
    ],
    "name": "` + _lt("bicycle") + `",
    "shortcodes": [
        ":bicycle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛴",
    "emoticons": [],
    "keywords": [
        "` + _lt("kick") + `",
        "` + _lt("scooter") + `"
    ],
    "name": "` + _lt("kick scooter") + `",
    "shortcodes": [
        ":kick_scooter:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛹",
    "emoticons": [],
    "keywords": [
        "` + _lt("board") + `",
        "` + _lt("skateboard") + `"
    ],
    "name": "` + _lt("skateboard") + `",
    "shortcodes": [
        ":skateboard:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚏",
    "emoticons": [],
    "keywords": [
        "` + _lt("bus") + `",
        "` + _lt("stop") + `",
        "` + _lt("busstop") + `"
    ],
    "name": "` + _lt("bus stop") + `",
    "shortcodes": [
        ":bus_stop:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛣️",
    "emoticons": [],
    "keywords": [
        "` + _lt("freeway") + `",
        "` + _lt("highway") + `",
        "` + _lt("road") + `",
        "` + _lt("motorway") + `"
    ],
    "name": "` + _lt("motorway") + `",
    "shortcodes": [
        ":motorway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛤️",
    "emoticons": [],
    "keywords": [
        "` + _lt("railway") + `",
        "` + _lt("railway track") + `",
        "` + _lt("train") + `"
    ],
    "name": "` + _lt("railway track") + `",
    "shortcodes": [
        ":railway_ltrack:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛢️",
    "emoticons": [],
    "keywords": [
        "` + _lt("drum") + `",
        "` + _lt("oil") + `"
    ],
    "name": "` + _lt("oil drum") + `",
    "shortcodes": [
        ":oil_drum:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛽",
    "emoticons": [],
    "keywords": [
        "` + _lt("diesel") + `",
        "` + _lt("fuel") + `",
        "` + _lt("gas") + `",
        "` + _lt("petrol pump") + `",
        "` + _lt("pump") + `",
        "` + _lt("station") + `",
        "` + _lt("fuelpump") + `"
    ],
    "name": "` + _lt("fuel pump") + `",
    "shortcodes": [
        ":fuel_pump:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚨",
    "emoticons": [],
    "keywords": [
        "` + _lt("beacon") + `",
        "` + _lt("car") + `",
        "` + _lt("light") + `",
        "` + _lt("police") + `",
        "` + _lt("revolving") + `"
    ],
    "name": "` + _lt("police car light") + `",
    "shortcodes": [
        ":police_car_light:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚥",
    "emoticons": [],
    "keywords": [
        "` + _lt("horizontal traffic lights") + `",
        "` + _lt("lights") + `",
        "` + _lt("signal") + `",
        "` + _lt("traffic") + `",
        "` + _lt("horizontal traffic light") + `",
        "` + _lt("light") + `"
    ],
    "name": "` + _lt("horizontal traffic light") + `",
    "shortcodes": [
        ":horizontal_ltraffic_light:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚦",
    "emoticons": [],
    "keywords": [
        "` + _lt("lights") + `",
        "` + _lt("signal") + `",
        "` + _lt("traffic") + `",
        "` + _lt("vertical traffic lights") + `",
        "` + _lt("light") + `",
        "` + _lt("vertical traffic light") + `"
    ],
    "name": "` + _lt("vertical traffic light") + `",
    "shortcodes": [
        ":vertical_ltraffic_light:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛑",
    "emoticons": [],
    "keywords": [
        "` + _lt("octagonal") + `",
        "` + _lt("sign") + `",
        "` + _lt("stop") + `"
    ],
    "name": "` + _lt("stop sign") + `",
    "shortcodes": [
        ":stop_sign:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚧",
    "emoticons": [],
    "keywords": [
        "` + _lt("barrier") + `",
        "` + _lt("construction") + `"
    ],
    "name": "` + _lt("construction") + `",
    "shortcodes": [
        ":construction:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⚓",
    "emoticons": [],
    "keywords": [
        "` + _lt("anchor") + `",
        "` + _lt("ship") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("anchor") + `",
    "shortcodes": [
        ":anchor:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛵",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("resort") + `",
        "` + _lt("sailboat") + `",
        "` + _lt("sea") + `",
        "` + _lt("yacht") + `"
    ],
    "name": "` + _lt("sailboat") + `",
    "shortcodes": [
        ":sailboat:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛶",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("canoe") + `"
    ],
    "name": "` + _lt("canoe") + `",
    "shortcodes": [
        ":canoe:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚤",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("speedboat") + `"
    ],
    "name": "` + _lt("speedboat") + `",
    "shortcodes": [
        ":speedboat:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛳️",
    "emoticons": [],
    "keywords": [
        "` + _lt("passenger") + `",
        "` + _lt("ship") + `"
    ],
    "name": "` + _lt("passenger ship") + `",
    "shortcodes": [
        ":passenger_ship:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛴️",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("ferry") + `",
        "` + _lt("passenger") + `"
    ],
    "name": "` + _lt("ferry") + `",
    "shortcodes": [
        ":ferry:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛥️",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("motor boat") + `",
        "` + _lt("motorboat") + `"
    ],
    "name": "` + _lt("motor boat") + `",
    "shortcodes": [
        ":motor_boat:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚢",
    "emoticons": [],
    "keywords": [
        "` + _lt("boat") + `",
        "` + _lt("passenger") + `",
        "` + _lt("ship") + `"
    ],
    "name": "` + _lt("ship") + `",
    "shortcodes": [
        ":ship:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "✈️",
    "emoticons": [],
    "keywords": [
        "` + _lt("aeroplane") + `",
        "` + _lt("airplane") + `"
    ],
    "name": "` + _lt("airplane") + `",
    "shortcodes": [
        ":airplane:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛩️",
    "emoticons": [],
    "keywords": [
        "` + _lt("aeroplane") + `",
        "` + _lt("airplane") + `",
        "` + _lt("small airplane") + `"
    ],
    "name": "` + _lt("small airplane") + `",
    "shortcodes": [
        ":small_airplane:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛫",
    "emoticons": [],
    "keywords": [
        "` + _lt("aeroplane") + `",
        "` + _lt("airplane") + `",
        "` + _lt("check-in") + `",
        "` + _lt("departure") + `",
        "` + _lt("departures") + `",
        "` + _lt("take-off") + `"
    ],
    "name": "` + _lt("airplane departure") + `",
    "shortcodes": [
        ":airplane_departure:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛬",
    "emoticons": [],
    "keywords": [
        "` + _lt("aeroplane") + `",
        "` + _lt("airplane") + `",
        "` + _lt("airplane arrival") + `",
        "` + _lt("arrivals") + `",
        "` + _lt("arriving") + `",
        "` + _lt("landing") + `"
    ],
    "name": "` + _lt("airplane arrival") + `",
    "shortcodes": [
        ":airplane_arrival:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🪂",
    "emoticons": [],
    "keywords": [
        "` + _lt("hang-glide") + `",
        "` + _lt("parachute") + `",
        "` + _lt("parasail") + `",
        "` + _lt("skydive") + `",
        "` + _lt("parascend") + `"
    ],
    "name": "` + _lt("parachute") + `",
    "shortcodes": [
        ":parachute:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "💺",
    "emoticons": [],
    "keywords": [
        "` + _lt("chair") + `",
        "` + _lt("seat") + `"
    ],
    "name": "` + _lt("seat") + `",
    "shortcodes": [
        ":seat:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚁",
    "emoticons": [],
    "keywords": [
        "` + _lt("helicopter") + `",
        "` + _lt("vehicle") + `"
    ],
    "name": "` + _lt("helicopter") + `",
    "shortcodes": [
        ":helicopter:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚟",
    "emoticons": [],
    "keywords": [
        "` + _lt("cable") + `",
        "` + _lt("railway") + `",
        "` + _lt("suspension") + `"
    ],
    "name": "` + _lt("suspension railway") + `",
    "shortcodes": [
        ":suspension_railway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚠",
    "emoticons": [],
    "keywords": [
        "` + _lt("cable") + `",
        "` + _lt("cableway") + `",
        "` + _lt("gondola") + `",
        "` + _lt("mountain") + `",
        "` + _lt("mountain cableway") + `"
    ],
    "name": "` + _lt("mountain cableway") + `",
    "shortcodes": [
        ":mountain_cableway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚡",
    "emoticons": [],
    "keywords": [
        "` + _lt("aerial") + `",
        "` + _lt("cable") + `",
        "` + _lt("car") + `",
        "` + _lt("gondola") + `",
        "` + _lt("tramway") + `"
    ],
    "name": "` + _lt("aerial tramway") + `",
    "shortcodes": [
        ":aerial_ltramway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛰️",
    "emoticons": [],
    "keywords": [
        "` + _lt("satellite") + `",
        "` + _lt("space") + `"
    ],
    "name": "` + _lt("satellite") + `",
    "shortcodes": [
        ":satellite:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚀",
    "emoticons": [],
    "keywords": [
        "` + _lt("rocket") + `",
        "` + _lt("space") + `"
    ],
    "name": "` + _lt("rocket") + `",
    "shortcodes": [
        ":rocket:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛸",
    "emoticons": [],
    "keywords": [
        "` + _lt("flying saucer") + `",
        "` + _lt("UFO") + `"
    ],
    "name": "` + _lt("flying saucer") + `",
    "shortcodes": [
        ":flying_saucer:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛎️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bell") + `",
        "` + _lt("hotel") + `",
        "` + _lt("porter") + `",
        "` + _lt("bellhop") + `"
    ],
    "name": "` + _lt("bellhop bell") + `",
    "shortcodes": [
        ":bellhop_bell:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🧳",
    "emoticons": [],
    "keywords": [
        "` + _lt("luggage") + `",
        "` + _lt("packing") + `",
        "` + _lt("travel") + `"
    ],
    "name": "` + _lt("luggage") + `",
    "shortcodes": [
        ":luggage:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⌛",
    "emoticons": [],
    "keywords": [
        "` + _lt("hourglass") + `",
        "` + _lt("hourglass done") + `",
        "` + _lt("sand") + `",
        "` + _lt("timer") + `"
    ],
    "name": "` + _lt("hourglass done") + `",
    "shortcodes": [
        ":hourglass_done:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⏳",
    "emoticons": [],
    "keywords": [
        "` + _lt("hourglass") + `",
        "` + _lt("hourglass not done") + `",
        "` + _lt("sand") + `",
        "` + _lt("timer") + `"
    ],
    "name": "` + _lt("hourglass not done") + `",
    "shortcodes": [
        ":hourglass_not_done:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⌚",
    "emoticons": [],
    "keywords": [
        "` + _lt("clock") + `",
        "` + _lt("watch") + `"
    ],
    "name": "` + _lt("watch") + `",
    "shortcodes": [
        ":watch:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⏰",
    "emoticons": [],
    "keywords": [
        "` + _lt("alarm") + `",
        "` + _lt("clock") + `"
    ],
    "name": "` + _lt("alarm clock") + `",
    "shortcodes": [
        ":alarm_clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⏱️",
    "emoticons": [],
    "keywords": [
        "` + _lt("clock") + `",
        "` + _lt("stopwatch") + `"
    ],
    "name": "` + _lt("stopwatch") + `",
    "shortcodes": [
        ":stopwatch:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⏲️",
    "emoticons": [],
    "keywords": [
        "` + _lt("clock") + `",
        "` + _lt("timer") + `"
    ],
    "name": "` + _lt("timer clock") + `",
    "shortcodes": [
        ":timer_clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕰️",
    "emoticons": [],
    "keywords": [
        "` + _lt("clock") + `",
        "` + _lt("mantelpiece clock") + `"
    ],
    "name": "` + _lt("mantelpiece clock") + `",
    "shortcodes": [
        ":mantelpiece_clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕛",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("12") + `",
        "` + _lt("12:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("o’clock") + `",
        "` + _lt("twelve") + `"
    ],
    "name": "` + _lt("twelve o’clock") + `",
    "shortcodes": [
        ":twelve_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕧",
    "emoticons": [],
    "keywords": [
        "` + _lt("12") + `",
        "` + _lt("12:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("thirty") + `",
        "` + _lt("twelve") + `",
        "` + _lt("twelve-thirty") + `",
        "` + _lt("half past twelve") + `",
        "` + _lt("12.30") + `"
    ],
    "name": "` + _lt("twelve-thirty") + `",
    "shortcodes": [
        ":twelve-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕐",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("1") + `",
        "` + _lt("1:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("o’clock") + `",
        "` + _lt("one") + `"
    ],
    "name": "` + _lt("one o’clock") + `",
    "shortcodes": [
        ":one_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕜",
    "emoticons": [],
    "keywords": [
        "` + _lt("1") + `",
        "` + _lt("1:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("one") + `",
        "` + _lt("one-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past one") + `",
        "` + _lt("1.30") + `"
    ],
    "name": "` + _lt("one-thirty") + `",
    "shortcodes": [
        ":one-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕑",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("2") + `",
        "` + _lt("2:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("o’clock") + `",
        "` + _lt("two") + `"
    ],
    "name": "` + _lt("two o’clock") + `",
    "shortcodes": [
        ":two_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕝",
    "emoticons": [],
    "keywords": [
        "` + _lt("2") + `",
        "` + _lt("2:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("thirty") + `",
        "` + _lt("two") + `",
        "` + _lt("two-thirty") + `",
        "` + _lt("half past two") + `",
        "` + _lt("2.30") + `"
    ],
    "name": "` + _lt("two-thirty") + `",
    "shortcodes": [
        ":two-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕒",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("3") + `",
        "` + _lt("3:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("o’clock") + `",
        "` + _lt("three") + `"
    ],
    "name": "` + _lt("three o’clock") + `",
    "shortcodes": [
        ":three_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕞",
    "emoticons": [],
    "keywords": [
        "` + _lt("3") + `",
        "` + _lt("3:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("thirty") + `",
        "` + _lt("three") + `",
        "` + _lt("three-thirty") + `",
        "` + _lt("half past three") + `",
        "` + _lt("3.30") + `"
    ],
    "name": "` + _lt("three-thirty") + `",
    "shortcodes": [
        ":three-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕓",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("4") + `",
        "` + _lt("4:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("four") + `",
        "` + _lt("o’clock") + `"
    ],
    "name": "` + _lt("four o’clock") + `",
    "shortcodes": [
        ":four_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕟",
    "emoticons": [],
    "keywords": [
        "` + _lt("4") + `",
        "` + _lt("4:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("four") + `",
        "` + _lt("four-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past four") + `",
        "` + _lt("4.30") + `"
    ],
    "name": "` + _lt("four-thirty") + `",
    "shortcodes": [
        ":four-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕔",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("5") + `",
        "` + _lt("5:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("five") + `",
        "` + _lt("o’clock") + `"
    ],
    "name": "` + _lt("five o’clock") + `",
    "shortcodes": [
        ":five_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕠",
    "emoticons": [],
    "keywords": [
        "` + _lt("5") + `",
        "` + _lt("5:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("five") + `",
        "` + _lt("five-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past five") + `",
        "` + _lt("5.30") + `"
    ],
    "name": "` + _lt("five-thirty") + `",
    "shortcodes": [
        ":five-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕕",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("6") + `",
        "` + _lt("6:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("o’clock") + `",
        "` + _lt("six") + `"
    ],
    "name": "` + _lt("six o’clock") + `",
    "shortcodes": [
        ":six_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕡",
    "emoticons": [],
    "keywords": [
        "` + _lt("6") + `",
        "` + _lt("6:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("six") + `",
        "` + _lt("six-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past six") + `",
        "` + _lt("6.30") + `"
    ],
    "name": "` + _lt("six-thirty") + `",
    "shortcodes": [
        ":six-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕖",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("7") + `",
        "` + _lt("7:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("o’clock") + `",
        "` + _lt("seven") + `"
    ],
    "name": "` + _lt("seven o’clock") + `",
    "shortcodes": [
        ":seven_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕢",
    "emoticons": [],
    "keywords": [
        "` + _lt("7") + `",
        "` + _lt("7:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("seven") + `",
        "` + _lt("seven-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past seven") + `",
        "` + _lt("7.30") + `"
    ],
    "name": "` + _lt("seven-thirty") + `",
    "shortcodes": [
        ":seven-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕗",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("8") + `",
        "` + _lt("8:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("eight") + `",
        "` + _lt("o’clock") + `"
    ],
    "name": "` + _lt("eight o’clock") + `",
    "shortcodes": [
        ":eight_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕣",
    "emoticons": [],
    "keywords": [
        "` + _lt("8") + `",
        "` + _lt("8:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("eight") + `",
        "` + _lt("eight-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past eight") + `",
        "` + _lt("8.30") + `"
    ],
    "name": "` + _lt("eight-thirty") + `",
    "shortcodes": [
        ":eight-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕘",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("9") + `",
        "` + _lt("9:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("nine") + `",
        "` + _lt("o’clock") + `"
    ],
    "name": "` + _lt("nine o’clock") + `",
    "shortcodes": [
        ":nine_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕤",
    "emoticons": [],
    "keywords": [
        "` + _lt("9") + `",
        "` + _lt("9:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("nine") + `",
        "` + _lt("nine-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past nine") + `",
        "` + _lt("9.30") + `"
    ],
    "name": "` + _lt("nine-thirty") + `",
    "shortcodes": [
        ":nine-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕙",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("10") + `",
        "` + _lt("10:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("o’clock") + `",
        "` + _lt("ten") + `"
    ],
    "name": "` + _lt("ten o’clock") + `",
    "shortcodes": [
        ":ten_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕥",
    "emoticons": [],
    "keywords": [
        "` + _lt("10") + `",
        "` + _lt("10:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("ten") + `",
        "` + _lt("ten-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past ten") + `",
        "` + _lt("10.30") + `"
    ],
    "name": "` + _lt("ten-thirty") + `",
    "shortcodes": [
        ":ten-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕚",
    "emoticons": [],
    "keywords": [
        "` + _lt("00") + `",
        "` + _lt("11") + `",
        "` + _lt("11:00") + `",
        "` + _lt("clock") + `",
        "` + _lt("eleven") + `",
        "` + _lt("o’clock") + `"
    ],
    "name": "` + _lt("eleven o’clock") + `",
    "shortcodes": [
        ":eleven_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕦",
    "emoticons": [],
    "keywords": [
        "` + _lt("11") + `",
        "` + _lt("11:30") + `",
        "` + _lt("clock") + `",
        "` + _lt("eleven") + `",
        "` + _lt("eleven-thirty") + `",
        "` + _lt("thirty") + `",
        "` + _lt("half past eleven") + `",
        "` + _lt("11.30") + `"
    ],
    "name": "` + _lt("eleven-thirty") + `",
    "shortcodes": [
        ":eleven-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌑",
    "emoticons": [],
    "keywords": [
        "` + _lt("dark") + `",
        "` + _lt("moon") + `",
        "` + _lt("new moon") + `"
    ],
    "name": "` + _lt("new moon") + `",
    "shortcodes": [
        ":new_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌒",
    "emoticons": [],
    "keywords": [
        "` + _lt("crescent") + `",
        "` + _lt("moon") + `",
        "` + _lt("waxing") + `"
    ],
    "name": "` + _lt("waxing crescent moon") + `",
    "shortcodes": [
        ":waxing_crescent_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌓",
    "emoticons": [],
    "keywords": [
        "` + _lt("first quarter moon") + `",
        "` + _lt("moon") + `",
        "` + _lt("quarter") + `"
    ],
    "name": "` + _lt("first quarter moon") + `",
    "shortcodes": [
        ":first_quarter_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌔",
    "emoticons": [],
    "keywords": [
        "` + _lt("gibbous") + `",
        "` + _lt("moon") + `",
        "` + _lt("waxing") + `"
    ],
    "name": "` + _lt("waxing gibbous moon") + `",
    "shortcodes": [
        ":waxing_gibbous_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌕",
    "emoticons": [],
    "keywords": [
        "` + _lt("full") + `",
        "` + _lt("moon") + `"
    ],
    "name": "` + _lt("full moon") + `",
    "shortcodes": [
        ":full_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌖",
    "emoticons": [],
    "keywords": [
        "` + _lt("gibbous") + `",
        "` + _lt("moon") + `",
        "` + _lt("waning") + `"
    ],
    "name": "` + _lt("waning gibbous moon") + `",
    "shortcodes": [
        ":waning_gibbous_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌗",
    "emoticons": [],
    "keywords": [
        "` + _lt("last quarter moon") + `",
        "` + _lt("moon") + `",
        "` + _lt("quarter") + `"
    ],
    "name": "` + _lt("last quarter moon") + `",
    "shortcodes": [
        ":last_quarter_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌘",
    "emoticons": [],
    "keywords": [
        "` + _lt("crescent") + `",
        "` + _lt("moon") + `",
        "` + _lt("waning") + `"
    ],
    "name": "` + _lt("waning crescent moon") + `",
    "shortcodes": [
        ":waning_crescent_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌙",
    "emoticons": [],
    "keywords": [
        "` + _lt("crescent") + `",
        "` + _lt("moon") + `"
    ],
    "name": "` + _lt("crescent moon") + `",
    "shortcodes": [
        ":crescent_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌚",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("moon") + `",
        "` + _lt("new moon face") + `"
    ],
    "name": "` + _lt("new moon face") + `",
    "shortcodes": [
        ":new_moon_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌛",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("first quarter moon face") + `",
        "` + _lt("moon") + `",
        "` + _lt("quarter") + `"
    ],
    "name": "` + _lt("first quarter moon face") + `",
    "shortcodes": [
        ":first_quarter_moon_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌜",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("last quarter moon face") + `",
        "` + _lt("moon") + `",
        "` + _lt("quarter") + `"
    ],
    "name": "` + _lt("last quarter moon face") + `",
    "shortcodes": [
        ":last_quarter_moon_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌡️",
    "emoticons": [],
    "keywords": [
        "` + _lt("thermometer") + `",
        "` + _lt("weather") + `"
    ],
    "name": "` + _lt("thermometer") + `",
    "shortcodes": [
        ":thermometer:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☀️",
    "emoticons": [
        ":sun"
    ],
    "keywords": [
        "` + _lt("bright") + `",
        "` + _lt("rays") + `",
        "` + _lt("sun") + `",
        "` + _lt("sunny") + `"
    ],
    "name": "` + _lt("sun") + `",
    "shortcodes": [
        ":sun:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌝",
    "emoticons": [],
    "keywords": [
        "` + _lt("bright") + `",
        "` + _lt("face") + `",
        "` + _lt("full") + `",
        "` + _lt("moon") + `",
        "` + _lt("full-moon face") + `"
    ],
    "name": "` + _lt("full moon face") + `",
    "shortcodes": [
        ":full_moon_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌞",
    "emoticons": [],
    "keywords": [
        "` + _lt("bright") + `",
        "` + _lt("face") + `",
        "` + _lt("sun") + `",
        "` + _lt("sun with face") + `"
    ],
    "name": "` + _lt("sun with face") + `",
    "shortcodes": [
        ":sun_with_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🪐",
    "emoticons": [],
    "keywords": [
        "` + _lt("ringed planet") + `",
        "` + _lt("saturn") + `",
        "` + _lt("saturnine") + `"
    ],
    "name": "` + _lt("ringed planet") + `",
    "shortcodes": [
        ":ringed_planet:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⭐",
    "emoticons": [
        ":star"
    ],
    "keywords": [
        "` + _lt("star") + `"
    ],
    "name": "` + _lt("star") + `",
    "shortcodes": [
        ":star:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌟",
    "emoticons": [],
    "keywords": [
        "` + _lt("glittery") + `",
        "` + _lt("glow") + `",
        "` + _lt("glowing star") + `",
        "` + _lt("shining") + `",
        "` + _lt("sparkle") + `",
        "` + _lt("star") + `"
    ],
    "name": "` + _lt("glowing star") + `",
    "shortcodes": [
        ":glowing_star:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌠",
    "emoticons": [],
    "keywords": [
        "` + _lt("falling") + `",
        "` + _lt("shooting") + `",
        "` + _lt("star") + `"
    ],
    "name": "` + _lt("shooting star") + `",
    "shortcodes": [
        ":shooting_star:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌌",
    "emoticons": [],
    "keywords": [
        "` + _lt("Milky Way") + `",
        "` + _lt("space") + `",
        "` + _lt("milky way") + `",
        "` + _lt("Milky") + `",
        "` + _lt("Way") + `"
    ],
    "name": "` + _lt("milky way") + `",
    "shortcodes": [
        ":milky_way:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☁️",
    "emoticons": [
        ":cloud"
    ],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("weather") + `"
    ],
    "name": "` + _lt("cloud") + `",
    "shortcodes": [
        ":cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛅",
    "emoticons": [
        ":partly_sunny:"
    ],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("sun") + `",
        "` + _lt("sun behind cloud") + `"
    ],
    "name": "` + _lt("sun behind cloud") + `",
    "shortcodes": [
        ":sun_behind_cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛈️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("cloud with lightning and rain") + `",
        "` + _lt("rain") + `",
        "` + _lt("thunder") + `"
    ],
    "name": "` + _lt("cloud with lightning and rain") + `",
    "shortcodes": [
        ":cloud_with_lightning_and_rain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌤️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("sun") + `",
        "` + _lt("sun behind small cloud") + `"
    ],
    "name": "` + _lt("sun behind small cloud") + `",
    "shortcodes": [
        ":sun_behind_small_cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌥️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("sun") + `",
        "` + _lt("sun behind large cloud") + `"
    ],
    "name": "` + _lt("sun behind large cloud") + `",
    "shortcodes": [
        ":sun_behind_large_cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌦️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("rain") + `",
        "` + _lt("sun") + `",
        "` + _lt("sun behind rain cloud") + `"
    ],
    "name": "` + _lt("sun behind rain cloud") + `",
    "shortcodes": [
        ":sun_behind_rain_cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌧️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("cloud with rain") + `",
        "` + _lt("rain") + `"
    ],
    "name": "` + _lt("cloud with rain") + `",
    "shortcodes": [
        ":cloud_with_rain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌨️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("cloud with snow") + `",
        "` + _lt("cold") + `",
        "` + _lt("snow") + `"
    ],
    "name": "` + _lt("cloud with snow") + `",
    "shortcodes": [
        ":cloud_with_snow:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌩️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("cloud with lightning") + `",
        "` + _lt("lightning") + `"
    ],
    "name": "` + _lt("cloud with lightning") + `",
    "shortcodes": [
        ":cloud_with_lightning:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌪️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("tornado") + `",
        "` + _lt("whirlwind") + `"
    ],
    "name": "` + _lt("tornado") + `",
    "shortcodes": [
        ":tornado:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌫️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cloud") + `",
        "` + _lt("fog") + `"
    ],
    "name": "` + _lt("fog") + `",
    "shortcodes": [
        ":fog:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌬️",
    "emoticons": [],
    "keywords": [
        "` + _lt("blow") + `",
        "` + _lt("cloud") + `",
        "` + _lt("face") + `",
        "` + _lt("wind") + `"
    ],
    "name": "` + _lt("wind face") + `",
    "shortcodes": [
        ":wind_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌀",
    "emoticons": [],
    "keywords": [
        "` + _lt("cyclone") + `",
        "` + _lt("dizzy") + `",
        "` + _lt("hurricane") + `",
        "` + _lt("twister") + `",
        "` + _lt("typhoon") + `"
    ],
    "name": "` + _lt("cyclone") + `",
    "shortcodes": [
        ":cyclone:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌈",
    "emoticons": [
        ":rainbow"
    ],
    "keywords": [
        "` + _lt("rain") + `",
        "` + _lt("rainbow") + `"
    ],
    "name": "` + _lt("rainbow") + `",
    "shortcodes": [
        ":rainbow:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌂",
    "emoticons": [],
    "keywords": [
        "` + _lt("closed umbrella") + `",
        "` + _lt("clothing") + `",
        "` + _lt("rain") + `",
        "` + _lt("umbrella") + `"
    ],
    "name": "` + _lt("closed umbrella") + `",
    "shortcodes": [
        ":closed_umbrella:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("rain") + `",
        "` + _lt("umbrella") + `"
    ],
    "name": "` + _lt("umbrella") + `",
    "shortcodes": [
        ":umbrella:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☔",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("drop") + `",
        "` + _lt("rain") + `",
        "` + _lt("umbrella") + `",
        "` + _lt("umbrella with rain drops") + `"
    ],
    "name": "` + _lt("umbrella with rain drops") + `",
    "shortcodes": [
        ":umbrella_with_rain_drops:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛱️",
    "emoticons": [],
    "keywords": [
        "` + _lt("beach") + `",
        "` + _lt("sand") + `",
        "` + _lt("sun") + `",
        "` + _lt("umbrella") + `",
        "` + _lt("rain") + `",
        "` + _lt("umbrella on ground") + `"
    ],
    "name": "` + _lt("umbrella on ground") + `",
    "shortcodes": [
        ":umbrella_on_ground:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⚡",
    "emoticons": [
        ":zap"
    ],
    "keywords": [
        "` + _lt("danger") + `",
        "` + _lt("electric") + `",
        "` + _lt("high voltage") + `",
        "` + _lt("lightning") + `",
        "` + _lt("voltage") + `",
        "` + _lt("zap") + `"
    ],
    "name": "` + _lt("high voltage") + `",
    "shortcodes": [
        ":high_voltage:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "❄️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("snow") + `",
        "` + _lt("snowflake") + `"
    ],
    "name": "` + _lt("snowflake") + `",
    "shortcodes": [
        ":snowflake:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☃️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("snow") + `",
        "` + _lt("snowman") + `"
    ],
    "name": "` + _lt("snowman") + `",
    "shortcodes": [
        ":snowman:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛄",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("snow") + `",
        "` + _lt("snowman") + `",
        "` + _lt("snowman without snow") + `"
    ],
    "name": "` + _lt("snowman without snow") + `",
    "shortcodes": [
        ":snowman_without_snow:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☄️",
    "emoticons": [],
    "keywords": [
        "` + _lt("comet") + `",
        "` + _lt("space") + `"
    ],
    "name": "` + _lt("comet") + `",
    "shortcodes": [
        ":comet:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🔥",
    "emoticons": [
        ":fire"
    ],
    "keywords": [
        "` + _lt("fire") + `",
        "` + _lt("flame") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("fire") + `",
    "shortcodes": [
        ":fire:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "💧",
    "emoticons": [],
    "keywords": [
        "` + _lt("cold") + `",
        "` + _lt("comic") + `",
        "` + _lt("drop") + `",
        "` + _lt("droplet") + `",
        "` + _lt("sweat") + `"
    ],
    "name": "` + _lt("droplet") + `",
    "shortcodes": [
        ":droplet:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌊",
    "emoticons": [],
    "keywords": [
        "` + _lt("ocean") + `",
        "` + _lt("water") + `",
        "` + _lt("wave") + `"
    ],
    "name": "` + _lt("water wave") + `",
    "shortcodes": [
        ":water_wave:"
    ]
},`;

const emojisData6 = `{
    "category": "Activities",
    "codepoints": "🎃",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("halloween") + `",
        "` + _lt("jack") + `",
        "` + _lt("jack-o-lantern") + `",
        "` + _lt("lantern") + `",
        "` + _lt("Halloween") + `",
        "` + _lt("jack-o’-lantern") + `"
    ],
    "name": "` + _lt("jack-o-lantern") + `",
    "shortcodes": [
        ":jack-o-lantern:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎄",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("Christmas") + `",
        "` + _lt("tree") + `"
    ],
    "name": "` + _lt("Christmas tree") + `",
    "shortcodes": [
        ":Christmas_ltree:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎆",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("fireworks") + `"
    ],
    "name": "` + _lt("fireworks") + `",
    "shortcodes": [
        ":fireworks:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎇",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("fireworks") + `",
        "` + _lt("sparkle") + `",
        "` + _lt("sparkler") + `"
    ],
    "name": "` + _lt("sparkler") + `",
    "shortcodes": [
        ":sparkler:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧨",
    "emoticons": [],
    "keywords": [
        "` + _lt("dynamite") + `",
        "` + _lt("explosive") + `",
        "` + _lt("firecracker") + `",
        "` + _lt("fireworks") + `"
    ],
    "name": "` + _lt("firecracker") + `",
    "shortcodes": [
        ":firecracker:"
    ]
},
{
    "category": "Activities",
    "codepoints": "✨",
    "emoticons": [],
    "keywords": [
        "` + _lt("*") + `",
        "` + _lt("sparkle") + `",
        "` + _lt("sparkles") + `",
        "` + _lt("star") + `"
    ],
    "name": "` + _lt("sparkles") + `",
    "shortcodes": [
        ":sparkles:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎈",
    "emoticons": [],
    "keywords": [
        "` + _lt("balloon") + `",
        "` + _lt("celebration") + `"
    ],
    "name": "` + _lt("balloon") + `",
    "shortcodes": [
        ":balloon:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎉",
    "emoticons": [
        ":party"
    ],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("party") + `",
        "` + _lt("popper") + `",
        "` + _lt("ta-da") + `",
        "` + _lt("tada") + `"
    ],
    "name": "` + _lt("party popper") + `",
    "shortcodes": [
        ":party_popper:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎊",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("celebration") + `",
        "` + _lt("confetti") + `"
    ],
    "name": "` + _lt("confetti ball") + `",
    "shortcodes": [
        ":confetti_ball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎋",
    "emoticons": [],
    "keywords": [
        "` + _lt("banner") + `",
        "` + _lt("celebration") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("tanabata tree") + `",
        "` + _lt("tree") + `",
        "` + _lt("Tanabata tree") + `"
    ],
    "name": "` + _lt("tanabata tree") + `",
    "shortcodes": [
        ":tanabata_ltree:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎍",
    "emoticons": [],
    "keywords": [
        "` + _lt("bamboo") + `",
        "` + _lt("celebration") + `",
        "` + _lt("decoration") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("pine") + `",
        "` + _lt("pine decoration") + `"
    ],
    "name": "` + _lt("pine decoration") + `",
    "shortcodes": [
        ":pine_decoration:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎎",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("doll") + `",
        "` + _lt("festival") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese dolls") + `"
    ],
    "name": "` + _lt("Japanese dolls") + `",
    "shortcodes": [
        ":Japanese_dolls:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎏",
    "emoticons": [],
    "keywords": [
        "` + _lt("carp") + `",
        "` + _lt("celebration") + `",
        "` + _lt("streamer") + `",
        "` + _lt("carp wind sock") + `",
        "` + _lt("Japanese wind socks") + `",
        "` + _lt("koinobori") + `"
    ],
    "name": "` + _lt("carp streamer") + `",
    "shortcodes": [
        ":carp_streamer:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎐",
    "emoticons": [],
    "keywords": [
        "` + _lt("bell") + `",
        "` + _lt("celebration") + `",
        "` + _lt("chime") + `",
        "` + _lt("wind") + `"
    ],
    "name": "` + _lt("wind chime") + `",
    "shortcodes": [
        ":wind_chime:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎑",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("ceremony") + `",
        "` + _lt("moon") + `",
        "` + _lt("moon viewing ceremony") + `",
        "` + _lt("moon-viewing ceremony") + `"
    ],
    "name": "` + _lt("moon viewing ceremony") + `",
    "shortcodes": [
        ":moon_viewing_ceremony:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧧",
    "emoticons": [],
    "keywords": [
        "` + _lt("gift") + `",
        "` + _lt("good luck") + `",
        "` + _lt("hóngbāo") + `",
        "` + _lt("lai see") + `",
        "` + _lt("money") + `",
        "` + _lt("red envelope") + `"
    ],
    "name": "` + _lt("red envelope") + `",
    "shortcodes": [
        ":red_envelope:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎀",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("ribbon") + `"
    ],
    "name": "` + _lt("ribbon") + `",
    "shortcodes": [
        ":ribbon:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎁",
    "emoticons": [],
    "keywords": [
        "` + _lt("box") + `",
        "` + _lt("celebration") + `",
        "` + _lt("gift") + `",
        "` + _lt("present") + `",
        "` + _lt("wrapped") + `"
    ],
    "name": "` + _lt("wrapped gift") + `",
    "shortcodes": [
        ":wrapped_gift:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎗️",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("reminder") + `",
        "` + _lt("ribbon") + `"
    ],
    "name": "` + _lt("reminder ribbon") + `",
    "shortcodes": [
        ":reminder_ribbon:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎟️",
    "emoticons": [],
    "keywords": [
        "` + _lt("admission") + `",
        "` + _lt("admission tickets") + `",
        "` + _lt("entry") + `",
        "` + _lt("ticket") + `"
    ],
    "name": "` + _lt("admission tickets") + `",
    "shortcodes": [
        ":admission_ltickets:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎫",
    "emoticons": [],
    "keywords": [
        "` + _lt("admission") + `",
        "` + _lt("ticket") + `"
    ],
    "name": "` + _lt("ticket") + `",
    "shortcodes": [
        ":ticket:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎖️",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("medal") + `",
        "` + _lt("military") + `"
    ],
    "name": "` + _lt("military medal") + `",
    "shortcodes": [
        ":military_medal:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏆",
    "emoticons": [
        ":trophy"
    ],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("prize") + `",
        "` + _lt("trophy") + `"
    ],
    "name": "` + _lt("trophy") + `",
    "shortcodes": [
        ":trophy:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏅",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("medal") + `",
        "` + _lt("sports") + `",
        "` + _lt("sports medal") + `"
    ],
    "name": "` + _lt("sports medal") + `",
    "shortcodes": [
        ":sports_medal:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥇",
    "emoticons": [],
    "keywords": [
        "` + _lt("1st place medal") + `",
        "` + _lt("first") + `",
        "` + _lt("gold") + `",
        "` + _lt("medal") + `"
    ],
    "name": "` + _lt("1st place medal") + `",
    "shortcodes": [
        ":1st_place_medal:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥈",
    "emoticons": [],
    "keywords": [
        "` + _lt("2nd place medal") + `",
        "` + _lt("medal") + `",
        "` + _lt("second") + `",
        "` + _lt("silver") + `"
    ],
    "name": "` + _lt("2nd place medal") + `",
    "shortcodes": [
        ":2nd_place_medal:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥉",
    "emoticons": [],
    "keywords": [
        "` + _lt("3rd place medal") + `",
        "` + _lt("bronze") + `",
        "` + _lt("medal") + `",
        "` + _lt("third") + `"
    ],
    "name": "` + _lt("3rd place medal") + `",
    "shortcodes": [
        ":3rd_place_medal:"
    ]
},
{
    "category": "Activities",
    "codepoints": "⚽",
    "emoticons": [
        ":soccer"
    ],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("football") + `",
        "` + _lt("soccer") + `"
    ],
    "name": "` + _lt("soccer ball") + `",
    "shortcodes": [
        ":soccer_ball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "⚾",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("baseball") + `"
    ],
    "name": "` + _lt("baseball") + `",
    "shortcodes": [
        ":baseball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥎",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("glove") + `",
        "` + _lt("softball") + `",
        "` + _lt("underarm") + `"
    ],
    "name": "` + _lt("softball") + `",
    "shortcodes": [
        ":softball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏀",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("basketball") + `",
        "` + _lt("hoop") + `"
    ],
    "name": "` + _lt("basketball") + `",
    "shortcodes": [
        ":basketball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏐",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("game") + `",
        "` + _lt("volleyball") + `"
    ],
    "name": "` + _lt("volleyball") + `",
    "shortcodes": [
        ":volleyball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏈",
    "emoticons": [
        ":football"
    ],
    "keywords": [
        "` + _lt("american") + `",
        "` + _lt("ball") + `",
        "` + _lt("football") + `"
    ],
    "name": "` + _lt("american football") + `",
    "shortcodes": [
        ":american_football:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏉",
    "emoticons": [],
    "keywords": [
        "` + _lt("australian football") + `",
        "` + _lt("rugby ball") + `",
        "` + _lt("rugby league") + `",
        "` + _lt("rugby union") + `",
        "` + _lt("ball") + `",
        "` + _lt("football") + `",
        "` + _lt("rugby") + `"
    ],
    "name": "` + _lt("rugby football") + `",
    "shortcodes": [
        ":rugby_football:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎾",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("racquet") + `",
        "` + _lt("tennis") + `"
    ],
    "name": "` + _lt("tennis") + `",
    "shortcodes": [
        ":tennis:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥏",
    "emoticons": [],
    "keywords": [
        "` + _lt("flying disc") + `",
        "` + _lt("frisbee") + `",
        "` + _lt("ultimate") + `",
        "` + _lt("Frisbee") + `"
    ],
    "name": "` + _lt("flying disc") + `",
    "shortcodes": [
        ":flying_disc:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎳",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("game") + `",
        "` + _lt("tenpin bowling") + `",
        "` + _lt("bowling") + `"
    ],
    "name": "` + _lt("bowling") + `",
    "shortcodes": [
        ":bowling:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏏",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("bat") + `",
        "` + _lt("cricket game") + `",
        "` + _lt("game") + `",
        "` + _lt("cricket") + `",
        "` + _lt("cricket match") + `"
    ],
    "name": "` + _lt("cricket game") + `",
    "shortcodes": [
        ":cricket_game:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏑",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("field") + `",
        "` + _lt("game") + `",
        "` + _lt("hockey") + `",
        "` + _lt("stick") + `"
    ],
    "name": "` + _lt("field hockey") + `",
    "shortcodes": [
        ":field_hockey:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏒",
    "emoticons": [],
    "keywords": [
        "` + _lt("game") + `",
        "` + _lt("hockey") + `",
        "` + _lt("ice") + `",
        "` + _lt("puck") + `",
        "` + _lt("stick") + `"
    ],
    "name": "` + _lt("ice hockey") + `",
    "shortcodes": [
        ":ice_hockey:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥍",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("goal") + `",
        "` + _lt("lacrosse") + `",
        "` + _lt("stick") + `"
    ],
    "name": "` + _lt("lacrosse") + `",
    "shortcodes": [
        ":lacrosse:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏓",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("bat") + `",
        "` + _lt("game") + `",
        "` + _lt("paddle") + `",
        "` + _lt("ping pong") + `",
        "` + _lt("table tennis") + `"
    ],
    "name": "` + _lt("ping pong") + `",
    "shortcodes": [
        ":ping_pong:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏸",
    "emoticons": [],
    "keywords": [
        "` + _lt("badminton") + `",
        "` + _lt("birdie") + `",
        "` + _lt("game") + `",
        "` + _lt("racquet") + `",
        "` + _lt("shuttlecock") + `"
    ],
    "name": "` + _lt("badminton") + `",
    "shortcodes": [
        ":badminton:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥊",
    "emoticons": [],
    "keywords": [
        "` + _lt("boxing") + `",
        "` + _lt("glove") + `"
    ],
    "name": "` + _lt("boxing glove") + `",
    "shortcodes": [
        ":boxing_glove:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥋",
    "emoticons": [],
    "keywords": [
        "` + _lt("judo") + `",
        "` + _lt("karate") + `",
        "` + _lt("martial arts") + `",
        "` + _lt("martial arts uniform") + `",
        "` + _lt("taekwondo") + `",
        "` + _lt("uniform") + `"
    ],
    "name": "` + _lt("martial arts uniform") + `",
    "shortcodes": [
        ":martial_arts_uniform:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥅",
    "emoticons": [],
    "keywords": [
        "` + _lt("goal") + `",
        "` + _lt("goal cage") + `",
        "` + _lt("net") + `"
    ],
    "name": "` + _lt("goal net") + `",
    "shortcodes": [
        ":goal_net:"
    ]
},
{
    "category": "Activities",
    "codepoints": "⛳",
    "emoticons": [],
    "keywords": [
        "` + _lt("flag") + `",
        "` + _lt("flag in hole") + `",
        "` + _lt("golf") + `",
        "` + _lt("hole") + `"
    ],
    "name": "` + _lt("flag in hole") + `",
    "shortcodes": [
        ":flag_in_hole:"
    ]
},
{
    "category": "Activities",
    "codepoints": "⛸️",
    "emoticons": [],
    "keywords": [
        "` + _lt("ice") + `",
        "` + _lt("ice skating") + `",
        "` + _lt("skate") + `"
    ],
    "name": "` + _lt("ice skate") + `",
    "shortcodes": [
        ":ice_skate:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎣",
    "emoticons": [],
    "keywords": [
        "` + _lt("fish") + `",
        "` + _lt("fishing") + `",
        "` + _lt("pole") + `",
        "` + _lt("rod") + `",
        "` + _lt("fishing pole") + `"
    ],
    "name": "` + _lt("fishing pole") + `",
    "shortcodes": [
        ":fishing_pole:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🤿",
    "emoticons": [],
    "keywords": [
        "` + _lt("diving") + `",
        "` + _lt("diving mask") + `",
        "` + _lt("scuba") + `",
        "` + _lt("snorkeling") + `",
        "` + _lt("snorkelling") + `"
    ],
    "name": "` + _lt("diving mask") + `",
    "shortcodes": [
        ":diving_mask:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎽",
    "emoticons": [],
    "keywords": [
        "` + _lt("athletics") + `",
        "` + _lt("running") + `",
        "` + _lt("sash") + `",
        "` + _lt("shirt") + `"
    ],
    "name": "` + _lt("running shirt") + `",
    "shortcodes": [
        ":running_shirt:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎿",
    "emoticons": [],
    "keywords": [
        "` + _lt("ski") + `",
        "` + _lt("skiing") + `",
        "` + _lt("skis") + `",
        "` + _lt("snow") + `"
    ],
    "name": "` + _lt("skis") + `",
    "shortcodes": [
        ":skis:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🛷",
    "emoticons": [],
    "keywords": [
        "` + _lt("sled") + `",
        "` + _lt("sledge") + `",
        "` + _lt("sleigh") + `"
    ],
    "name": "` + _lt("sled") + `",
    "shortcodes": [
        ":sled:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥌",
    "emoticons": [],
    "keywords": [
        "` + _lt("curling") + `",
        "` + _lt("game") + `",
        "` + _lt("rock") + `",
        "` + _lt("stone") + `",
        "` + _lt("curling stone") + `",
        "` + _lt("curling rock") + `"
    ],
    "name": "` + _lt("curling stone") + `",
    "shortcodes": [
        ":curling_stone:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎯",
    "emoticons": [],
    "keywords": [
        "` + _lt("bullseye") + `",
        "` + _lt("dart") + `",
        "` + _lt("direct hit") + `",
        "` + _lt("game") + `",
        "` + _lt("hit") + `",
        "` + _lt("target") + `"
    ],
    "name": "` + _lt("bullseye") + `",
    "shortcodes": [
        ":bullseye:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🪀",
    "emoticons": [],
    "keywords": [
        "` + _lt("fluctuate") + `",
        "` + _lt("toy") + `",
        "` + _lt("yo-yo") + `"
    ],
    "name": "` + _lt("yo-yo") + `",
    "shortcodes": [
        ":yo-yo:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🪁",
    "emoticons": [],
    "keywords": [
        "` + _lt("fly") + `",
        "` + _lt("kite") + `",
        "` + _lt("soar") + `"
    ],
    "name": "` + _lt("kite") + `",
    "shortcodes": [
        ":kite:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎱",
    "emoticons": [
        ":8ball"
    ],
    "keywords": [
        "` + _lt("8") + `",
        "` + _lt("ball") + `",
        "` + _lt("billiard") + `",
        "` + _lt("eight") + `",
        "` + _lt("game") + `",
        "` + _lt("pool 8 ball") + `"
    ],
    "name": "` + _lt("pool 8 ball") + `",
    "shortcodes": [
        ":pool_8_ball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🔮",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("crystal") + `",
        "` + _lt("fairy tale") + `",
        "` + _lt("fantasy") + `",
        "` + _lt("fortune") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("crystal ball") + `",
    "shortcodes": [
        ":crystal_ball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧿",
    "emoticons": [],
    "keywords": [
        "` + _lt("amulet") + `",
        "` + _lt("charm") + `",
        "` + _lt("evil-eye") + `",
        "` + _lt("nazar") + `",
        "` + _lt("talisman") + `",
        "` + _lt("bead") + `",
        "` + _lt("nazar amulet") + `",
        "` + _lt("evil eye") + `"
    ],
    "name": "` + _lt("nazar amulet") + `",
    "shortcodes": [
        ":nazar_amulet:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎮",
    "emoticons": [],
    "keywords": [
        "` + _lt("controller") + `",
        "` + _lt("game") + `",
        "` + _lt("video game") + `"
    ],
    "name": "` + _lt("video game") + `",
    "shortcodes": [
        ":video_game:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🕹️",
    "emoticons": [],
    "keywords": [
        "` + _lt("game") + `",
        "` + _lt("joystick") + `",
        "` + _lt("video game") + `"
    ],
    "name": "` + _lt("joystick") + `",
    "shortcodes": [
        ":joystick:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎰",
    "emoticons": [],
    "keywords": [
        "` + _lt("game") + `",
        "` + _lt("pokie") + `",
        "` + _lt("pokies") + `",
        "` + _lt("slot") + `",
        "` + _lt("slot machine") + `"
    ],
    "name": "` + _lt("slot machine") + `",
    "shortcodes": [
        ":slot_machine:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎲",
    "emoticons": [],
    "keywords": [
        "` + _lt("dice") + `",
        "` + _lt("die") + `",
        "` + _lt("game") + `"
    ],
    "name": "` + _lt("game die") + `",
    "shortcodes": [
        ":game_die:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧩",
    "emoticons": [],
    "keywords": [
        "` + _lt("clue") + `",
        "` + _lt("interlocking") + `",
        "` + _lt("jigsaw") + `",
        "` + _lt("piece") + `",
        "` + _lt("puzzle") + `"
    ],
    "name": "` + _lt("puzzle piece") + `",
    "shortcodes": [
        ":puzzle_piece:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧸",
    "emoticons": [],
    "keywords": [
        "` + _lt("plaything") + `",
        "` + _lt("plush") + `",
        "` + _lt("stuffed") + `",
        "` + _lt("teddy bear") + `",
        "` + _lt("toy") + `"
    ],
    "name": "` + _lt("teddy bear") + `",
    "shortcodes": [
        ":teddy_bear:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♠️",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("game") + `",
        "` + _lt("spade suit") + `"
    ],
    "name": "` + _lt("spade suit") + `",
    "shortcodes": [
        ":spade_suit:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♥️",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("game") + `",
        "` + _lt("heart suit") + `"
    ],
    "name": "` + _lt("heart suit") + `",
    "shortcodes": [
        ":heart_suit:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♦️",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("diamond suit") + `",
        "` + _lt("diamonds") + `",
        "` + _lt("game") + `"
    ],
    "name": "` + _lt("diamond suit") + `",
    "shortcodes": [
        ":diamond_suit:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♣️",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("club suit") + `",
        "` + _lt("clubs") + `",
        "` + _lt("game") + `"
    ],
    "name": "` + _lt("club suit") + `",
    "shortcodes": [
        ":club_suit:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♟️",
    "emoticons": [],
    "keywords": [
        "` + _lt("chess") + `",
        "` + _lt("chess pawn") + `",
        "` + _lt("dupe") + `",
        "` + _lt("expendable") + `"
    ],
    "name": "` + _lt("chess pawn") + `",
    "shortcodes": [
        ":chess_pawn:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🃏",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("game") + `",
        "` + _lt("joker") + `",
        "` + _lt("wildcard") + `"
    ],
    "name": "` + _lt("joker") + `",
    "shortcodes": [
        ":joker:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🀄",
    "emoticons": [],
    "keywords": [
        "` + _lt("game") + `",
        "` + _lt("mahjong") + `",
        "` + _lt("mahjong red dragon") + `",
        "` + _lt("red") + `",
        "` + _lt("Mahjong") + `",
        "` + _lt("Mahjong red dragon") + `"
    ],
    "name": "` + _lt("mahjong red dragon") + `",
    "shortcodes": [
        ":mahjong_red_dragon:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎴",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("flower") + `",
        "` + _lt("flower playing cards") + `",
        "` + _lt("game") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("playing") + `"
    ],
    "name": "` + _lt("flower playing cards") + `",
    "shortcodes": [
        ":flower_playing_cards:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎭",
    "emoticons": [],
    "keywords": [
        "` + _lt("art") + `",
        "` + _lt("mask") + `",
        "` + _lt("performing") + `",
        "` + _lt("performing arts") + `",
        "` + _lt("theater") + `",
        "` + _lt("theatre") + `"
    ],
    "name": "` + _lt("performing arts") + `",
    "shortcodes": [
        ":performing_arts:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🖼️",
    "emoticons": [],
    "keywords": [
        "` + _lt("art") + `",
        "` + _lt("frame") + `",
        "` + _lt("framed picture") + `",
        "` + _lt("museum") + `",
        "` + _lt("painting") + `",
        "` + _lt("picture") + `"
    ],
    "name": "` + _lt("framed picture") + `",
    "shortcodes": [
        ":framed_picture:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎨",
    "emoticons": [],
    "keywords": [
        "` + _lt("art") + `",
        "` + _lt("artist palette") + `",
        "` + _lt("museum") + `",
        "` + _lt("painting") + `",
        "` + _lt("palette") + `"
    ],
    "name": "` + _lt("artist palette") + `",
    "shortcodes": [
        ":artist_palette:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧵",
    "emoticons": [],
    "keywords": [
        "` + _lt("needle") + `",
        "` + _lt("sewing") + `",
        "` + _lt("spool") + `",
        "` + _lt("string") + `",
        "` + _lt("thread") + `"
    ],
    "name": "` + _lt("thread") + `",
    "shortcodes": [
        ":thread:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧶",
    "emoticons": [],
    "keywords": [
        "` + _lt("ball") + `",
        "` + _lt("crochet") + `",
        "` + _lt("knit") + `",
        "` + _lt("yarn") + `"
    ],
    "name": "` + _lt("yarn") + `",
    "shortcodes": [
        ":yarn:"
    ]
},`;

const emojisData7 = `{
    "category": "Objects",
    "codepoints": "👓",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("eye") + `",
        "` + _lt("eyeglasses") + `",
        "` + _lt("eyewear") + `",
        "` + _lt("glasses") + `"
    ],
    "name": "` + _lt("glasses") + `",
    "shortcodes": [
        ":glasses:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🕶️",
    "emoticons": [],
    "keywords": [
        "` + _lt("dark") + `",
        "` + _lt("eye") + `",
        "` + _lt("eyewear") + `",
        "` + _lt("glasses") + `",
        "` + _lt("sunglasses") + `",
        "` + _lt("sunnies") + `"
    ],
    "name": "` + _lt("sunglasses") + `",
    "shortcodes": [
        ":sunglasses:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥽",
    "emoticons": [],
    "keywords": [
        "` + _lt("eye protection") + `",
        "` + _lt("goggles") + `",
        "` + _lt("swimming") + `",
        "` + _lt("welding") + `"
    ],
    "name": "` + _lt("goggles") + `",
    "shortcodes": [
        ":goggles:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥼",
    "emoticons": [],
    "keywords": [
        "` + _lt("doctor") + `",
        "` + _lt("experiment") + `",
        "` + _lt("lab coat") + `",
        "` + _lt("scientist") + `"
    ],
    "name": "` + _lt("lab coat") + `",
    "shortcodes": [
        ":lab_coat:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🦺",
    "emoticons": [],
    "keywords": [
        "` + _lt("emergency") + `",
        "` + _lt("safety") + `",
        "` + _lt("vest") + `",
        "` + _lt("hi-vis") + `",
        "` + _lt("high-vis") + `",
        "` + _lt("jacket") + `",
        "` + _lt("life jacket") + `"
    ],
    "name": "` + _lt("safety vest") + `",
    "shortcodes": [
        ":safety_vest:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👔",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("necktie") + `",
        "` + _lt("tie") + `"
    ],
    "name": "` + _lt("necktie") + `",
    "shortcodes": [
        ":necktie:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👕",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("shirt") + `",
        "` + _lt("t-shirt") + `",
        "` + _lt("T-shirt") + `",
        "` + _lt("tee") + `",
        "` + _lt("tshirt") + `",
        "` + _lt("tee-shirt") + `"
    ],
    "name": "` + _lt("t-shirt") + `",
    "shortcodes": [
        ":t-shirt:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👖",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("jeans") + `",
        "` + _lt("pants") + `",
        "` + _lt("trousers") + `"
    ],
    "name": "` + _lt("jeans") + `",
    "shortcodes": [
        ":jeans:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧣",
    "emoticons": [],
    "keywords": [
        "` + _lt("neck") + `",
        "` + _lt("scarf") + `"
    ],
    "name": "` + _lt("scarf") + `",
    "shortcodes": [
        ":scarf:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧤",
    "emoticons": [],
    "keywords": [
        "` + _lt("gloves") + `",
        "` + _lt("hand") + `"
    ],
    "name": "` + _lt("gloves") + `",
    "shortcodes": [
        ":gloves:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧥",
    "emoticons": [],
    "keywords": [
        "` + _lt("coat") + `",
        "` + _lt("jacket") + `"
    ],
    "name": "` + _lt("coat") + `",
    "shortcodes": [
        ":coat:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧦",
    "emoticons": [],
    "keywords": [
        "` + _lt("socks") + `",
        "` + _lt("stocking") + `"
    ],
    "name": "` + _lt("socks") + `",
    "shortcodes": [
        ":socks:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👗",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("dress") + `",
        "` + _lt("woman’s clothes") + `"
    ],
    "name": "` + _lt("dress") + `",
    "shortcodes": [
        ":dress:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👘",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("kimono") + `"
    ],
    "name": "` + _lt("kimono") + `",
    "shortcodes": [
        ":kimono:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥻",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("dress") + `",
        "` + _lt("sari") + `"
    ],
    "name": "` + _lt("sari") + `",
    "shortcodes": [
        ":sari:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩱",
    "emoticons": [],
    "keywords": [
        "` + _lt("bathing suit") + `",
        "` + _lt("one-piece swimsuit") + `",
        "` + _lt("swimming costume") + `"
    ],
    "name": "` + _lt("one-piece swimsuit") + `",
    "shortcodes": [
        ":one-piece_swimsuit:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩲",
    "emoticons": [],
    "keywords": [
        "` + _lt("bathers") + `",
        "` + _lt("briefs") + `",
        "` + _lt("speedos") + `",
        "` + _lt("underwear") + `",
        "` + _lt("bathing suit") + `",
        "` + _lt("one-piece") + `",
        "` + _lt("swimsuit") + `",
        "` + _lt("pants") + `"
    ],
    "name": "` + _lt("briefs") + `",
    "shortcodes": [
        ":briefs:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩳",
    "emoticons": [],
    "keywords": [
        "` + _lt("bathing suit") + `",
        "` + _lt("boardies") + `",
        "` + _lt("boardshorts") + `",
        "` + _lt("shorts") + `",
        "` + _lt("swim shorts") + `",
        "` + _lt("underwear") + `",
        "` + _lt("pants") + `"
    ],
    "name": "` + _lt("shorts") + `",
    "shortcodes": [
        ":shorts:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👙",
    "emoticons": [],
    "keywords": [
        "` + _lt("bikini") + `",
        "` + _lt("clothing") + `",
        "` + _lt("swim suit") + `",
        "` + _lt("two-piece") + `",
        "` + _lt("swim") + `"
    ],
    "name": "` + _lt("bikini") + `",
    "shortcodes": [
        ":bikini:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👚",
    "emoticons": [],
    "keywords": [
        "` + _lt("blouse") + `",
        "` + _lt("clothing") + `",
        "` + _lt("top") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman’s clothes") + `"
    ],
    "name": "` + _lt("woman’s clothes") + `",
    "shortcodes": [
        ":woman’s_clothes:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👛",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessories") + `",
        "` + _lt("coin") + `",
        "` + _lt("purse") + `",
        "` + _lt("clothing") + `"
    ],
    "name": "` + _lt("purse") + `",
    "shortcodes": [
        ":purse:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👜",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessories") + `",
        "` + _lt("bag") + `",
        "` + _lt("handbag") + `",
        "` + _lt("tote") + `",
        "` + _lt("clothing") + `",
        "` + _lt("purse") + `"
    ],
    "name": "` + _lt("handbag") + `",
    "shortcodes": [
        ":handbag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👝",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessories") + `",
        "` + _lt("bag") + `",
        "` + _lt("clutch bag") + `",
        "` + _lt("pouch") + `",
        "` + _lt("clothing") + `"
    ],
    "name": "` + _lt("clutch bag") + `",
    "shortcodes": [
        ":clutch_bag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛍️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bag") + `",
        "` + _lt("hotel") + `",
        "` + _lt("shopping") + `",
        "` + _lt("shopping bags") + `"
    ],
    "name": "` + _lt("shopping bags") + `",
    "shortcodes": [
        ":shopping_bags:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎒",
    "emoticons": [],
    "keywords": [
        "` + _lt("backpack") + `",
        "` + _lt("bag") + `",
        "` + _lt("rucksack") + `",
        "` + _lt("satchel") + `",
        "` + _lt("school") + `"
    ],
    "name": "` + _lt("backpack") + `",
    "shortcodes": [
        ":backpack:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👞",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("man") + `",
        "` + _lt("man’s shoe") + `",
        "` + _lt("shoe") + `"
    ],
    "name": "` + _lt("man’s shoe") + `",
    "shortcodes": [
        ":man’s_shoe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👟",
    "emoticons": [],
    "keywords": [
        "` + _lt("athletic") + `",
        "` + _lt("clothing") + `",
        "` + _lt("runners") + `",
        "` + _lt("running shoe") + `",
        "` + _lt("shoe") + `",
        "` + _lt("sneaker") + `",
        "` + _lt("trainer") + `"
    ],
    "name": "` + _lt("running shoe") + `",
    "shortcodes": [
        ":running_shoe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥾",
    "emoticons": [],
    "keywords": [
        "` + _lt("backpacking") + `",
        "` + _lt("boot") + `",
        "` + _lt("camping") + `",
        "` + _lt("hiking") + `"
    ],
    "name": "` + _lt("hiking boot") + `",
    "shortcodes": [
        ":hiking_boot:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥿",
    "emoticons": [],
    "keywords": [
        "` + _lt("ballet flat") + `",
        "` + _lt("flat shoe") + `",
        "` + _lt("slip-on") + `",
        "` + _lt("slipper") + `",
        "` + _lt("pump") + `"
    ],
    "name": "` + _lt("flat shoe") + `",
    "shortcodes": [
        ":flat_shoe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👠",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("heel") + `",
        "` + _lt("high-heeled shoe") + `",
        "` + _lt("shoe") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("high-heeled shoe") + `",
    "shortcodes": [
        ":high-heeled_shoe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👡",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("sandal") + `",
        "` + _lt("shoe") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman’s sandal") + `"
    ],
    "name": "` + _lt("woman’s sandal") + `",
    "shortcodes": [
        ":woman’s_sandal:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩰",
    "emoticons": [],
    "keywords": [
        "` + _lt("ballet") + `",
        "` + _lt("ballet shoes") + `",
        "` + _lt("dance") + `"
    ],
    "name": "` + _lt("ballet shoes") + `",
    "shortcodes": [
        ":ballet_shoes:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👢",
    "emoticons": [],
    "keywords": [
        "` + _lt("boot") + `",
        "` + _lt("clothing") + `",
        "` + _lt("shoe") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman’s boot") + `"
    ],
    "name": "` + _lt("woman’s boot") + `",
    "shortcodes": [
        ":woman’s_boot:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👑",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("crown") + `",
        "` + _lt("king") + `",
        "` + _lt("queen") + `"
    ],
    "name": "` + _lt("crown") + `",
    "shortcodes": [
        ":crown:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👒",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("hat") + `",
        "` + _lt("woman") + `",
        "` + _lt("woman’s hat") + `"
    ],
    "name": "` + _lt("woman’s hat") + `",
    "shortcodes": [
        ":woman’s_hat:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎩",
    "emoticons": [],
    "keywords": [
        "` + _lt("clothing") + `",
        "` + _lt("hat") + `",
        "` + _lt("top") + `",
        "` + _lt("tophat") + `"
    ],
    "name": "` + _lt("top hat") + `",
    "shortcodes": [
        ":top_hat:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎓",
    "emoticons": [],
    "keywords": [
        "` + _lt("cap") + `",
        "` + _lt("celebration") + `",
        "` + _lt("clothing") + `",
        "` + _lt("graduation") + `",
        "` + _lt("hat") + `"
    ],
    "name": "` + _lt("graduation cap") + `",
    "shortcodes": [
        ":graduation_cap:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧢",
    "emoticons": [],
    "keywords": [
        "` + _lt("baseball cap") + `",
        "` + _lt("billed cap") + `"
    ],
    "name": "` + _lt("billed cap") + `",
    "shortcodes": [
        ":billed_cap:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⛑️",
    "emoticons": [],
    "keywords": [
        "` + _lt("aid") + `",
        "` + _lt("cross") + `",
        "` + _lt("face") + `",
        "` + _lt("hat") + `",
        "` + _lt("helmet") + `",
        "` + _lt("rescue worker’s helmet") + `"
    ],
    "name": "` + _lt("rescue worker’s helmet") + `",
    "shortcodes": [
        ":rescue_worker’s_helmet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📿",
    "emoticons": [],
    "keywords": [
        "` + _lt("beads") + `",
        "` + _lt("clothing") + `",
        "` + _lt("necklace") + `",
        "` + _lt("prayer") + `",
        "` + _lt("religion") + `"
    ],
    "name": "` + _lt("prayer beads") + `",
    "shortcodes": [
        ":prayer_beads:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💄",
    "emoticons": [],
    "keywords": [
        "` + _lt("cosmetics") + `",
        "` + _lt("lipstick") + `",
        "` + _lt("make-up") + `",
        "` + _lt("makeup") + `"
    ],
    "name": "` + _lt("lipstick") + `",
    "shortcodes": [
        ":lipstick:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💍",
    "emoticons": [],
    "keywords": [
        "` + _lt("diamond") + `",
        "` + _lt("ring") + `"
    ],
    "name": "` + _lt("ring") + `",
    "shortcodes": [
        ":ring:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💎",
    "emoticons": [],
    "keywords": [
        "` + _lt("diamond") + `",
        "` + _lt("gem") + `",
        "` + _lt("gem stone") + `",
        "` + _lt("jewel") + `",
        "` + _lt("gemstone") + `"
    ],
    "name": "` + _lt("gem stone") + `",
    "shortcodes": [
        ":gem_stone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔇",
    "emoticons": [],
    "keywords": [
        "` + _lt("mute") + `",
        "` + _lt("muted speaker") + `",
        "` + _lt("quiet") + `",
        "` + _lt("silent") + `",
        "` + _lt("speaker") + `"
    ],
    "name": "` + _lt("muted speaker") + `",
    "shortcodes": [
        ":muted_speaker:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔈",
    "emoticons": [],
    "keywords": [
        "` + _lt("low") + `",
        "` + _lt("quiet") + `",
        "` + _lt("soft") + `",
        "` + _lt("speaker") + `",
        "` + _lt("volume") + `",
        "` + _lt("speaker low volume") + `"
    ],
    "name": "` + _lt("speaker low volume") + `",
    "shortcodes": [
        ":speaker_low_volume:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔉",
    "emoticons": [],
    "keywords": [
        "` + _lt("medium") + `",
        "` + _lt("speaker medium volume") + `"
    ],
    "name": "` + _lt("speaker medium volume") + `",
    "shortcodes": [
        ":speaker_medium_volume:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔊",
    "emoticons": [],
    "keywords": [
        "` + _lt("loud") + `",
        "` + _lt("speaker high volume") + `"
    ],
    "name": "` + _lt("speaker high volume") + `",
    "shortcodes": [
        ":speaker_high_volume:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📢",
    "emoticons": [],
    "keywords": [
        "` + _lt("loud") + `",
        "` + _lt("loudspeaker") + `",
        "` + _lt("public address") + `"
    ],
    "name": "` + _lt("loudspeaker") + `",
    "shortcodes": [
        ":loudspeaker:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📣",
    "emoticons": [],
    "keywords": [
        "` + _lt("cheering") + `",
        "` + _lt("megaphone") + `"
    ],
    "name": "` + _lt("megaphone") + `",
    "shortcodes": [
        ":megaphone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📯",
    "emoticons": [
        ":postal_horn"
    ],
    "keywords": [
        "` + _lt("horn") + `",
        "` + _lt("post") + `",
        "` + _lt("postal") + `"
    ],
    "name": "` + _lt("postal horn") + `",
    "shortcodes": [
        ":postal_horn:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔔",
    "emoticons": [],
    "keywords": [
        "` + _lt("bell") + `"
    ],
    "name": "` + _lt("bell") + `",
    "shortcodes": [
        ":bell:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔕",
    "emoticons": [],
    "keywords": [
        "` + _lt("bell") + `",
        "` + _lt("bell with slash") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("mute") + `",
        "` + _lt("quiet") + `",
        "` + _lt("silent") + `"
    ],
    "name": "` + _lt("bell with slash") + `",
    "shortcodes": [
        ":bell_with_slash:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎼",
    "emoticons": [],
    "keywords": [
        "` + _lt("music") + `",
        "` + _lt("musical score") + `",
        "` + _lt("score") + `"
    ],
    "name": "` + _lt("musical score") + `",
    "shortcodes": [
        ":musical_score:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎵",
    "emoticons": [
        ":music"
    ],
    "keywords": [
        "` + _lt("music") + `",
        "` + _lt("musical note") + `",
        "` + _lt("note") + `"
    ],
    "name": "` + _lt("musical note") + `",
    "shortcodes": [
        ":musical_note:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎶",
    "emoticons": [],
    "keywords": [
        "` + _lt("music") + `",
        "` + _lt("musical notes") + `",
        "` + _lt("note") + `",
        "` + _lt("notes") + `"
    ],
    "name": "` + _lt("musical notes") + `",
    "shortcodes": [
        ":musical_notes:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎙️",
    "emoticons": [],
    "keywords": [
        "` + _lt("mic") + `",
        "` + _lt("microphone") + `",
        "` + _lt("music") + `",
        "` + _lt("studio") + `"
    ],
    "name": "` + _lt("studio microphone") + `",
    "shortcodes": [
        ":studio_microphone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎚️",
    "emoticons": [],
    "keywords": [
        "` + _lt("level") + `",
        "` + _lt("music") + `",
        "` + _lt("slider") + `"
    ],
    "name": "` + _lt("level slider") + `",
    "shortcodes": [
        ":level_slider:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎛️",
    "emoticons": [],
    "keywords": [
        "` + _lt("control") + `",
        "` + _lt("knobs") + `",
        "` + _lt("music") + `"
    ],
    "name": "` + _lt("control knobs") + `",
    "shortcodes": [
        ":control_knobs:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎤",
    "emoticons": [
        ":microphone"
    ],
    "keywords": [
        "` + _lt("karaoke") + `",
        "` + _lt("mic") + `",
        "` + _lt("microphone") + `"
    ],
    "name": "` + _lt("microphone") + `",
    "shortcodes": [
        ":microphone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎧",
    "emoticons": [],
    "keywords": [
        "` + _lt("earbud") + `",
        "` + _lt("headphone") + `"
    ],
    "name": "` + _lt("headphone") + `",
    "shortcodes": [
        ":headphone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📻",
    "emoticons": [],
    "keywords": [
        "` + _lt("AM") + `",
        "` + _lt("FM") + `",
        "` + _lt("radio") + `",
        "` + _lt("wireless") + `",
        "` + _lt("video") + `"
    ],
    "name": "` + _lt("radio") + `",
    "shortcodes": [
        ":radio:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎷",
    "emoticons": [],
    "keywords": [
        "` + _lt("instrument") + `",
        "` + _lt("music") + `",
        "` + _lt("sax") + `",
        "` + _lt("saxophone") + `"
    ],
    "name": "` + _lt("saxophone") + `",
    "shortcodes": [
        ":saxophone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎸",
    "emoticons": [
        ":guitar"
    ],
    "keywords": [
        "` + _lt("guitar") + `",
        "` + _lt("instrument") + `",
        "` + _lt("music") + `"
    ],
    "name": "` + _lt("guitar") + `",
    "shortcodes": [
        ":guitar:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎹",
    "emoticons": [],
    "keywords": [
        "` + _lt("instrument") + `",
        "` + _lt("keyboard") + `",
        "` + _lt("music") + `",
        "` + _lt("musical keyboard") + `",
        "` + _lt("organ") + `",
        "` + _lt("piano") + `"
    ],
    "name": "` + _lt("musical keyboard") + `",
    "shortcodes": [
        ":musical_keyboard:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎺",
    "emoticons": [
        ":trumpet"
    ],
    "keywords": [
        "` + _lt("instrument") + `",
        "` + _lt("music") + `",
        "` + _lt("trumpet") + `"
    ],
    "name": "` + _lt("trumpet") + `",
    "shortcodes": [
        ":trumpet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎻",
    "emoticons": [],
    "keywords": [
        "` + _lt("instrument") + `",
        "` + _lt("music") + `",
        "` + _lt("violin") + `"
    ],
    "name": "` + _lt("violin") + `",
    "shortcodes": [
        ":violin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪕",
    "emoticons": [],
    "keywords": [
        "` + _lt("banjo") + `",
        "` + _lt("music") + `",
        "` + _lt("stringed") + `"
    ],
    "name": "` + _lt("banjo") + `",
    "shortcodes": [
        ":banjo:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥁",
    "emoticons": [],
    "keywords": [
        "` + _lt("drum") + `",
        "` + _lt("drumsticks") + `",
        "` + _lt("music") + `",
        "` + _lt("percussions") + `"
    ],
    "name": "` + _lt("drum") + `",
    "shortcodes": [
        ":drum:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📱",
    "emoticons": [],
    "keywords": [
        "` + _lt("cell") + `",
        "` + _lt("mobile") + `",
        "` + _lt("phone") + `",
        "` + _lt("telephone") + `"
    ],
    "name": "` + _lt("mobile phone") + `",
    "shortcodes": [
        ":mobile_phone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📲",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("cell") + `",
        "` + _lt("mobile") + `",
        "` + _lt("mobile phone with arrow") + `",
        "` + _lt("phone") + `",
        "` + _lt("receive") + `"
    ],
    "name": "` + _lt("mobile phone with arrow") + `",
    "shortcodes": [
        ":mobile_phone_with_arrow:"
    ]
},
{
    "category": "Objects",
    "codepoints": "☎️",
    "emoticons": [],
    "keywords": [
        "` + _lt("landline") + `",
        "` + _lt("phone") + `",
        "` + _lt("telephone") + `"
    ],
    "name": "` + _lt("telephone") + `",
    "shortcodes": [
        ":telephone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📞",
    "emoticons": [],
    "keywords": [
        "` + _lt("phone") + `",
        "` + _lt("receiver") + `",
        "` + _lt("telephone") + `"
    ],
    "name": "` + _lt("telephone receiver") + `",
    "shortcodes": [
        ":telephone_receiver:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📟",
    "emoticons": [],
    "keywords": [
        "` + _lt("pager") + `"
    ],
    "name": "` + _lt("pager") + `",
    "shortcodes": [
        ":pager:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📠",
    "emoticons": [],
    "keywords": [
        "` + _lt("fax") + `",
        "` + _lt("fax machine") + `"
    ],
    "name": "` + _lt("fax machine") + `",
    "shortcodes": [
        ":fax_machine:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔋",
    "emoticons": [],
    "keywords": [
        "` + _lt("battery") + `"
    ],
    "name": "` + _lt("battery") + `",
    "shortcodes": [
        ":battery:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔌",
    "emoticons": [],
    "keywords": [
        "` + _lt("electric") + `",
        "` + _lt("electricity") + `",
        "` + _lt("plug") + `"
    ],
    "name": "` + _lt("electric plug") + `",
    "shortcodes": [
        ":electric_plug:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💻",
    "emoticons": [],
    "keywords": [
        "` + _lt("computer") + `",
        "` + _lt("laptop") + `",
        "` + _lt("PC") + `",
        "` + _lt("personal") + `",
        "` + _lt("pc") + `"
    ],
    "name": "` + _lt("laptop") + `",
    "shortcodes": [
        ":laptop:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖥️",
    "emoticons": [],
    "keywords": [
        "` + _lt("computer") + `",
        "` + _lt("desktop") + `"
    ],
    "name": "` + _lt("desktop computer") + `",
    "shortcodes": [
        ":desktop_computer:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖨️",
    "emoticons": [],
    "keywords": [
        "` + _lt("computer") + `",
        "` + _lt("printer") + `"
    ],
    "name": "` + _lt("printer") + `",
    "shortcodes": [
        ":printer:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⌨️",
    "emoticons": [],
    "keywords": [
        "` + _lt("computer") + `",
        "` + _lt("keyboard") + `"
    ],
    "name": "` + _lt("keyboard") + `",
    "shortcodes": [
        ":keyboard:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖱️",
    "emoticons": [],
    "keywords": [
        "` + _lt("computer") + `",
        "` + _lt("computer mouse") + `"
    ],
    "name": "` + _lt("computer mouse") + `",
    "shortcodes": [
        ":computer_mouse:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖲️",
    "emoticons": [],
    "keywords": [
        "` + _lt("computer") + `",
        "` + _lt("trackball") + `"
    ],
    "name": "` + _lt("trackball") + `",
    "shortcodes": [
        ":trackball:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💽",
    "emoticons": [],
    "keywords": [
        "` + _lt("computer") + `",
        "` + _lt("disk") + `",
        "` + _lt("minidisk") + `",
        "` + _lt("optical") + `"
    ],
    "name": "` + _lt("computer disk") + `",
    "shortcodes": [
        ":computer_disk:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💾",
    "emoticons": [],
    "keywords": [
        "` + _lt("computer") + `",
        "` + _lt("disk") + `",
        "` + _lt("diskette") + `",
        "` + _lt("floppy") + `"
    ],
    "name": "` + _lt("floppy disk") + `",
    "shortcodes": [
        ":floppy_disk:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💿",
    "emoticons": [],
    "keywords": [
        "` + _lt("CD") + `",
        "` + _lt("computer") + `",
        "` + _lt("disk") + `",
        "` + _lt("optical") + `"
    ],
    "name": "` + _lt("optical disk") + `",
    "shortcodes": [
        ":optical_disk:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📀",
    "emoticons": [],
    "keywords": [
        "` + _lt("blu-ray") + `",
        "` + _lt("computer") + `",
        "` + _lt("disk") + `",
        "` + _lt("dvd") + `",
        "` + _lt("DVD") + `",
        "` + _lt("optical") + `",
        "` + _lt("Blu-ray") + `"
    ],
    "name": "` + _lt("dvd") + `",
    "shortcodes": [
        ":dvd:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧮",
    "emoticons": [],
    "keywords": [
        "` + _lt("abacus") + `",
        "` + _lt("calculation") + `"
    ],
    "name": "` + _lt("abacus") + `",
    "shortcodes": [
        ":abacus:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎥",
    "emoticons": [],
    "keywords": [
        "` + _lt("camera") + `",
        "` + _lt("cinema") + `",
        "` + _lt("movie") + `"
    ],
    "name": "` + _lt("movie camera") + `",
    "shortcodes": [
        ":movie_camera:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎞️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cinema") + `",
        "` + _lt("film") + `",
        "` + _lt("frames") + `",
        "` + _lt("movie") + `"
    ],
    "name": "` + _lt("film frames") + `",
    "shortcodes": [
        ":film_frames:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📽️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cinema") + `",
        "` + _lt("film") + `",
        "` + _lt("movie") + `",
        "` + _lt("projector") + `",
        "` + _lt("video") + `"
    ],
    "name": "` + _lt("film projector") + `",
    "shortcodes": [
        ":film_projector:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎬",
    "emoticons": [
        ":clapper"
    ],
    "keywords": [
        "` + _lt("clapper") + `",
        "` + _lt("clapper board") + `",
        "` + _lt("clapperboard") + `",
        "` + _lt("film") + `",
        "` + _lt("movie") + `"
    ],
    "name": "` + _lt("clapper board") + `",
    "shortcodes": [
        ":clapper_board:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📺",
    "emoticons": [],
    "keywords": [
        "` + _lt("television") + `",
        "` + _lt("TV") + `",
        "` + _lt("video") + `",
        "` + _lt("tv") + `"
    ],
    "name": "` + _lt("television") + `",
    "shortcodes": [
        ":television:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📷",
    "emoticons": [],
    "keywords": [
        "` + _lt("camera") + `",
        "` + _lt("video") + `"
    ],
    "name": "` + _lt("camera") + `",
    "shortcodes": [
        ":camera:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📸",
    "emoticons": [],
    "keywords": [
        "` + _lt("camera") + `",
        "` + _lt("camera with flash") + `",
        "` + _lt("flash") + `",
        "` + _lt("video") + `"
    ],
    "name": "` + _lt("camera with flash") + `",
    "shortcodes": [
        ":camera_with_flash:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📹",
    "emoticons": [],
    "keywords": [
        "` + _lt("camera") + `",
        "` + _lt("video") + `"
    ],
    "name": "` + _lt("video camera") + `",
    "shortcodes": [
        ":video_camera:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📼",
    "emoticons": [],
    "keywords": [
        "` + _lt("tape") + `",
        "` + _lt("VHS") + `",
        "` + _lt("video") + `",
        "` + _lt("videocassette") + `",
        "` + _lt("vhs") + `"
    ],
    "name": "` + _lt("videocassette") + `",
    "shortcodes": [
        ":videocassette:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔍",
    "emoticons": [],
    "keywords": [
        "` + _lt("glass") + `",
        "` + _lt("magnifying") + `",
        "` + _lt("magnifying glass tilted left") + `",
        "` + _lt("search") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("magnifying glass tilted left") + `",
    "shortcodes": [
        ":magnifying_glass_ltilted_left:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔎",
    "emoticons": [],
    "keywords": [
        "` + _lt("glass") + `",
        "` + _lt("magnifying") + `",
        "` + _lt("magnifying glass tilted right") + `",
        "` + _lt("search") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("magnifying glass tilted right") + `",
    "shortcodes": [
        ":magnifying_glass_ltilted_right:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🕯️",
    "emoticons": [],
    "keywords": [
        "` + _lt("candle") + `",
        "` + _lt("light") + `"
    ],
    "name": "` + _lt("candle") + `",
    "shortcodes": [
        ":candle:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💡",
    "emoticons": [],
    "keywords": [
        "` + _lt("bulb") + `",
        "` + _lt("comic") + `",
        "` + _lt("electric") + `",
        "` + _lt("globe") + `",
        "` + _lt("idea") + `",
        "` + _lt("light") + `"
    ],
    "name": "` + _lt("light bulb") + `",
    "shortcodes": [
        ":light_bulb:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔦",
    "emoticons": [],
    "keywords": [
        "` + _lt("electric") + `",
        "` + _lt("flashlight") + `",
        "` + _lt("light") + `",
        "` + _lt("tool") + `",
        "` + _lt("torch") + `"
    ],
    "name": "` + _lt("flashlight") + `",
    "shortcodes": [
        ":flashlight:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🏮",
    "emoticons": [],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("lantern") + `",
        "` + _lt("light") + `",
        "` + _lt("red") + `",
        "` + _lt("red paper lantern") + `"
    ],
    "name": "` + _lt("red paper lantern") + `",
    "shortcodes": [
        ":red_paper_lantern:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪔",
    "emoticons": [],
    "keywords": [
        "` + _lt("diya") + `",
        "` + _lt("lamp") + `",
        "` + _lt("oil") + `"
    ],
    "name": "` + _lt("diya lamp") + `",
    "shortcodes": [
        ":diya_lamp:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📔",
    "emoticons": [],
    "keywords": [
        "` + _lt("book") + `",
        "` + _lt("cover") + `",
        "` + _lt("decorated") + `",
        "` + _lt("notebook") + `",
        "` + _lt("notebook with decorative cover") + `"
    ],
    "name": "` + _lt("notebook with decorative cover") + `",
    "shortcodes": [
        ":notebook_with_decorative_cover:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📕",
    "emoticons": [],
    "keywords": [
        "` + _lt("book") + `",
        "` + _lt("closed") + `"
    ],
    "name": "` + _lt("closed book") + `",
    "shortcodes": [
        ":closed_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📖",
    "emoticons": [],
    "keywords": [
        "` + _lt("book") + `",
        "` + _lt("open") + `"
    ],
    "name": "` + _lt("open book") + `",
    "shortcodes": [
        ":open_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📗",
    "emoticons": [],
    "keywords": [
        "` + _lt("book") + `",
        "` + _lt("green") + `"
    ],
    "name": "` + _lt("green book") + `",
    "shortcodes": [
        ":green_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📘",
    "emoticons": [],
    "keywords": [
        "` + _lt("blue") + `",
        "` + _lt("book") + `"
    ],
    "name": "` + _lt("blue book") + `",
    "shortcodes": [
        ":blue_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📙",
    "emoticons": [],
    "keywords": [
        "` + _lt("book") + `",
        "` + _lt("orange") + `"
    ],
    "name": "` + _lt("orange book") + `",
    "shortcodes": [
        ":orange_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📚",
    "emoticons": [],
    "keywords": [
        "` + _lt("book") + `",
        "` + _lt("books") + `"
    ],
    "name": "` + _lt("books") + `",
    "shortcodes": [
        ":books:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📓",
    "emoticons": [],
    "keywords": [
        "` + _lt("notebook") + `"
    ],
    "name": "` + _lt("notebook") + `",
    "shortcodes": [
        ":notebook:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📒",
    "emoticons": [],
    "keywords": [
        "` + _lt("ledger") + `",
        "` + _lt("notebook") + `"
    ],
    "name": "` + _lt("ledger") + `",
    "shortcodes": [
        ":ledger:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📃",
    "emoticons": [],
    "keywords": [
        "` + _lt("curl") + `",
        "` + _lt("document") + `",
        "` + _lt("page") + `",
        "` + _lt("page with curl") + `"
    ],
    "name": "` + _lt("page with curl") + `",
    "shortcodes": [
        ":page_with_curl:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📜",
    "emoticons": [],
    "keywords": [
        "` + _lt("paper") + `",
        "` + _lt("scroll") + `"
    ],
    "name": "` + _lt("scroll") + `",
    "shortcodes": [
        ":scroll:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📄",
    "emoticons": [],
    "keywords": [
        "` + _lt("document") + `",
        "` + _lt("page") + `",
        "` + _lt("page facing up") + `"
    ],
    "name": "` + _lt("page facing up") + `",
    "shortcodes": [
        ":page_facing_up:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📰",
    "emoticons": [],
    "keywords": [
        "` + _lt("news") + `",
        "` + _lt("newspaper") + `",
        "` + _lt("paper") + `"
    ],
    "name": "` + _lt("newspaper") + `",
    "shortcodes": [
        ":newspaper:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗞️",
    "emoticons": [],
    "keywords": [
        "` + _lt("news") + `",
        "` + _lt("newspaper") + `",
        "` + _lt("paper") + `",
        "` + _lt("rolled") + `",
        "` + _lt("rolled-up newspaper") + `"
    ],
    "name": "` + _lt("rolled-up newspaper") + `",
    "shortcodes": [
        ":rolled-up_newspaper:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📑",
    "emoticons": [],
    "keywords": [
        "` + _lt("bookmark") + `",
        "` + _lt("mark") + `",
        "` + _lt("marker") + `",
        "` + _lt("tabs") + `"
    ],
    "name": "` + _lt("bookmark tabs") + `",
    "shortcodes": [
        ":bookmark_ltabs:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔖",
    "emoticons": [],
    "keywords": [
        "` + _lt("bookmark") + `",
        "` + _lt("mark") + `"
    ],
    "name": "` + _lt("bookmark") + `",
    "shortcodes": [
        ":bookmark:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🏷️",
    "emoticons": [],
    "keywords": [
        "` + _lt("label") + `"
    ],
    "name": "` + _lt("label") + `",
    "shortcodes": [
        ":label:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💰",
    "emoticons": [],
    "keywords": [
        "` + _lt("bag") + `",
        "` + _lt("dollar") + `",
        "` + _lt("money") + `",
        "` + _lt("moneybag") + `"
    ],
    "name": "` + _lt("money bag") + `",
    "shortcodes": [
        ":money_bag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💴",
    "emoticons": [],
    "keywords": [
        "` + _lt("banknote") + `",
        "` + _lt("bill") + `",
        "` + _lt("currency") + `",
        "` + _lt("money") + `",
        "` + _lt("note") + `",
        "` + _lt("yen") + `"
    ],
    "name": "` + _lt("yen banknote") + `",
    "shortcodes": [
        ":yen_banknote:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💵",
    "emoticons": [],
    "keywords": [
        "` + _lt("banknote") + `",
        "` + _lt("bill") + `",
        "` + _lt("currency") + `",
        "` + _lt("dollar") + `",
        "` + _lt("money") + `",
        "` + _lt("note") + `"
    ],
    "name": "` + _lt("dollar banknote") + `",
    "shortcodes": [
        ":dollar_banknote:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💶",
    "emoticons": [],
    "keywords": [
        "` + _lt("banknote") + `",
        "` + _lt("bill") + `",
        "` + _lt("currency") + `",
        "` + _lt("euro") + `",
        "` + _lt("money") + `",
        "` + _lt("note") + `"
    ],
    "name": "` + _lt("euro banknote") + `",
    "shortcodes": [
        ":euro_banknote:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💷",
    "emoticons": [],
    "keywords": [
        "` + _lt("banknote") + `",
        "` + _lt("bill") + `",
        "` + _lt("currency") + `",
        "` + _lt("money") + `",
        "` + _lt("note") + `",
        "` + _lt("pound") + `",
        "` + _lt("sterling") + `"
    ],
    "name": "` + _lt("pound banknote") + `",
    "shortcodes": [
        ":pound_banknote:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💸",
    "emoticons": [],
    "keywords": [
        "` + _lt("banknote") + `",
        "` + _lt("bill") + `",
        "` + _lt("fly") + `",
        "` + _lt("money") + `",
        "` + _lt("money with wings") + `",
        "` + _lt("wings") + `"
    ],
    "name": "` + _lt("money with wings") + `",
    "shortcodes": [
        ":money_with_wings:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💳",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("credit") + `",
        "` + _lt("money") + `"
    ],
    "name": "` + _lt("credit card") + `",
    "shortcodes": [
        ":credit_card:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧾",
    "emoticons": [],
    "keywords": [
        "` + _lt("accounting") + `",
        "` + _lt("bookkeeping") + `",
        "` + _lt("evidence") + `",
        "` + _lt("proof") + `",
        "` + _lt("receipt") + `"
    ],
    "name": "` + _lt("receipt") + `",
    "shortcodes": [
        ":receipt:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💹",
    "emoticons": [],
    "keywords": [
        "` + _lt("chart") + `",
        "` + _lt("chart increasing with yen") + `",
        "` + _lt("graph") + `",
        "` + _lt("graph increasing with yen") + `",
        "` + _lt("growth") + `",
        "` + _lt("money") + `",
        "` + _lt("yen") + `"
    ],
    "name": "` + _lt("chart increasing with yen") + `",
    "shortcodes": [
        ":chart_increasing_with_yen:"
    ]
},
{
    "category": "Objects",
    "codepoints": "✉️",
    "emoticons": [],
    "keywords": [
        "` + _lt("email") + `",
        "` + _lt("envelope") + `",
        "` + _lt("letter") + `",
        "` + _lt("e-mail") + `"
    ],
    "name": "` + _lt("envelope") + `",
    "shortcodes": [
        ":envelope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📧",
    "emoticons": [],
    "keywords": [
        "` + _lt("e-mail") + `",
        "` + _lt("email") + `",
        "` + _lt("letter") + `",
        "` + _lt("mail") + `"
    ],
    "name": "` + _lt("e-mail") + `",
    "shortcodes": [
        ":e-mail:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📨",
    "emoticons": [],
    "keywords": [
        "` + _lt("e-mail") + `",
        "` + _lt("email") + `",
        "` + _lt("envelope") + `",
        "` + _lt("incoming") + `",
        "` + _lt("letter") + `",
        "` + _lt("receive") + `"
    ],
    "name": "` + _lt("incoming envelope") + `",
    "shortcodes": [
        ":incoming_envelope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📩",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("e-mail") + `",
        "` + _lt("email") + `",
        "` + _lt("envelope") + `",
        "` + _lt("envelope with arrow") + `",
        "` + _lt("outgoing") + `"
    ],
    "name": "` + _lt("envelope with arrow") + `",
    "shortcodes": [
        ":envelope_with_arrow:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📤",
    "emoticons": [],
    "keywords": [
        "` + _lt("box") + `",
        "` + _lt("letter") + `",
        "` + _lt("mail") + `",
        "` + _lt("out tray") + `",
        "` + _lt("outbox") + `",
        "` + _lt("sent") + `",
        "` + _lt("tray") + `"
    ],
    "name": "` + _lt("outbox tray") + `",
    "shortcodes": [
        ":outbox_ltray:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📥",
    "emoticons": [],
    "keywords": [
        "` + _lt("box") + `",
        "` + _lt("in tray") + `",
        "` + _lt("inbox") + `",
        "` + _lt("letter") + `",
        "` + _lt("mail") + `",
        "` + _lt("receive") + `",
        "` + _lt("tray") + `"
    ],
    "name": "` + _lt("inbox tray") + `",
    "shortcodes": [
        ":inbox_ltray:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📦",
    "emoticons": [],
    "keywords": [
        "` + _lt("box") + `",
        "` + _lt("package") + `",
        "` + _lt("parcel") + `"
    ],
    "name": "` + _lt("package") + `",
    "shortcodes": [
        ":package:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📫",
    "emoticons": [],
    "keywords": [
        "` + _lt("closed") + `",
        "` + _lt("closed letterbox with raised flag") + `",
        "` + _lt("mail") + `",
        "` + _lt("mailbox") + `",
        "` + _lt("postbox") + `",
        "` + _lt("closed mailbox with raised flag") + `",
        "` + _lt("closed postbox with raised flag") + `",
        "` + _lt("letterbox") + `",
        "` + _lt("post") + `",
        "` + _lt("post box") + `"
    ],
    "name": "` + _lt("closed mailbox with raised flag") + `",
    "shortcodes": [
        ":closed_mailbox_with_raised_flag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📪",
    "emoticons": [],
    "keywords": [
        "` + _lt("closed") + `",
        "` + _lt("closed letterbox with lowered flag") + `",
        "` + _lt("lowered") + `",
        "` + _lt("mail") + `",
        "` + _lt("mailbox") + `",
        "` + _lt("postbox") + `",
        "` + _lt("closed mailbox with lowered flag") + `",
        "` + _lt("closed postbox with lowered flag") + `",
        "` + _lt("letterbox") + `",
        "` + _lt("post box") + `",
        "` + _lt("post") + `"
    ],
    "name": "` + _lt("closed mailbox with lowered flag") + `",
    "shortcodes": [
        ":closed_mailbox_with_lowered_flag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📬",
    "emoticons": [],
    "keywords": [
        "` + _lt("mail") + `",
        "` + _lt("mailbox") + `",
        "` + _lt("open") + `",
        "` + _lt("open letterbox with raised flag") + `",
        "` + _lt("postbox") + `",
        "` + _lt("open mailbox with raised flag") + `",
        "` + _lt("open postbox with raised flag") + `",
        "` + _lt("post") + `",
        "` + _lt("post box") + `"
    ],
    "name": "` + _lt("open mailbox with raised flag") + `",
    "shortcodes": [
        ":open_mailbox_with_raised_flag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📭",
    "emoticons": [],
    "keywords": [
        "` + _lt("lowered") + `",
        "` + _lt("mail") + `",
        "` + _lt("mailbox") + `",
        "` + _lt("open") + `",
        "` + _lt("open letterbox with lowered flag") + `",
        "` + _lt("postbox") + `",
        "` + _lt("open mailbox with lowered flag") + `",
        "` + _lt("open postbox with lowered flag") + `",
        "` + _lt("post") + `",
        "` + _lt("post box") + `"
    ],
    "name": "` + _lt("open mailbox with lowered flag") + `",
    "shortcodes": [
        ":open_mailbox_with_lowered_flag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📮",
    "emoticons": [],
    "keywords": [
        "` + _lt("mail") + `",
        "` + _lt("mailbox") + `",
        "` + _lt("postbox") + `",
        "` + _lt("post") + `",
        "` + _lt("post box") + `"
    ],
    "name": "` + _lt("postbox") + `",
    "shortcodes": [
        ":postbox:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗳️",
    "emoticons": [],
    "keywords": [
        "` + _lt("ballot") + `",
        "` + _lt("ballot box with ballot") + `",
        "` + _lt("box") + `"
    ],
    "name": "` + _lt("ballot box with ballot") + `",
    "shortcodes": [
        ":ballot_box_with_ballot:"
    ]
},
{
    "category": "Objects",
    "codepoints": "✏️",
    "emoticons": [],
    "keywords": [
        "` + _lt("pencil") + `"
    ],
    "name": "` + _lt("pencil") + `",
    "shortcodes": [
        ":pencil:"
    ]
},
{
    "category": "Objects",
    "codepoints": "✒️",
    "emoticons": [],
    "keywords": [
        "` + _lt("black nib") + `",
        "` + _lt("nib") + `",
        "` + _lt("pen") + `"
    ],
    "name": "` + _lt("black nib") + `",
    "shortcodes": [
        ":black_nib:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖋️",
    "emoticons": [],
    "keywords": [
        "` + _lt("fountain") + `",
        "` + _lt("pen") + `"
    ],
    "name": "` + _lt("fountain pen") + `",
    "shortcodes": [
        ":fountain_pen:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖊️",
    "emoticons": [],
    "keywords": [
        "` + _lt("ballpoint") + `",
        "` + _lt("pen") + `"
    ],
    "name": "` + _lt("pen") + `",
    "shortcodes": [
        ":pen:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖌️",
    "emoticons": [],
    "keywords": [
        "` + _lt("paintbrush") + `",
        "` + _lt("painting") + `"
    ],
    "name": "` + _lt("paintbrush") + `",
    "shortcodes": [
        ":paintbrush:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖍️",
    "emoticons": [],
    "keywords": [
        "` + _lt("crayon") + `"
    ],
    "name": "` + _lt("crayon") + `",
    "shortcodes": [
        ":crayon:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📝",
    "emoticons": [],
    "keywords": [
        "` + _lt("memo") + `",
        "` + _lt("pencil") + `"
    ],
    "name": "` + _lt("memo") + `",
    "shortcodes": [
        ":memo:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💼",
    "emoticons": [],
    "keywords": [
        "` + _lt("briefcase") + `"
    ],
    "name": "` + _lt("briefcase") + `",
    "shortcodes": [
        ":briefcase:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📁",
    "emoticons": [],
    "keywords": [
        "` + _lt("file") + `",
        "` + _lt("folder") + `"
    ],
    "name": "` + _lt("file folder") + `",
    "shortcodes": [
        ":file_folder:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📂",
    "emoticons": [],
    "keywords": [
        "` + _lt("file") + `",
        "` + _lt("folder") + `",
        "` + _lt("open") + `"
    ],
    "name": "` + _lt("open file folder") + `",
    "shortcodes": [
        ":open_file_folder:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("dividers") + `",
        "` + _lt("index") + `"
    ],
    "name": "` + _lt("card index dividers") + `",
    "shortcodes": [
        ":card_index_dividers:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📅",
    "emoticons": [],
    "keywords": [
        "` + _lt("calendar") + `",
        "` + _lt("date") + `"
    ],
    "name": "` + _lt("calendar") + `",
    "shortcodes": [
        ":calendar:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📆",
    "emoticons": [],
    "keywords": [
        "` + _lt("calendar") + `",
        "` + _lt("tear-off calendar") + `"
    ],
    "name": "` + _lt("tear-off calendar") + `",
    "shortcodes": [
        ":tear-off_calendar:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗒️",
    "emoticons": [],
    "keywords": [
        "` + _lt("note") + `",
        "` + _lt("pad") + `",
        "` + _lt("spiral") + `",
        "` + _lt("spiral notepad") + `"
    ],
    "name": "` + _lt("spiral notepad") + `",
    "shortcodes": [
        ":spiral_notepad:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗓️",
    "emoticons": [],
    "keywords": [
        "` + _lt("calendar") + `",
        "` + _lt("pad") + `",
        "` + _lt("spiral") + `"
    ],
    "name": "` + _lt("spiral calendar") + `",
    "shortcodes": [
        ":spiral_calendar:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📇",
    "emoticons": [],
    "keywords": [
        "` + _lt("card") + `",
        "` + _lt("index") + `",
        "` + _lt("rolodex") + `"
    ],
    "name": "` + _lt("card index") + `",
    "shortcodes": [
        ":card_index:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📈",
    "emoticons": [],
    "keywords": [
        "` + _lt("chart") + `",
        "` + _lt("chart increasing") + `",
        "` + _lt("graph") + `",
        "` + _lt("graph increasing") + `",
        "` + _lt("growth") + `",
        "` + _lt("trend") + `",
        "` + _lt("upward") + `"
    ],
    "name": "` + _lt("chart increasing") + `",
    "shortcodes": [
        ":chart_increasing:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📉",
    "emoticons": [],
    "keywords": [
        "` + _lt("chart") + `",
        "` + _lt("chart decreasing") + `",
        "` + _lt("down") + `",
        "` + _lt("graph") + `",
        "` + _lt("graph decreasing") + `",
        "` + _lt("trend") + `"
    ],
    "name": "` + _lt("chart decreasing") + `",
    "shortcodes": [
        ":chart_decreasing:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📊",
    "emoticons": [],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("chart") + `",
        "` + _lt("graph") + `"
    ],
    "name": "` + _lt("bar chart") + `",
    "shortcodes": [
        ":bar_chart:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📋",
    "emoticons": [],
    "keywords": [
        "` + _lt("clipboard") + `"
    ],
    "name": "` + _lt("clipboard") + `",
    "shortcodes": [
        ":clipboard:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📌",
    "emoticons": [
        ":pin"
    ],
    "keywords": [
        "` + _lt("drawing-pin") + `",
        "` + _lt("pin") + `",
        "` + _lt("pushpin") + `"
    ],
    "name": "` + _lt("pushpin") + `",
    "shortcodes": [
        ":pushpin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📍",
    "emoticons": [],
    "keywords": [
        "` + _lt("pin") + `",
        "` + _lt("pushpin") + `",
        "` + _lt("round drawing-pin") + `",
        "` + _lt("round pushpin") + `"
    ],
    "name": "` + _lt("round pushpin") + `",
    "shortcodes": [
        ":round_pushpin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📎",
    "emoticons": [],
    "keywords": [
        "` + _lt("paperclip") + `"
    ],
    "name": "` + _lt("paperclip") + `",
    "shortcodes": [
        ":paperclip:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖇️",
    "emoticons": [],
    "keywords": [
        "` + _lt("link") + `",
        "` + _lt("linked paperclips") + `",
        "` + _lt("paperclip") + `"
    ],
    "name": "` + _lt("linked paperclips") + `",
    "shortcodes": [
        ":linked_paperclips:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📏",
    "emoticons": [],
    "keywords": [
        "` + _lt("ruler") + `",
        "` + _lt("straight edge") + `",
        "` + _lt("straight ruler") + `"
    ],
    "name": "` + _lt("straight ruler") + `",
    "shortcodes": [
        ":straight_ruler:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📐",
    "emoticons": [],
    "keywords": [
        "` + _lt("ruler") + `",
        "` + _lt("set") + `",
        "` + _lt("triangle") + `",
        "` + _lt("triangular ruler") + `",
        "` + _lt("set square") + `"
    ],
    "name": "` + _lt("triangular ruler") + `",
    "shortcodes": [
        ":triangular_ruler:"
    ]
},
{
    "category": "Objects",
    "codepoints": "✂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cutting") + `",
        "` + _lt("scissors") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("scissors") + `",
    "shortcodes": [
        ":scissors:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗃️",
    "emoticons": [],
    "keywords": [
        "` + _lt("box") + `",
        "` + _lt("card") + `",
        "` + _lt("file") + `"
    ],
    "name": "` + _lt("card file box") + `",
    "shortcodes": [
        ":card_file_box:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗄️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cabinet") + `",
        "` + _lt("file") + `",
        "` + _lt("filing") + `"
    ],
    "name": "` + _lt("file cabinet") + `",
    "shortcodes": [
        ":file_cabinet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗑️",
    "emoticons": [],
    "keywords": [
        "` + _lt("wastebasket") + `"
    ],
    "name": "` + _lt("wastebasket") + `",
    "shortcodes": [
        ":wastebasket:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔒",
    "emoticons": [],
    "keywords": [
        "` + _lt("closed") + `",
        "` + _lt("locked") + `",
        "` + _lt("padlock") + `"
    ],
    "name": "` + _lt("locked") + `",
    "shortcodes": [
        ":locked:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔓",
    "emoticons": [],
    "keywords": [
        "` + _lt("lock") + `",
        "` + _lt("open") + `",
        "` + _lt("unlock") + `",
        "` + _lt("unlocked") + `",
        "` + _lt("padlock") + `"
    ],
    "name": "` + _lt("unlocked") + `",
    "shortcodes": [
        ":unlocked:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔏",
    "emoticons": [],
    "keywords": [
        "` + _lt("ink") + `",
        "` + _lt("lock") + `",
        "` + _lt("locked with pen") + `",
        "` + _lt("nib") + `",
        "` + _lt("pen") + `",
        "` + _lt("privacy") + `"
    ],
    "name": "` + _lt("locked with pen") + `",
    "shortcodes": [
        ":locked_with_pen:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔐",
    "emoticons": [],
    "keywords": [
        "` + _lt("closed") + `",
        "` + _lt("key") + `",
        "` + _lt("lock") + `",
        "` + _lt("locked with key") + `",
        "` + _lt("secure") + `"
    ],
    "name": "` + _lt("locked with key") + `",
    "shortcodes": [
        ":locked_with_key:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔑",
    "emoticons": [
        ":key"
    ],
    "keywords": [
        "` + _lt("key") + `",
        "` + _lt("lock") + `",
        "` + _lt("password") + `"
    ],
    "name": "` + _lt("key") + `",
    "shortcodes": [
        ":key:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗝️",
    "emoticons": [],
    "keywords": [
        "` + _lt("clue") + `",
        "` + _lt("key") + `",
        "` + _lt("lock") + `",
        "` + _lt("old") + `"
    ],
    "name": "` + _lt("old key") + `",
    "shortcodes": [
        ":old_key:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔨",
    "emoticons": [],
    "keywords": [
        "` + _lt("hammer") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("hammer") + `",
    "shortcodes": [
        ":hammer:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪓",
    "emoticons": [],
    "keywords": [
        "` + _lt("axe") + `",
        "` + _lt("chop") + `",
        "` + _lt("hatchet") + `",
        "` + _lt("split") + `",
        "` + _lt("wood") + `"
    ],
    "name": "` + _lt("axe") + `",
    "shortcodes": [
        ":axe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⛏️",
    "emoticons": [],
    "keywords": [
        "` + _lt("mining") + `",
        "` + _lt("pick") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("pick") + `",
    "shortcodes": [
        ":pick:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚒️",
    "emoticons": [],
    "keywords": [
        "` + _lt("hammer") + `",
        "` + _lt("hammer and pick") + `",
        "` + _lt("pick") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("hammer and pick") + `",
    "shortcodes": [
        ":hammer_and_pick:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛠️",
    "emoticons": [],
    "keywords": [
        "` + _lt("hammer") + `",
        "` + _lt("hammer and spanner") + `",
        "` + _lt("hammer and wrench") + `",
        "` + _lt("spanner") + `",
        "` + _lt("tool") + `",
        "` + _lt("wrench") + `"
    ],
    "name": "` + _lt("hammer and wrench") + `",
    "shortcodes": [
        ":hammer_and_wrench:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗡️",
    "emoticons": [],
    "keywords": [
        "` + _lt("dagger") + `",
        "` + _lt("knife") + `",
        "` + _lt("weapon") + `"
    ],
    "name": "` + _lt("dagger") + `",
    "shortcodes": [
        ":dagger:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚔️",
    "emoticons": [],
    "keywords": [
        "` + _lt("crossed") + `",
        "` + _lt("swords") + `",
        "` + _lt("weapon") + `"
    ],
    "name": "` + _lt("crossed swords") + `",
    "shortcodes": [
        ":crossed_swords:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔫",
    "emoticons": [],
    "keywords": [
        "` + _lt("toy") + `",
        "` + _lt("water pistol") + `",
        "` + _lt("gun") + `",
        "` + _lt("handgun") + `",
        "` + _lt("pistol") + `",
        "` + _lt("revolver") + `",
        "` + _lt("tool") + `",
        "` + _lt("water") + `",
        "` + _lt("weapon") + `"
    ],
    "name": "` + _lt("water pistol") + `",
    "shortcodes": [
        ":water_pistol:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🏹",
    "emoticons": [],
    "keywords": [
        "` + _lt("archer") + `",
        "` + _lt("arrow") + `",
        "` + _lt("bow") + `",
        "` + _lt("bow and arrow") + `",
        "` + _lt("Sagittarius") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("bow and arrow") + `",
    "shortcodes": [
        ":bow_and_arrow:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛡️",
    "emoticons": [],
    "keywords": [
        "` + _lt("shield") + `",
        "` + _lt("weapon") + `"
    ],
    "name": "` + _lt("shield") + `",
    "shortcodes": [
        ":shield:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔧",
    "emoticons": [],
    "keywords": [
        "` + _lt("spanner") + `",
        "` + _lt("tool") + `",
        "` + _lt("wrench") + `"
    ],
    "name": "` + _lt("wrench") + `",
    "shortcodes": [
        ":wrench:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔩",
    "emoticons": [],
    "keywords": [
        "` + _lt("bolt") + `",
        "` + _lt("nut") + `",
        "` + _lt("nut and bolt") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("nut and bolt") + `",
    "shortcodes": [
        ":nut_and_bolt:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚙️",
    "emoticons": [],
    "keywords": [
        "` + _lt("cog") + `",
        "` + _lt("cogwheel") + `",
        "` + _lt("gear") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("gear") + `",
    "shortcodes": [
        ":gear:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗜️",
    "emoticons": [],
    "keywords": [
        "` + _lt("clamp") + `",
        "` + _lt("compress") + `",
        "` + _lt("tool") + `",
        "` + _lt("vice") + `"
    ],
    "name": "` + _lt("clamp") + `",
    "shortcodes": [
        ":clamp:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚖️",
    "emoticons": [],
    "keywords": [
        "` + _lt("balance") + `",
        "` + _lt("justice") + `",
        "` + _lt("Libra") + `",
        "` + _lt("scale") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("balance scale") + `",
    "shortcodes": [
        ":balance_scale:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🦯",
    "emoticons": [],
    "keywords": [
        "` + _lt("accessibility") + `",
        "` + _lt("long mobility cane") + `",
        "` + _lt("white cane") + `",
        "` + _lt("blind") + `",
        "` + _lt("guide cane") + `"
    ],
    "name": "` + _lt("white cane") + `",
    "shortcodes": [
        ":white_cane:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔗",
    "emoticons": [],
    "keywords": [
        "` + _lt("link") + `"
    ],
    "name": "` + _lt("link") + `",
    "shortcodes": [
        ":link:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⛓️",
    "emoticons": [],
    "keywords": [
        "` + _lt("chain") + `",
        "` + _lt("chains") + `"
    ],
    "name": "` + _lt("chains") + `",
    "shortcodes": [
        ":chains:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧰",
    "emoticons": [],
    "keywords": [
        "` + _lt("chest") + `",
        "` + _lt("mechanic") + `",
        "` + _lt("tool") + `",
        "` + _lt("toolbox") + `"
    ],
    "name": "` + _lt("toolbox") + `",
    "shortcodes": [
        ":toolbox:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧲",
    "emoticons": [],
    "keywords": [
        "` + _lt("attraction") + `",
        "` + _lt("horseshoe") + `",
        "` + _lt("magnet") + `",
        "` + _lt("magnetic") + `"
    ],
    "name": "` + _lt("magnet") + `",
    "shortcodes": [
        ":magnet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚗️",
    "emoticons": [],
    "keywords": [
        "` + _lt("alembic") + `",
        "` + _lt("chemistry") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("alembic") + `",
    "shortcodes": [
        ":alembic:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧪",
    "emoticons": [],
    "keywords": [
        "` + _lt("chemist") + `",
        "` + _lt("chemistry") + `",
        "` + _lt("experiment") + `",
        "` + _lt("lab") + `",
        "` + _lt("science") + `",
        "` + _lt("test tube") + `"
    ],
    "name": "` + _lt("test tube") + `",
    "shortcodes": [
        ":test_ltube:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧫",
    "emoticons": [],
    "keywords": [
        "` + _lt("bacteria") + `",
        "` + _lt("biologist") + `",
        "` + _lt("biology") + `",
        "` + _lt("culture") + `",
        "` + _lt("lab") + `",
        "` + _lt("petri dish") + `"
    ],
    "name": "` + _lt("petri dish") + `",
    "shortcodes": [
        ":petri_dish:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧬",
    "emoticons": [],
    "keywords": [
        "` + _lt("biologist") + `",
        "` + _lt("dna") + `",
        "` + _lt("DNA") + `",
        "` + _lt("evolution") + `",
        "` + _lt("gene") + `",
        "` + _lt("genetics") + `",
        "` + _lt("life") + `"
    ],
    "name": "` + _lt("dna") + `",
    "shortcodes": [
        ":dna:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔬",
    "emoticons": [],
    "keywords": [
        "` + _lt("microscope") + `",
        "` + _lt("science") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("microscope") + `",
    "shortcodes": [
        ":microscope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔭",
    "emoticons": [],
    "keywords": [
        "` + _lt("science") + `",
        "` + _lt("telescope") + `",
        "` + _lt("tool") + `"
    ],
    "name": "` + _lt("telescope") + `",
    "shortcodes": [
        ":telescope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📡",
    "emoticons": [],
    "keywords": [
        "` + _lt("antenna") + `",
        "` + _lt("dish") + `",
        "` + _lt("satellite") + `"
    ],
    "name": "` + _lt("satellite antenna") + `",
    "shortcodes": [
        ":satellite_antenna:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💉",
    "emoticons": [],
    "keywords": [
        "` + _lt("medicine") + `",
        "` + _lt("needle") + `",
        "` + _lt("shot") + `",
        "` + _lt("sick") + `",
        "` + _lt("syringe") + `",
        "` + _lt("ill") + `",
        "` + _lt("injection") + `"
    ],
    "name": "` + _lt("syringe") + `",
    "shortcodes": [
        ":syringe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩸",
    "emoticons": [],
    "keywords": [
        "` + _lt("bleed") + `",
        "` + _lt("blood donation") + `",
        "` + _lt("drop of blood") + `",
        "` + _lt("injury") + `",
        "` + _lt("medicine") + `",
        "` + _lt("menstruation") + `"
    ],
    "name": "` + _lt("drop of blood") + `",
    "shortcodes": [
        ":drop_of_blood:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💊",
    "emoticons": [],
    "keywords": [
        "` + _lt("doctor") + `",
        "` + _lt("medicine") + `",
        "` + _lt("pill") + `",
        "` + _lt("sick") + `"
    ],
    "name": "` + _lt("pill") + `",
    "shortcodes": [
        ":pill:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩹",
    "emoticons": [],
    "keywords": [
        "` + _lt("adhesive bandage") + `",
        "` + _lt("bandage") + `",
        "` + _lt("bandaid") + `",
        "` + _lt("dressing") + `",
        "` + _lt("injury") + `",
        "` + _lt("plaster") + `",
        "` + _lt("sticking plaster") + `"
    ],
    "name": "` + _lt("adhesive bandage") + `",
    "shortcodes": [
        ":adhesive_bandage:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩺",
    "emoticons": [],
    "keywords": [
        "` + _lt("doctor") + `",
        "` + _lt("heart") + `",
        "` + _lt("medicine") + `",
        "` + _lt("stethoscope") + `"
    ],
    "name": "` + _lt("stethoscope") + `",
    "shortcodes": [
        ":stethoscope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🚪",
    "emoticons": [],
    "keywords": [
        "` + _lt("door") + `"
    ],
    "name": "` + _lt("door") + `",
    "shortcodes": [
        ":door:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛏️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bed") + `",
        "` + _lt("hotel") + `",
        "` + _lt("sleep") + `"
    ],
    "name": "` + _lt("bed") + `",
    "shortcodes": [
        ":bed:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛋️",
    "emoticons": [],
    "keywords": [
        "` + _lt("couch") + `",
        "` + _lt("couch and lamp") + `",
        "` + _lt("hotel") + `",
        "` + _lt("lamp") + `",
        "` + _lt("sofa") + `",
        "` + _lt("sofa and lamp") + `"
    ],
    "name": "` + _lt("couch and lamp") + `",
    "shortcodes": [
        ":couch_and_lamp:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪑",
    "emoticons": [],
    "keywords": [
        "` + _lt("chair") + `",
        "` + _lt("seat") + `",
        "` + _lt("sit") + `"
    ],
    "name": "` + _lt("chair") + `",
    "shortcodes": [
        ":chair:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🚽",
    "emoticons": [],
    "keywords": [
        "` + _lt("facilities") + `",
        "` + _lt("loo") + `",
        "` + _lt("toilet") + `",
        "` + _lt("WC") + `",
        "` + _lt("lavatory") + `"
    ],
    "name": "` + _lt("toilet") + `",
    "shortcodes": [
        ":toilet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🚿",
    "emoticons": [],
    "keywords": [
        "` + _lt("shower") + `",
        "` + _lt("water") + `"
    ],
    "name": "` + _lt("shower") + `",
    "shortcodes": [
        ":shower:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛁",
    "emoticons": [],
    "keywords": [
        "` + _lt("bath") + `",
        "` + _lt("bathtub") + `"
    ],
    "name": "` + _lt("bathtub") + `",
    "shortcodes": [
        ":bathtub:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪒",
    "emoticons": [],
    "keywords": [
        "` + _lt("razor") + `",
        "` + _lt("sharp") + `",
        "` + _lt("shave") + `",
        "` + _lt("cut-throat") + `"
    ],
    "name": "` + _lt("razor") + `",
    "shortcodes": [
        ":razor:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧴",
    "emoticons": [],
    "keywords": [
        "` + _lt("lotion") + `",
        "` + _lt("lotion bottle") + `",
        "` + _lt("moisturizer") + `",
        "` + _lt("shampoo") + `",
        "` + _lt("sunscreen") + `",
        "` + _lt("moisturiser") + `"
    ],
    "name": "` + _lt("lotion bottle") + `",
    "shortcodes": [
        ":lotion_bottle:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧷",
    "emoticons": [],
    "keywords": [
        "` + _lt("nappy") + `",
        "` + _lt("punk rock") + `",
        "` + _lt("safety pin") + `",
        "` + _lt("diaper") + `"
    ],
    "name": "` + _lt("safety pin") + `",
    "shortcodes": [
        ":safety_pin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧹",
    "emoticons": [],
    "keywords": [
        "` + _lt("broom") + `",
        "` + _lt("cleaning") + `",
        "` + _lt("sweeping") + `",
        "` + _lt("witch") + `"
    ],
    "name": "` + _lt("broom") + `",
    "shortcodes": [
        ":broom:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧺",
    "emoticons": [],
    "keywords": [
        "` + _lt("basket") + `",
        "` + _lt("farming") + `",
        "` + _lt("laundry") + `",
        "` + _lt("picnic") + `"
    ],
    "name": "` + _lt("basket") + `",
    "shortcodes": [
        ":basket:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧻",
    "emoticons": [],
    "keywords": [
        "` + _lt("paper towels") + `",
        "` + _lt("roll of paper") + `",
        "` + _lt("toilet paper") + `",
        "` + _lt("toilet roll") + `"
    ],
    "name": "` + _lt("roll of paper") + `",
    "shortcodes": [
        ":roll_of_paper:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧼",
    "emoticons": [],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("bathing") + `",
        "` + _lt("cleaning") + `",
        "` + _lt("lather") + `",
        "` + _lt("soap") + `",
        "` + _lt("soapdish") + `"
    ],
    "name": "` + _lt("soap") + `",
    "shortcodes": [
        ":soap:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧽",
    "emoticons": [],
    "keywords": [
        "` + _lt("absorbing") + `",
        "` + _lt("cleaning") + `",
        "` + _lt("porous") + `",
        "` + _lt("sponge") + `"
    ],
    "name": "` + _lt("sponge") + `",
    "shortcodes": [
        ":sponge:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧯",
    "emoticons": [],
    "keywords": [
        "` + _lt("extinguish") + `",
        "` + _lt("fire") + `",
        "` + _lt("fire extinguisher") + `",
        "` + _lt("quench") + `"
    ],
    "name": "` + _lt("fire extinguisher") + `",
    "shortcodes": [
        ":fire_extinguisher:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛒",
    "emoticons": [],
    "keywords": [
        "` + _lt("cart") + `",
        "` + _lt("shopping") + `",
        "` + _lt("trolley") + `",
        "` + _lt("basket") + `"
    ],
    "name": "` + _lt("shopping cart") + `",
    "shortcodes": [
        ":shopping_cart:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🚬",
    "emoticons": [],
    "keywords": [
        "` + _lt("cigarette") + `",
        "` + _lt("smoking") + `"
    ],
    "name": "` + _lt("cigarette") + `",
    "shortcodes": [
        ":cigarette:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚰️",
    "emoticons": [],
    "keywords": [
        "` + _lt("coffin") + `",
        "` + _lt("death") + `"
    ],
    "name": "` + _lt("coffin") + `",
    "shortcodes": [
        ":coffin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚱️",
    "emoticons": [],
    "keywords": [
        "` + _lt("ashes") + `",
        "` + _lt("death") + `",
        "` + _lt("funeral") + `",
        "` + _lt("urn") + `"
    ],
    "name": "` + _lt("funeral urn") + `",
    "shortcodes": [
        ":funeral_urn:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗿",
    "emoticons": [],
    "keywords": [
        "` + _lt("face") + `",
        "` + _lt("moai") + `",
        "` + _lt("moyai") + `",
        "` + _lt("statue") + `"
    ],
    "name": "` + _lt("moai") + `",
    "shortcodes": [
        ":moai:"
    ]
},`;

const emojisData8 = `{
    "category": "Symbols",
    "codepoints": "🏧",
    "emoticons": [],
    "keywords": [
        "` + _lt("ATM") + `",
        "` + _lt("ATM sign") + `",
        "` + _lt("automated") + `",
        "` + _lt("bank") + `",
        "` + _lt("teller") + `"
    ],
    "name": "` + _lt("ATM sign") + `",
    "shortcodes": [
        ":ATM_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚮",
    "emoticons": [],
    "keywords": [
        "` + _lt("litter") + `",
        "` + _lt("litter bin") + `",
        "` + _lt("litter in bin sign") + `",
        "` + _lt("garbage") + `",
        "` + _lt("trash") + `"
    ],
    "name": "` + _lt("litter in bin sign") + `",
    "shortcodes": [
        ":litter_in_bin_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚰",
    "emoticons": [],
    "keywords": [
        "` + _lt("drinking") + `",
        "` + _lt("potable") + `",
        "` + _lt("water") + `"
    ],
    "name": "` + _lt("potable water") + `",
    "shortcodes": [
        ":potable_water:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♿",
    "emoticons": [],
    "keywords": [
        "` + _lt("access") + `",
        "` + _lt("disabled access") + `",
        "` + _lt("wheelchair symbol") + `"
    ],
    "name": "` + _lt("wheelchair symbol") + `",
    "shortcodes": [
        ":wheelchair_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚹",
    "emoticons": [],
    "keywords": [
        "` + _lt("bathroom") + `",
        "` + _lt("lavatory") + `",
        "` + _lt("man") + `",
        "` + _lt("men’s room") + `",
        "` + _lt("restroom") + `",
        "` + _lt("toilet") + `",
        "` + _lt("WC") + `",
        "` + _lt("men’s") + `",
        "` + _lt("washroom") + `",
        "` + _lt("wc") + `"
    ],
    "name": "` + _lt("men’s room") + `",
    "shortcodes": [
        ":men’s_room:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚺",
    "emoticons": [],
    "keywords": [
        "` + _lt("ladies room") + `",
        "` + _lt("lavatory") + `",
        "` + _lt("restroom") + `",
        "` + _lt("wc") + `",
        "` + _lt("woman") + `",
        "` + _lt("women’s room") + `",
        "` + _lt("women’s toilet") + `",
        "` + _lt("bathroom") + `",
        "` + _lt("toilet") + `",
        "` + _lt("WC") + `",
        "` + _lt("ladies’ room") + `",
        "` + _lt("washroom") + `",
        "` + _lt("women’s") + `"
    ],
    "name": "` + _lt("women’s room") + `",
    "shortcodes": [
        ":women’s_room:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚻",
    "emoticons": [],
    "keywords": [
        "` + _lt("bathroom") + `",
        "` + _lt("lavatory") + `",
        "` + _lt("restroom") + `",
        "` + _lt("toilet") + `",
        "` + _lt("WC") + `",
        "` + _lt("washroom") + `"
    ],
    "name": "` + _lt("restroom") + `",
    "shortcodes": [
        ":restroom:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚼",
    "emoticons": [],
    "keywords": [
        "` + _lt("baby") + `",
        "` + _lt("baby symbol") + `",
        "` + _lt("change room") + `",
        "` + _lt("changing") + `"
    ],
    "name": "` + _lt("baby symbol") + `",
    "shortcodes": [
        ":baby_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚾",
    "emoticons": [],
    "keywords": [
        "` + _lt("amenities") + `",
        "` + _lt("bathroom") + `",
        "` + _lt("restroom") + `",
        "` + _lt("toilet") + `",
        "` + _lt("water closet") + `",
        "` + _lt("wc") + `",
        "` + _lt("WC") + `",
        "` + _lt("closet") + `",
        "` + _lt("lavatory") + `",
        "` + _lt("water") + `"
    ],
    "name": "` + _lt("water closet") + `",
    "shortcodes": [
        ":water_closet:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛂",
    "emoticons": [],
    "keywords": [
        "` + _lt("border") + `",
        "` + _lt("control") + `",
        "` + _lt("passport") + `",
        "` + _lt("security") + `"
    ],
    "name": "` + _lt("passport control") + `",
    "shortcodes": [
        ":passport_control:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛃",
    "emoticons": [],
    "keywords": [
        "` + _lt("customs") + `"
    ],
    "name": "` + _lt("customs") + `",
    "shortcodes": [
        ":customs:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛄",
    "emoticons": [],
    "keywords": [
        "` + _lt("baggage") + `",
        "` + _lt("claim") + `"
    ],
    "name": "` + _lt("baggage claim") + `",
    "shortcodes": [
        ":baggage_claim:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛅",
    "emoticons": [],
    "keywords": [
        "` + _lt("baggage") + `",
        "` + _lt("left luggage") + `",
        "` + _lt("locker") + `",
        "` + _lt("luggage") + `"
    ],
    "name": "` + _lt("left luggage") + `",
    "shortcodes": [
        ":left_luggage:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚠️",
    "emoticons": [],
    "keywords": [
        "` + _lt("warning") + `"
    ],
    "name": "` + _lt("warning") + `",
    "shortcodes": [
        ":warning:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚸",
    "emoticons": [],
    "keywords": [
        "` + _lt("child") + `",
        "` + _lt("children crossing") + `",
        "` + _lt("crossing") + `",
        "` + _lt("pedestrian") + `",
        "` + _lt("traffic") + `"
    ],
    "name": "` + _lt("children crossing") + `",
    "shortcodes": [
        ":children_crossing:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⛔",
    "emoticons": [],
    "keywords": [
        "` + _lt("denied") + `",
        "` + _lt("entry") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("no") + `",
        "` + _lt("prohibited") + `",
        "` + _lt("traffic") + `",
        "` + _lt("not") + `"
    ],
    "name": "` + _lt("no entry") + `",
    "shortcodes": [
        ":no_entry:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚫",
    "emoticons": [],
    "keywords": [
        "` + _lt("denied") + `",
        "` + _lt("entry") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("no") + `",
        "` + _lt("prohibited") + `",
        "` + _lt("not") + `"
    ],
    "name": "` + _lt("prohibited") + `",
    "shortcodes": [
        ":prohibited:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚳",
    "emoticons": [],
    "keywords": [
        "` + _lt("bicycle") + `",
        "` + _lt("bike") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("no") + `",
        "` + _lt("no bicycles") + `",
        "` + _lt("prohibited") + `"
    ],
    "name": "` + _lt("no bicycles") + `",
    "shortcodes": [
        ":no_bicycles:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚭",
    "emoticons": [],
    "keywords": [
        "` + _lt("denied") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("no") + `",
        "` + _lt("prohibited") + `",
        "` + _lt("smoking") + `",
        "` + _lt("not") + `"
    ],
    "name": "` + _lt("no smoking") + `",
    "shortcodes": [
        ":no_smoking:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚯",
    "emoticons": [],
    "keywords": [
        "` + _lt("denied") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("litter") + `",
        "` + _lt("no") + `",
        "` + _lt("no littering") + `",
        "` + _lt("prohibited") + `",
        "` + _lt("not") + `"
    ],
    "name": "` + _lt("no littering") + `",
    "shortcodes": [
        ":no_littering:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚱",
    "emoticons": [],
    "keywords": [
        "` + _lt("non-drinkable water") + `",
        "` + _lt("non-drinking") + `",
        "` + _lt("non-potable") + `",
        "` + _lt("water") + `"
    ],
    "name": "` + _lt("non-potable water") + `",
    "shortcodes": [
        ":non-potable_water:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚷",
    "emoticons": [],
    "keywords": [
        "` + _lt("denied") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("no") + `",
        "` + _lt("no pedestrians") + `",
        "` + _lt("pedestrian") + `",
        "` + _lt("prohibited") + `",
        "` + _lt("not") + `"
    ],
    "name": "` + _lt("no pedestrians") + `",
    "shortcodes": [
        ":no_pedestrians:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📵",
    "emoticons": [],
    "keywords": [
        "` + _lt("cell") + `",
        "` + _lt("forbidden") + `",
        "` + _lt("mobile") + `",
        "` + _lt("no") + `",
        "` + _lt("no mobile phones") + `",
        "` + _lt("phone") + `"
    ],
    "name": "` + _lt("no mobile phones") + `",
    "shortcodes": [
        ":no_mobile_phones:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔞",
    "emoticons": [],
    "keywords": [
        "` + _lt("18") + `",
        "` + _lt("age restriction") + `",
        "` + _lt("eighteen") + `",
        "` + _lt("no one under eighteen") + `",
        "` + _lt("prohibited") + `",
        "` + _lt("underage") + `"
    ],
    "name": "` + _lt("no one under eighteen") + `",
    "shortcodes": [
        ":no_one_under_eighteen:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☢️",
    "emoticons": [],
    "keywords": [
        "` + _lt("radioactive") + `",
        "` + _lt("sign") + `"
    ],
    "name": "` + _lt("radioactive") + `",
    "shortcodes": [
        ":radioactive:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☣️",
    "emoticons": [],
    "keywords": [
        "` + _lt("biohazard") + `",
        "` + _lt("sign") + `"
    ],
    "name": "` + _lt("biohazard") + `",
    "shortcodes": [
        ":biohazard:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬆️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("cardinal") + `",
        "` + _lt("direction") + `",
        "` + _lt("north") + `",
        "` + _lt("up") + `",
        "` + _lt("up arrow") + `"
    ],
    "name": "` + _lt("up arrow") + `",
    "shortcodes": [
        ":up_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↗️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("direction") + `",
        "` + _lt("intercardinal") + `",
        "` + _lt("northeast") + `",
        "` + _lt("up-right arrow") + `"
    ],
    "name": "` + _lt("up-right arrow") + `",
    "shortcodes": [
        ":up-right_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➡️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("cardinal") + `",
        "` + _lt("direction") + `",
        "` + _lt("east") + `",
        "` + _lt("right arrow") + `"
    ],
    "name": "` + _lt("right arrow") + `",
    "shortcodes": [
        ":right_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↘️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("direction") + `",
        "` + _lt("down-right arrow") + `",
        "` + _lt("intercardinal") + `",
        "` + _lt("southeast") + `"
    ],
    "name": "` + _lt("down-right arrow") + `",
    "shortcodes": [
        ":down-right_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬇️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("cardinal") + `",
        "` + _lt("direction") + `",
        "` + _lt("down") + `",
        "` + _lt("south") + `"
    ],
    "name": "` + _lt("down arrow") + `",
    "shortcodes": [
        ":down_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↙️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("direction") + `",
        "` + _lt("down-left arrow") + `",
        "` + _lt("intercardinal") + `",
        "` + _lt("southwest") + `"
    ],
    "name": "` + _lt("down-left arrow") + `",
    "shortcodes": [
        ":down-left_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬅️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("cardinal") + `",
        "` + _lt("direction") + `",
        "` + _lt("left arrow") + `",
        "` + _lt("west") + `"
    ],
    "name": "` + _lt("left arrow") + `",
    "shortcodes": [
        ":left_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↖️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("direction") + `",
        "` + _lt("intercardinal") + `",
        "` + _lt("northwest") + `",
        "` + _lt("up-left arrow") + `"
    ],
    "name": "` + _lt("up-left arrow") + `",
    "shortcodes": [
        ":up-left_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↕️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("up-down arrow") + `"
    ],
    "name": "` + _lt("up-down arrow") + `",
    "shortcodes": [
        ":up-down_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↔️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("left-right arrow") + `"
    ],
    "name": "` + _lt("left-right arrow") + `",
    "shortcodes": [
        ":left-right_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↩️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("right arrow curving left") + `"
    ],
    "name": "` + _lt("right arrow curving left") + `",
    "shortcodes": [
        ":right_arrow_curving_left:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↪️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("left arrow curving right") + `"
    ],
    "name": "` + _lt("left arrow curving right") + `",
    "shortcodes": [
        ":left_arrow_curving_right:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⤴️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("right arrow curving up") + `"
    ],
    "name": "` + _lt("right arrow curving up") + `",
    "shortcodes": [
        ":right_arrow_curving_up:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⤵️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("down") + `",
        "` + _lt("right arrow curving down") + `"
    ],
    "name": "` + _lt("right arrow curving down") + `",
    "shortcodes": [
        ":right_arrow_curving_down:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔃",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("clockwise") + `",
        "` + _lt("clockwise vertical arrows") + `",
        "` + _lt("reload") + `"
    ],
    "name": "` + _lt("clockwise vertical arrows") + `",
    "shortcodes": [
        ":clockwise_vertical_arrows:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔄",
    "emoticons": [],
    "keywords": [
        "` + _lt("anticlockwise") + `",
        "` + _lt("arrow") + `",
        "` + _lt("counterclockwise") + `",
        "` + _lt("counterclockwise arrows button") + `",
        "` + _lt("withershins") + `",
        "` + _lt("anticlockwise arrows button") + `"
    ],
    "name": "` + _lt("counterclockwise arrows button") + `",
    "shortcodes": [
        ":counterclockwise_arrows_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔙",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("BACK") + `"
    ],
    "name": "` + _lt("BACK arrow") + `",
    "shortcodes": [
        ":BACK_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔚",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("END") + `"
    ],
    "name": "` + _lt("END arrow") + `",
    "shortcodes": [
        ":END_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔛",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("mark") + `",
        "` + _lt("ON") + `",
        "` + _lt("ON!") + `"
    ],
    "name": "` + _lt("ON! arrow") + `",
    "shortcodes": [
        ":ON!_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔜",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("SOON") + `"
    ],
    "name": "` + _lt("SOON arrow") + `",
    "shortcodes": [
        ":SOON_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔝",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("TOP") + `",
        "` + _lt("up") + `"
    ],
    "name": "` + _lt("TOP arrow") + `",
    "shortcodes": [
        ":TOP_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛐",
    "emoticons": [],
    "keywords": [
        "` + _lt("place of worship") + `",
        "` + _lt("religion") + `",
        "` + _lt("worship") + `"
    ],
    "name": "` + _lt("place of worship") + `",
    "shortcodes": [
        ":place_of_worship:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚛️",
    "emoticons": [],
    "keywords": [
        "` + _lt("atheist") + `",
        "` + _lt("atom") + `",
        "` + _lt("atom symbol") + `"
    ],
    "name": "` + _lt("atom symbol") + `",
    "shortcodes": [
        ":atom_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🕉️",
    "emoticons": [],
    "keywords": [
        "` + _lt("Hindu") + `",
        "` + _lt("om") + `",
        "` + _lt("religion") + `"
    ],
    "name": "` + _lt("om") + `",
    "shortcodes": [
        ":om:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✡️",
    "emoticons": [],
    "keywords": [
        "` + _lt("David") + `",
        "` + _lt("Jew") + `",
        "` + _lt("Jewish") + `",
        "` + _lt("religion") + `",
        "` + _lt("star") + `",
        "` + _lt("star of David") + `",
        "` + _lt("Judaism") + `",
        "` + _lt("Star of David") + `"
    ],
    "name": "` + _lt("star of David") + `",
    "shortcodes": [
        ":star_of_David:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☸️",
    "emoticons": [],
    "keywords": [
        "` + _lt("Buddhist") + `",
        "` + _lt("dharma") + `",
        "` + _lt("religion") + `",
        "` + _lt("wheel") + `",
        "` + _lt("wheel of dharma") + `"
    ],
    "name": "` + _lt("wheel of dharma") + `",
    "shortcodes": [
        ":wheel_of_dharma:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☯️",
    "emoticons": [],
    "keywords": [
        "` + _lt("religion") + `",
        "` + _lt("tao") + `",
        "` + _lt("taoist") + `",
        "` + _lt("yang") + `",
        "` + _lt("yin") + `",
        "` + _lt("Tao") + `",
        "` + _lt("Taoist") + `"
    ],
    "name": "` + _lt("yin yang") + `",
    "shortcodes": [
        ":yin_yang:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✝️",
    "emoticons": [],
    "keywords": [
        "` + _lt("Christian") + `",
        "` + _lt("cross") + `",
        "` + _lt("religion") + `",
        "` + _lt("latin cross") + `",
        "` + _lt("Latin cross") + `"
    ],
    "name": "` + _lt("latin cross") + `",
    "shortcodes": [
        ":latin_cross:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☦️",
    "emoticons": [],
    "keywords": [
        "` + _lt("Christian") + `",
        "` + _lt("cross") + `",
        "` + _lt("orthodox cross") + `",
        "` + _lt("religion") + `",
        "` + _lt("Orthodox cross") + `"
    ],
    "name": "` + _lt("orthodox cross") + `",
    "shortcodes": [
        ":orthodox_cross:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☪️",
    "emoticons": [],
    "keywords": [
        "` + _lt("islam") + `",
        "` + _lt("Muslim") + `",
        "` + _lt("religion") + `",
        "` + _lt("star and crescent") + `",
        "` + _lt("Islam") + `"
    ],
    "name": "` + _lt("star and crescent") + `",
    "shortcodes": [
        ":star_and_crescent:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☮️",
    "emoticons": [],
    "keywords": [
        "` + _lt("peace") + `",
        "` + _lt("peace symbol") + `"
    ],
    "name": "` + _lt("peace symbol") + `",
    "shortcodes": [
        ":peace_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🕎",
    "emoticons": [],
    "keywords": [
        "` + _lt("candelabrum") + `",
        "` + _lt("candlestick") + `",
        "` + _lt("menorah") + `",
        "` + _lt("religion") + `"
    ],
    "name": "` + _lt("menorah") + `",
    "shortcodes": [
        ":menorah:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔯",
    "emoticons": [],
    "keywords": [
        "` + _lt("dotted six-pointed star") + `",
        "` + _lt("fortune") + `",
        "` + _lt("star") + `"
    ],
    "name": "` + _lt("dotted six-pointed star") + `",
    "shortcodes": [
        ":dotted_six-pointed_star:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♈",
    "emoticons": [],
    "keywords": [
        "` + _lt("Aries") + `",
        "` + _lt("ram") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Aries") + `",
    "shortcodes": [
        ":Aries:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♉",
    "emoticons": [],
    "keywords": [
        "` + _lt("bull") + `",
        "` + _lt("ox") + `",
        "` + _lt("Taurus") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Taurus") + `",
    "shortcodes": [
        ":Taurus:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♊",
    "emoticons": [],
    "keywords": [
        "` + _lt("Gemini") + `",
        "` + _lt("twins") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Gemini") + `",
    "shortcodes": [
        ":Gemini:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♋",
    "emoticons": [],
    "keywords": [
        "` + _lt("Cancer") + `",
        "` + _lt("crab") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Cancer") + `",
    "shortcodes": [
        ":Cancer:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♌",
    "emoticons": [],
    "keywords": [
        "` + _lt("Leo") + `",
        "` + _lt("lion") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Leo") + `",
    "shortcodes": [
        ":Leo:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♍",
    "emoticons": [],
    "keywords": [
        "` + _lt("virgin") + `",
        "` + _lt("Virgo") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Virgo") + `",
    "shortcodes": [
        ":Virgo:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♎",
    "emoticons": [],
    "keywords": [
        "` + _lt("balance") + `",
        "` + _lt("justice") + `",
        "` + _lt("Libra") + `",
        "` + _lt("scales") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Libra") + `",
    "shortcodes": [
        ":Libra:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♏",
    "emoticons": [],
    "keywords": [
        "` + _lt("Scorpio") + `",
        "` + _lt("scorpion") + `",
        "` + _lt("scorpius") + `",
        "` + _lt("zodiac") + `",
        "` + _lt("Scorpius") + `"
    ],
    "name": "` + _lt("Scorpio") + `",
    "shortcodes": [
        ":Scorpio:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♐",
    "emoticons": [],
    "keywords": [
        "` + _lt("archer") + `",
        "` + _lt("centaur") + `",
        "` + _lt("Sagittarius") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Sagittarius") + `",
    "shortcodes": [
        ":Sagittarius:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♑",
    "emoticons": [],
    "keywords": [
        "` + _lt("Capricorn") + `",
        "` + _lt("goat") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Capricorn") + `",
    "shortcodes": [
        ":Capricorn:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♒",
    "emoticons": [],
    "keywords": [
        "` + _lt("Aquarius") + `",
        "` + _lt("water bearer") + `",
        "` + _lt("zodiac") + `",
        "` + _lt("bearer") + `",
        "` + _lt("water") + `"
    ],
    "name": "` + _lt("Aquarius") + `",
    "shortcodes": [
        ":Aquarius:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♓",
    "emoticons": [],
    "keywords": [
        "` + _lt("fish") + `",
        "` + _lt("Pisces") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Pisces") + `",
    "shortcodes": [
        ":Pisces:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⛎",
    "emoticons": [],
    "keywords": [
        "` + _lt("bearer") + `",
        "` + _lt("Ophiuchus") + `",
        "` + _lt("serpent") + `",
        "` + _lt("snake") + `",
        "` + _lt("zodiac") + `"
    ],
    "name": "` + _lt("Ophiuchus") + `",
    "shortcodes": [
        ":Ophiuchus:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔀",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("crossed") + `",
        "` + _lt("shuffle tracks button") + `"
    ],
    "name": "` + _lt("shuffle tracks button") + `",
    "shortcodes": [
        ":shuffle_ltracks_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔁",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("clockwise") + `",
        "` + _lt("repeat") + `",
        "` + _lt("repeat button") + `"
    ],
    "name": "` + _lt("repeat button") + `",
    "shortcodes": [
        ":repeat_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔂",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("clockwise") + `",
        "` + _lt("once") + `",
        "` + _lt("repeat single button") + `"
    ],
    "name": "` + _lt("repeat single button") + `",
    "shortcodes": [
        ":repeat_single_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "▶️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("play") + `",
        "` + _lt("play button") + `",
        "` + _lt("right") + `",
        "` + _lt("triangle") + `"
    ],
    "name": "` + _lt("play button") + `",
    "shortcodes": [
        ":play_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏩",
    "emoticons": [],
    "keywords": [
        "` + _lt("fast forward button") + `",
        "` + _lt("arrow") + `",
        "` + _lt("double") + `",
        "` + _lt("fast") + `",
        "` + _lt("fast-forward button") + `",
        "` + _lt("forward") + `"
    ],
    "name": "` + _lt("fast-forward button") + `",
    "shortcodes": [
        ":fast-forward_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏭️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("next scene") + `",
        "` + _lt("next track") + `",
        "` + _lt("next track button") + `",
        "` + _lt("triangle") + `"
    ],
    "name": "` + _lt("next track button") + `",
    "shortcodes": [
        ":next_ltrack_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏯️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("pause") + `",
        "` + _lt("play") + `",
        "` + _lt("play or pause button") + `",
        "` + _lt("right") + `",
        "` + _lt("triangle") + `"
    ],
    "name": "` + _lt("play or pause button") + `",
    "shortcodes": [
        ":play_or_pause_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("left") + `",
        "` + _lt("reverse") + `",
        "` + _lt("reverse button") + `",
        "` + _lt("triangle") + `"
    ],
    "name": "` + _lt("reverse button") + `",
    "shortcodes": [
        ":reverse_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏪",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("double") + `",
        "` + _lt("fast reverse button") + `",
        "` + _lt("rewind") + `"
    ],
    "name": "` + _lt("fast reverse button") + `",
    "shortcodes": [
        ":fast_reverse_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏮️",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("last track button") + `",
        "` + _lt("previous scene") + `",
        "` + _lt("previous track") + `",
        "` + _lt("triangle") + `"
    ],
    "name": "` + _lt("last track button") + `",
    "shortcodes": [
        ":last_ltrack_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔼",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("button") + `",
        "` + _lt("red") + `",
        "` + _lt("upwards button") + `",
        "` + _lt("upward button") + `"
    ],
    "name": "` + _lt("upwards button") + `",
    "shortcodes": [
        ":upwards_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏫",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("double") + `",
        "` + _lt("fast up button") + `"
    ],
    "name": "` + _lt("fast up button") + `",
    "shortcodes": [
        ":fast_up_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔽",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("button") + `",
        "` + _lt("down") + `",
        "` + _lt("downwards button") + `",
        "` + _lt("red") + `",
        "` + _lt("downward button") + `"
    ],
    "name": "` + _lt("downwards button") + `",
    "shortcodes": [
        ":downwards_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏬",
    "emoticons": [],
    "keywords": [
        "` + _lt("arrow") + `",
        "` + _lt("double") + `",
        "` + _lt("down") + `",
        "` + _lt("fast down button") + `"
    ],
    "name": "` + _lt("fast down button") + `",
    "shortcodes": [
        ":fast_down_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏸️",
    "emoticons": [],
    "keywords": [
        "` + _lt("bar") + `",
        "` + _lt("double") + `",
        "` + _lt("pause") + `",
        "` + _lt("pause button") + `",
        "` + _lt("vertical") + `"
    ],
    "name": "` + _lt("pause button") + `",
    "shortcodes": [
        ":pause_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏹️",
    "emoticons": [],
    "keywords": [
        "` + _lt("square") + `",
        "` + _lt("stop") + `",
        "` + _lt("stop button") + `"
    ],
    "name": "` + _lt("stop button") + `",
    "shortcodes": [
        ":stop_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏺️",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("record") + `",
        "` + _lt("record button") + `"
    ],
    "name": "` + _lt("record button") + `",
    "shortcodes": [
        ":record_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏏️",
    "emoticons": [],
    "keywords": [
        "` + _lt("eject") + `",
        "` + _lt("eject button") + `"
    ],
    "name": "` + _lt("eject button") + `",
    "shortcodes": [
        ":eject_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🎦",
    "emoticons": [],
    "keywords": [
        "` + _lt("camera") + `",
        "` + _lt("cinema") + `",
        "` + _lt("film") + `",
        "` + _lt("movie") + `"
    ],
    "name": "` + _lt("cinema") + `",
    "shortcodes": [
        ":cinema:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔅",
    "emoticons": [],
    "keywords": [
        "` + _lt("brightness") + `",
        "` + _lt("dim") + `",
        "` + _lt("dim button") + `",
        "` + _lt("low") + `"
    ],
    "name": "` + _lt("dim button") + `",
    "shortcodes": [
        ":dim_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔆",
    "emoticons": [],
    "keywords": [
        "` + _lt("bright button") + `",
        "` + _lt("brightness") + `",
        "` + _lt("brightness button") + `",
        "` + _lt("bright") + `"
    ],
    "name": "` + _lt("bright button") + `",
    "shortcodes": [
        ":bright_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📶",
    "emoticons": [],
    "keywords": [
        "` + _lt("antenna") + `",
        "` + _lt("antenna bars") + `",
        "` + _lt("bar") + `",
        "` + _lt("cell") + `",
        "` + _lt("mobile") + `",
        "` + _lt("phone") + `"
    ],
    "name": "` + _lt("antenna bars") + `",
    "shortcodes": [
        ":antenna_bars:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📳",
    "emoticons": [],
    "keywords": [
        "` + _lt("cell") + `",
        "` + _lt("mobile") + `",
        "` + _lt("mode") + `",
        "` + _lt("phone") + `",
        "` + _lt("telephone") + `",
        "` + _lt("vibration") + `",
        "` + _lt("vibrate") + `"
    ],
    "name": "` + _lt("vibration mode") + `",
    "shortcodes": [
        ":vibration_mode:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📴",
    "emoticons": [],
    "keywords": [
        "` + _lt("cell") + `",
        "` + _lt("mobile") + `",
        "` + _lt("off") + `",
        "` + _lt("phone") + `",
        "` + _lt("telephone") + `"
    ],
    "name": "` + _lt("mobile phone off") + `",
    "shortcodes": [
        ":mobile_phone_off:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♀️",
    "emoticons": [],
    "keywords": [
        "` + _lt("female sign") + `",
        "` + _lt("woman") + `"
    ],
    "name": "` + _lt("female sign") + `",
    "shortcodes": [
        ":female_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("male sign") + `",
        "` + _lt("man") + `"
    ],
    "name": "` + _lt("male sign") + `",
    "shortcodes": [
        ":male_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✖️",
    "emoticons": [],
    "keywords": [
        "` + _lt("×") + `",
        "` + _lt("cancel") + `",
        "` + _lt("multiplication") + `",
        "` + _lt("multiply") + `",
        "` + _lt("sign") + `",
        "` + _lt("x") + `",
        "` + _lt("heavy multiplication sign") + `"
    ],
    "name": "` + _lt("multiply") + `",
    "shortcodes": [
        ":multiply:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➕",
    "emoticons": [],
    "keywords": [
        "` + _lt("+") + `",
        "` + _lt("add") + `",
        "` + _lt("addition") + `",
        "` + _lt("math") + `",
        "` + _lt("maths") + `",
        "` + _lt("plus") + `",
        "` + _lt("sign") + `"
    ],
    "name": "` + _lt("plus") + `",
    "shortcodes": [
        ":plus:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➖",
    "emoticons": [],
    "keywords": [
        "` + _lt("-") + `",
        "` + _lt("–") + `",
        "` + _lt("math") + `",
        "` + _lt("maths") + `",
        "` + _lt("minus") + `",
        "` + _lt("sign") + `",
        "` + _lt("subtraction") + `",
        "` + _lt("−") + `",
        "` + _lt("heavy minus sign") + `"
    ],
    "name": "` + _lt("minus") + `",
    "shortcodes": [
        ":minus:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➗",
    "emoticons": [],
    "keywords": [
        "` + _lt("÷") + `",
        "` + _lt("divide") + `",
        "` + _lt("division") + `",
        "` + _lt("math") + `",
        "` + _lt("sign") + `"
    ],
    "name": "` + _lt("divide") + `",
    "shortcodes": [
        ":divide:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♾️",
    "emoticons": [],
    "keywords": [
        "` + _lt("eternal") + `",
        "` + _lt("forever") + `",
        "` + _lt("infinity") + `",
        "` + _lt("unbound") + `",
        "` + _lt("universal") + `",
        "` + _lt("unbounded") + `"
    ],
    "name": "` + _lt("infinity") + `",
    "shortcodes": [
        ":infinity:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "‼️",
    "emoticons": [],
    "keywords": [
        "` + _lt("double exclamation mark") + `",
        "` + _lt("exclamation") + `",
        "` + _lt("mark") + `",
        "` + _lt("punctuation") + `",
        "` + _lt("!") + `",
        "` + _lt("!!") + `",
        "` + _lt("bangbang") + `"
    ],
    "name": "` + _lt("double exclamation mark") + `",
    "shortcodes": [
        ":double_exclamation_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⁉️",
    "emoticons": [],
    "keywords": [
        "` + _lt("exclamation") + `",
        "` + _lt("mark") + `",
        "` + _lt("punctuation") + `",
        "` + _lt("question") + `",
        "` + _lt("!") + `",
        "` + _lt("!?") + `",
        "` + _lt("?") + `",
        "` + _lt("interrobang") + `",
        "` + _lt("exclamation question mark") + `"
    ],
    "name": "` + _lt("exclamation question mark") + `",
    "shortcodes": [
        ":exclamation_question_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❓",
    "emoticons": [],
    "keywords": [
        "` + _lt("?") + `",
        "` + _lt("mark") + `",
        "` + _lt("punctuation") + `",
        "` + _lt("question") + `",
        "` + _lt("red question mark") + `"
    ],
    "name": "` + _lt("red question mark") + `",
    "shortcodes": [
        ":red_question_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❔",
    "emoticons": [],
    "keywords": [
        "` + _lt("?") + `",
        "` + _lt("mark") + `",
        "` + _lt("outlined") + `",
        "` + _lt("punctuation") + `",
        "` + _lt("question") + `",
        "` + _lt("white question mark") + `"
    ],
    "name": "` + _lt("white question mark") + `",
    "shortcodes": [
        ":white_question_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❕",
    "emoticons": [],
    "keywords": [
        "` + _lt("!") + `",
        "` + _lt("exclamation") + `",
        "` + _lt("mark") + `",
        "` + _lt("outlined") + `",
        "` + _lt("punctuation") + `",
        "` + _lt("white exclamation mark") + `"
    ],
    "name": "` + _lt("white exclamation mark") + `",
    "shortcodes": [
        ":white_exclamation_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❗",
    "emoticons": [],
    "keywords": [
        "` + _lt("!") + `",
        "` + _lt("exclamation") + `",
        "` + _lt("mark") + `",
        "` + _lt("punctuation") + `",
        "` + _lt("red exclamation mark") + `"
    ],
    "name": "` + _lt("red exclamation mark") + `",
    "shortcodes": [
        ":red_exclamation_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "〰️",
    "emoticons": [],
    "keywords": [
        "` + _lt("dash") + `",
        "` + _lt("punctuation") + `",
        "` + _lt("wavy") + `"
    ],
    "name": "` + _lt("wavy dash") + `",
    "shortcodes": [
        ":wavy_dash:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "💱",
    "emoticons": [],
    "keywords": [
        "` + _lt("bank") + `",
        "` + _lt("currency") + `",
        "` + _lt("exchange") + `",
        "` + _lt("money") + `"
    ],
    "name": "` + _lt("currency exchange") + `",
    "shortcodes": [
        ":currency_exchange:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "💲",
    "emoticons": [],
    "keywords": [
        "` + _lt("currency") + `",
        "` + _lt("dollar") + `",
        "` + _lt("heavy dollar sign") + `",
        "` + _lt("money") + `"
    ],
    "name": "` + _lt("heavy dollar sign") + `",
    "shortcodes": [
        ":heavy_dollar_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚕️",
    "emoticons": [],
    "keywords": [
        "` + _lt("aesculapius") + `",
        "` + _lt("medical symbol") + `",
        "` + _lt("medicine") + `",
        "` + _lt("staff") + `"
    ],
    "name": "` + _lt("medical symbol") + `",
    "shortcodes": [
        ":medical_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♻️",
    "emoticons": [],
    "keywords": [
        "` + _lt("recycle") + `",
        "` + _lt("recycling symbol") + `"
    ],
    "name": "` + _lt("recycling symbol") + `",
    "shortcodes": [
        ":recycling_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚜️",
    "emoticons": [],
    "keywords": [
        "` + _lt("fleur-de-lis") + `"
    ],
    "name": "` + _lt("fleur-de-lis") + `",
    "shortcodes": [
        ":fleur-de-lis:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔱",
    "emoticons": [],
    "keywords": [
        "` + _lt("anchor") + `",
        "` + _lt("emblem") + `",
        "` + _lt("ship") + `",
        "` + _lt("tool") + `",
        "` + _lt("trident") + `"
    ],
    "name": "` + _lt("trident emblem") + `",
    "shortcodes": [
        ":trident_emblem:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📛",
    "emoticons": [],
    "keywords": [
        "` + _lt("badge") + `",
        "` + _lt("name") + `"
    ],
    "name": "` + _lt("name badge") + `",
    "shortcodes": [
        ":name_badge:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔰",
    "emoticons": [],
    "keywords": [
        "` + _lt("beginner") + `",
        "` + _lt("chevron") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese symbol for beginner") + `",
        "` + _lt("leaf") + `"
    ],
    "name": "` + _lt("Japanese symbol for beginner") + `",
    "shortcodes": [
        ":Japanese_symbol_for_beginner:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⭕",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("hollow red circle") + `",
        "` + _lt("large") + `",
        "` + _lt("o") + `",
        "` + _lt("red") + `"
    ],
    "name": "` + _lt("hollow red circle") + `",
    "shortcodes": [
        ":hollow_red_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✅",
    "emoticons": [],
    "keywords": [
        "` + _lt("✓") + `",
        "` + _lt("button") + `",
        "` + _lt("check") + `",
        "` + _lt("mark") + `",
        "` + _lt("tick") + `"
    ],
    "name": "` + _lt("check mark button") + `",
    "shortcodes": [
        ":check_mark_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☑️",
    "emoticons": [],
    "keywords": [
        "` + _lt("ballot") + `",
        "` + _lt("box") + `",
        "` + _lt("check box with check") + `",
        "` + _lt("tick") + `",
        "` + _lt("tick box with tick") + `",
        "` + _lt("✓") + `",
        "` + _lt("check") + `"
    ],
    "name": "` + _lt("check box with check") + `",
    "shortcodes": [
        ":check_box_with_check:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✔️",
    "emoticons": [],
    "keywords": [
        "` + _lt("check mark") + `",
        "` + _lt("heavy tick mark") + `",
        "` + _lt("mark") + `",
        "` + _lt("tick") + `",
        "` + _lt("✓") + `",
        "` + _lt("check") + `"
    ],
    "name": "` + _lt("check mark") + `",
    "shortcodes": [
        ":check_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❌",
    "emoticons": [],
    "keywords": [
        "` + _lt("×") + `",
        "` + _lt("cancel") + `",
        "` + _lt("cross") + `",
        "` + _lt("mark") + `",
        "` + _lt("multiplication") + `",
        "` + _lt("multiply") + `",
        "` + _lt("x") + `"
    ],
    "name": "` + _lt("cross mark") + `",
    "shortcodes": [
        ":cross_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❎",
    "emoticons": [],
    "keywords": [
        "` + _lt("×") + `",
        "` + _lt("cross mark button") + `",
        "` + _lt("mark") + `",
        "` + _lt("square") + `",
        "` + _lt("x") + `"
    ],
    "name": "` + _lt("cross mark button") + `",
    "shortcodes": [
        ":cross_mark_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➰",
    "emoticons": [],
    "keywords": [
        "` + _lt("curl") + `",
        "` + _lt("curly loop") + `",
        "` + _lt("loop") + `"
    ],
    "name": "` + _lt("curly loop") + `",
    "shortcodes": [
        ":curly_loop:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➿",
    "emoticons": [],
    "keywords": [
        "` + _lt("curl") + `",
        "` + _lt("double") + `",
        "` + _lt("double curly loop") + `",
        "` + _lt("loop") + `"
    ],
    "name": "` + _lt("double curly loop") + `",
    "shortcodes": [
        ":double_curly_loop:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "〽️",
    "emoticons": [],
    "keywords": [
        "` + _lt("mark") + `",
        "` + _lt("part") + `",
        "` + _lt("part alternation mark") + `"
    ],
    "name": "` + _lt("part alternation mark") + `",
    "shortcodes": [
        ":part_alternation_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✳️",
    "emoticons": [],
    "keywords": [
        "` + _lt("*") + `",
        "` + _lt("asterisk") + `",
        "` + _lt("eight-spoked asterisk") + `"
    ],
    "name": "` + _lt("eight-spoked asterisk") + `",
    "shortcodes": [
        ":eight-spoked_asterisk:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✴️",
    "emoticons": [],
    "keywords": [
        "` + _lt("*") + `",
        "` + _lt("eight-pointed star") + `",
        "` + _lt("star") + `"
    ],
    "name": "` + _lt("eight-pointed star") + `",
    "shortcodes": [
        ":eight-pointed_star:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❇️",
    "emoticons": [],
    "keywords": [
        "` + _lt("*") + `",
        "` + _lt("sparkle") + `"
    ],
    "name": "` + _lt("sparkle") + `",
    "shortcodes": [
        ":sparkle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "©️",
    "emoticons": [],
    "keywords": [
        "` + _lt("C") + `",
        "` + _lt("copyright") + `"
    ],
    "name": "` + _lt("copyright") + `",
    "shortcodes": [
        ":copyright:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "®️",
    "emoticons": [],
    "keywords": [
        "` + _lt("R") + `",
        "` + _lt("registered") + `",
        "` + _lt("r") + `",
        "` + _lt("trademark") + `"
    ],
    "name": "` + _lt("registered") + `",
    "shortcodes": [
        ":registered:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "™️",
    "emoticons": [],
    "keywords": [
        "` + _lt("mark") + `",
        "` + _lt("TM") + `",
        "` + _lt("trade mark") + `",
        "` + _lt("trademark") + `"
    ],
    "name": "` + _lt("trade mark") + `",
    "shortcodes": [
        ":trade_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "#️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: #") + `",
    "shortcodes": [
        ":keycap:_#:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "*️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: *") + `",
    "shortcodes": [
        ":keycap:_*:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "0️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 0") + `",
    "shortcodes": [
        ":keycap:_0:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "1️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 1") + `",
    "shortcodes": [
        ":keycap:_1:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "2️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 2") + `",
    "shortcodes": [
        ":keycap:_2:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "3️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 3") + `",
    "shortcodes": [
        ":keycap:_3:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "4️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 4") + `",
    "shortcodes": [
        ":keycap:_4:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "5️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 5") + `",
    "shortcodes": [
        ":keycap:_5:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "6️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 6") + `",
    "shortcodes": [
        ":keycap:_6:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "7️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 7") + `",
    "shortcodes": [
        ":keycap:_7:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "8️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 8") + `",
    "shortcodes": [
        ":keycap:_8:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "9️⃣",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 9") + `",
    "shortcodes": [
        ":keycap:_9:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔟",
    "emoticons": [],
    "keywords": [
        "` + _lt("keycap") + `"
    ],
    "name": "` + _lt("keycap: 10") + `",
    "shortcodes": [
        ":keycap:_10:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔠",
    "emoticons": [],
    "keywords": [
        "` + _lt("input Latin uppercase") + `",
        "` + _lt("ABCD") + `",
        "` + _lt("input") + `",
        "` + _lt("latin") + `",
        "` + _lt("letters") + `",
        "` + _lt("uppercase") + `",
        "` + _lt("Latin") + `"
    ],
    "name": "` + _lt("input latin uppercase") + `",
    "shortcodes": [
        ":input_latin_uppercase:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔡",
    "emoticons": [],
    "keywords": [
        "` + _lt("input Latin lowercase") + `",
        "` + _lt("abcd") + `",
        "` + _lt("input") + `",
        "` + _lt("latin") + `",
        "` + _lt("letters") + `",
        "` + _lt("lowercase") + `",
        "` + _lt("Latin") + `"
    ],
    "name": "` + _lt("input latin lowercase") + `",
    "shortcodes": [
        ":input_latin_lowercase:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔢",
    "emoticons": [],
    "keywords": [
        "` + _lt("1234") + `",
        "` + _lt("input") + `",
        "` + _lt("numbers") + `"
    ],
    "name": "` + _lt("input numbers") + `",
    "shortcodes": [
        ":input_numbers:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔣",
    "emoticons": [],
    "keywords": [
        "` + _lt("〒♪&%") + `",
        "` + _lt("input") + `",
        "` + _lt("input symbols") + `"
    ],
    "name": "` + _lt("input symbols") + `",
    "shortcodes": [
        ":input_symbols:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔤",
    "emoticons": [],
    "keywords": [
        "` + _lt("input Latin letters") + `",
        "` + _lt("abc") + `",
        "` + _lt("alphabet") + `",
        "` + _lt("input") + `",
        "` + _lt("latin") + `",
        "` + _lt("letters") + `",
        "` + _lt("Latin") + `"
    ],
    "name": "` + _lt("input latin letters") + `",
    "shortcodes": [
        ":input_latin_letters:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🅰️",
    "emoticons": [],
    "keywords": [
        "` + _lt("A") + `",
        "` + _lt("A button (blood type)") + `",
        "` + _lt("blood type") + `"
    ],
    "name": "` + _lt("A button (blood type)") + `",
    "shortcodes": [
        ":A_button_(blood_ltype):"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆎",
    "emoticons": [],
    "keywords": [
        "` + _lt("AB") + `",
        "` + _lt("AB button (blood type)") + `",
        "` + _lt("blood type") + `"
    ],
    "name": "` + _lt("AB button (blood type)") + `",
    "shortcodes": [
        ":AB_button_(blood_ltype):"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🅱️",
    "emoticons": [],
    "keywords": [
        "` + _lt("B") + `",
        "` + _lt("B button (blood type)") + `",
        "` + _lt("blood type") + `"
    ],
    "name": "` + _lt("B button (blood type)") + `",
    "shortcodes": [
        ":B_button_(blood_ltype):"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆑",
    "emoticons": [],
    "keywords": [
        "` + _lt("CL") + `",
        "` + _lt("CL button") + `"
    ],
    "name": "` + _lt("CL button") + `",
    "shortcodes": [
        ":CL_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆒",
    "emoticons": [],
    "keywords": [
        "` + _lt("COOL") + `",
        "` + _lt("COOL button") + `"
    ],
    "name": "` + _lt("COOL button") + `",
    "shortcodes": [
        ":COOL_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆓",
    "emoticons": [],
    "keywords": [
        "` + _lt("FREE") + `",
        "` + _lt("FREE button") + `"
    ],
    "name": "` + _lt("FREE button") + `",
    "shortcodes": [
        ":FREE_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "ℹ️",
    "emoticons": [],
    "keywords": [
        "` + _lt("i") + `",
        "` + _lt("information") + `"
    ],
    "name": "` + _lt("information") + `",
    "shortcodes": [
        ":information:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆔",
    "emoticons": [],
    "keywords": [
        "` + _lt("ID") + `",
        "` + _lt("ID button") + `",
        "` + _lt("identity") + `"
    ],
    "name": "` + _lt("ID button") + `",
    "shortcodes": [
        ":ID_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "Ⓜ️",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("circled M") + `",
        "` + _lt("M") + `"
    ],
    "name": "` + _lt("circled M") + `",
    "shortcodes": [
        ":circled_M:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆕",
    "emoticons": [],
    "keywords": [
        "` + _lt("NEW") + `",
        "` + _lt("NEW button") + `"
    ],
    "name": "` + _lt("NEW button") + `",
    "shortcodes": [
        ":NEW_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆖",
    "emoticons": [],
    "keywords": [
        "` + _lt("NG") + `",
        "` + _lt("NG button") + `"
    ],
    "name": "` + _lt("NG button") + `",
    "shortcodes": [
        ":NG_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🅾️",
    "emoticons": [],
    "keywords": [
        "` + _lt("blood type") + `",
        "` + _lt("O") + `",
        "` + _lt("O button (blood type)") + `"
    ],
    "name": "` + _lt("O button (blood type)") + `",
    "shortcodes": [
        ":O_button_(blood_ltype):"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆗",
    "emoticons": [],
    "keywords": [
        "` + _lt("OK") + `",
        "` + _lt("OK button") + `"
    ],
    "name": "` + _lt("OK button") + `",
    "shortcodes": [
        ":OK_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🅿️",
    "emoticons": [],
    "keywords": [
        "` + _lt("P") + `",
        "` + _lt("P button") + `",
        "` + _lt("parking") + `"
    ],
    "name": "` + _lt("P button") + `",
    "shortcodes": [
        ":P_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆘",
    "emoticons": [],
    "keywords": [
        "` + _lt("help") + `",
        "` + _lt("SOS") + `",
        "` + _lt("SOS button") + `"
    ],
    "name": "` + _lt("SOS button") + `",
    "shortcodes": [
        ":SOS_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆙",
    "emoticons": [],
    "keywords": [
        "` + _lt("mark") + `",
        "` + _lt("UP") + `",
        "` + _lt("UP!") + `",
        "` + _lt("UP! button") + `"
    ],
    "name": "` + _lt("UP! button") + `",
    "shortcodes": [
        ":UP!_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆚",
    "emoticons": [],
    "keywords": [
        "` + _lt("versus") + `",
        "` + _lt("VS") + `",
        "` + _lt("VS button") + `"
    ],
    "name": "` + _lt("VS button") + `",
    "shortcodes": [
        ":VS_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈁",
    "emoticons": [],
    "keywords": [
        "` + _lt("“here”") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “here” button") + `",
        "` + _lt("katakana") + `",
        "` + _lt("ココ") + `"
    ],
    "name": "` + _lt("Japanese “here” button") + `",
    "shortcodes": [
        ":Japanese_“here”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈂️",
    "emoticons": [],
    "keywords": [
        "` + _lt("“service charge”") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “service charge” button") + `",
        "` + _lt("katakana") + `",
        "` + _lt("サ") + `"
    ],
    "name": "` + _lt("Japanese “service charge” button") + `",
    "shortcodes": [
        ":Japanese_“service_charge”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈷️",
    "emoticons": [],
    "keywords": [
        "` + _lt("“monthly amount”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “monthly amount” button") + `",
        "` + _lt("月") + `"
    ],
    "name": "` + _lt("Japanese “monthly amount” button") + `",
    "shortcodes": [
        ":Japanese_“monthly_amount”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈶",
    "emoticons": [],
    "keywords": [
        "` + _lt("“not free of charge”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “not free of charge” button") + `",
        "` + _lt("有") + `"
    ],
    "name": "` + _lt("Japanese “not free of charge” button") + `",
    "shortcodes": [
        ":Japanese_“not_free_of_charge”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈯",
    "emoticons": [],
    "keywords": [
        "` + _lt("“reserved”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “reserved” button") + `",
        "` + _lt("指") + `"
    ],
    "name": "` + _lt("Japanese “reserved” button") + `",
    "shortcodes": [
        ":Japanese_“reserved”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🉐",
    "emoticons": [],
    "keywords": [
        "` + _lt("“bargain”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “bargain” button") + `",
        "` + _lt("得") + `"
    ],
    "name": "` + _lt("Japanese “bargain” button") + `",
    "shortcodes": [
        ":Japanese_“bargain”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈹",
    "emoticons": [],
    "keywords": [
        "` + _lt("“discount”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “discount” button") + `",
        "` + _lt("割") + `"
    ],
    "name": "` + _lt("Japanese “discount” button") + `",
    "shortcodes": [
        ":Japanese_“discount”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈚",
    "emoticons": [],
    "keywords": [
        "` + _lt("“free of charge”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “free of charge” button") + `",
        "` + _lt("無") + `"
    ],
    "name": "` + _lt("Japanese “free of charge” button") + `",
    "shortcodes": [
        ":Japanese_“free_of_charge”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈲",
    "emoticons": [],
    "keywords": [
        "` + _lt("“prohibited”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “prohibited” button") + `",
        "` + _lt("禁") + `"
    ],
    "name": "` + _lt("Japanese “prohibited” button") + `",
    "shortcodes": [
        ":Japanese_“prohibited”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🉑",
    "emoticons": [],
    "keywords": [
        "` + _lt("“acceptable”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “acceptable” button") + `",
        "` + _lt("可") + `"
    ],
    "name": "` + _lt("Japanese “acceptable” button") + `",
    "shortcodes": [
        ":Japanese_“acceptable”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈸",
    "emoticons": [],
    "keywords": [
        "` + _lt("“application”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “application” button") + `",
        "` + _lt("申") + `"
    ],
    "name": "` + _lt("Japanese “application” button") + `",
    "shortcodes": [
        ":Japanese_“application”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈴",
    "emoticons": [],
    "keywords": [
        "` + _lt("“passing grade”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “passing grade” button") + `",
        "` + _lt("合") + `"
    ],
    "name": "` + _lt("Japanese “passing grade” button") + `",
    "shortcodes": [
        ":Japanese_“passing_grade”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈳",
    "emoticons": [],
    "keywords": [
        "` + _lt("“vacancy”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “vacancy” button") + `",
        "` + _lt("空") + `"
    ],
    "name": "` + _lt("Japanese “vacancy” button") + `",
    "shortcodes": [
        ":Japanese_“vacancy”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "㊗️",
    "emoticons": [],
    "keywords": [
        "` + _lt("“congratulations”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “congratulations” button") + `",
        "` + _lt("祝") + `"
    ],
    "name": "` + _lt("Japanese “congratulations” button") + `",
    "shortcodes": [
        ":Japanese_“congratulations”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "㊙️",
    "emoticons": [],
    "keywords": [
        "` + _lt("“secret”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “secret” button") + `",
        "` + _lt("秘") + `"
    ],
    "name": "` + _lt("Japanese “secret” button") + `",
    "shortcodes": [
        ":Japanese_“secret”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈺",
    "emoticons": [],
    "keywords": [
        "` + _lt("“open for business”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “open for business” button") + `",
        "` + _lt("営") + `"
    ],
    "name": "` + _lt("Japanese “open for business” button") + `",
    "shortcodes": [
        ":Japanese_“open_for_business”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈵",
    "emoticons": [],
    "keywords": [
        "` + _lt("“no vacancy”") + `",
        "` + _lt("ideograph") + `",
        "` + _lt("Japanese") + `",
        "` + _lt("Japanese “no vacancy” button") + `",
        "` + _lt("満") + `"
    ],
    "name": "` + _lt("Japanese “no vacancy” button") + `",
    "shortcodes": [
        ":Japanese_“no_vacancy”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔴",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("geometric") + `",
        "` + _lt("red") + `"
    ],
    "name": "` + _lt("red circle") + `",
    "shortcodes": [
        ":red_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟠",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("orange") + `"
    ],
    "name": "` + _lt("orange circle") + `",
    "shortcodes": [
        ":orange_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟡",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("yellow") + `"
    ],
    "name": "` + _lt("yellow circle") + `",
    "shortcodes": [
        ":yellow_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟢",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("green") + `"
    ],
    "name": "` + _lt("green circle") + `",
    "shortcodes": [
        ":green_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔵",
    "emoticons": [],
    "keywords": [
        "` + _lt("blue") + `",
        "` + _lt("circle") + `",
        "` + _lt("geometric") + `"
    ],
    "name": "` + _lt("blue circle") + `",
    "shortcodes": [
        ":blue_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟣",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("purple") + `"
    ],
    "name": "` + _lt("purple circle") + `",
    "shortcodes": [
        ":purple_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟤",
    "emoticons": [],
    "keywords": [
        "` + _lt("brown") + `",
        "` + _lt("circle") + `"
    ],
    "name": "` + _lt("brown circle") + `",
    "shortcodes": [
        ":brown_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚫",
    "emoticons": [],
    "keywords": [
        "` + _lt("black circle") + `",
        "` + _lt("circle") + `",
        "` + _lt("geometric") + `"
    ],
    "name": "` + _lt("black circle") + `",
    "shortcodes": [
        ":black_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚪",
    "emoticons": [],
    "keywords": [
        "` + _lt("circle") + `",
        "` + _lt("geometric") + `",
        "` + _lt("white circle") + `"
    ],
    "name": "` + _lt("white circle") + `",
    "shortcodes": [
        ":white_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟥",
    "emoticons": [],
    "keywords": [
        "` + _lt("red") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("red square") + `",
    "shortcodes": [
        ":red_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟧",
    "emoticons": [],
    "keywords": [
        "` + _lt("orange") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("orange square") + `",
    "shortcodes": [
        ":orange_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟨",
    "emoticons": [],
    "keywords": [
        "` + _lt("square") + `",
        "` + _lt("yellow") + `"
    ],
    "name": "` + _lt("yellow square") + `",
    "shortcodes": [
        ":yellow_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟩",
    "emoticons": [],
    "keywords": [
        "` + _lt("green") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("green square") + `",
    "shortcodes": [
        ":green_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟦",
    "emoticons": [],
    "keywords": [
        "` + _lt("blue") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("blue square") + `",
    "shortcodes": [
        ":blue_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟪",
    "emoticons": [],
    "keywords": [
        "` + _lt("purple") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("purple square") + `",
    "shortcodes": [
        ":purple_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟫",
    "emoticons": [],
    "keywords": [
        "` + _lt("brown") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("brown square") + `",
    "shortcodes": [
        ":brown_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬛",
    "emoticons": [],
    "keywords": [
        "` + _lt("black large square") + `",
        "` + _lt("geometric") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("black large square") + `",
    "shortcodes": [
        ":black_large_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬜",
    "emoticons": [],
    "keywords": [
        "` + _lt("geometric") + `",
        "` + _lt("square") + `",
        "` + _lt("white large square") + `"
    ],
    "name": "` + _lt("white large square") + `",
    "shortcodes": [
        ":white_large_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◼️",
    "emoticons": [],
    "keywords": [
        "` + _lt("black medium square") + `",
        "` + _lt("geometric") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("black medium square") + `",
    "shortcodes": [
        ":black_medium_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◻️",
    "emoticons": [],
    "keywords": [
        "` + _lt("geometric") + `",
        "` + _lt("square") + `",
        "` + _lt("white medium square") + `"
    ],
    "name": "` + _lt("white medium square") + `",
    "shortcodes": [
        ":white_medium_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◾",
    "emoticons": [],
    "keywords": [
        "` + _lt("black medium-small square") + `",
        "` + _lt("geometric") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("black medium-small square") + `",
    "shortcodes": [
        ":black_medium-small_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◽",
    "emoticons": [],
    "keywords": [
        "` + _lt("geometric") + `",
        "` + _lt("square") + `",
        "` + _lt("white medium-small square") + `"
    ],
    "name": "` + _lt("white medium-small square") + `",
    "shortcodes": [
        ":white_medium-small_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "▪️",
    "emoticons": [],
    "keywords": [
        "` + _lt("black small square") + `",
        "` + _lt("geometric") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("black small square") + `",
    "shortcodes": [
        ":black_small_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "▫️",
    "emoticons": [],
    "keywords": [
        "` + _lt("geometric") + `",
        "` + _lt("square") + `",
        "` + _lt("white small square") + `"
    ],
    "name": "` + _lt("white small square") + `",
    "shortcodes": [
        ":white_small_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔶",
    "emoticons": [],
    "keywords": [
        "` + _lt("diamond") + `",
        "` + _lt("geometric") + `",
        "` + _lt("large orange diamond") + `",
        "` + _lt("orange") + `"
    ],
    "name": "` + _lt("large orange diamond") + `",
    "shortcodes": [
        ":large_orange_diamond:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔷",
    "emoticons": [],
    "keywords": [
        "` + _lt("blue") + `",
        "` + _lt("diamond") + `",
        "` + _lt("geometric") + `",
        "` + _lt("large blue diamond") + `"
    ],
    "name": "` + _lt("large blue diamond") + `",
    "shortcodes": [
        ":large_blue_diamond:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔸",
    "emoticons": [],
    "keywords": [
        "` + _lt("diamond") + `",
        "` + _lt("geometric") + `",
        "` + _lt("orange") + `",
        "` + _lt("small orange diamond") + `"
    ],
    "name": "` + _lt("small orange diamond") + `",
    "shortcodes": [
        ":small_orange_diamond:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔹",
    "emoticons": [],
    "keywords": [
        "` + _lt("blue") + `",
        "` + _lt("diamond") + `",
        "` + _lt("geometric") + `",
        "` + _lt("small blue diamond") + `"
    ],
    "name": "` + _lt("small blue diamond") + `",
    "shortcodes": [
        ":small_blue_diamond:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔺",
    "emoticons": [],
    "keywords": [
        "` + _lt("geometric") + `",
        "` + _lt("red") + `",
        "` + _lt("red triangle pointed up") + `"
    ],
    "name": "` + _lt("red triangle pointed up") + `",
    "shortcodes": [
        ":red_ltriangle_pointed_up:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔻",
    "emoticons": [],
    "keywords": [
        "` + _lt("down") + `",
        "` + _lt("geometric") + `",
        "` + _lt("red") + `",
        "` + _lt("red triangle pointed down") + `"
    ],
    "name": "` + _lt("red triangle pointed down") + `",
    "shortcodes": [
        ":red_ltriangle_pointed_down:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "💠",
    "emoticons": [],
    "keywords": [
        "` + _lt("comic") + `",
        "` + _lt("diamond") + `",
        "` + _lt("diamond with a dot") + `",
        "` + _lt("geometric") + `",
        "` + _lt("inside") + `"
    ],
    "name": "` + _lt("diamond with a dot") + `",
    "shortcodes": [
        ":diamond_with_a_dot:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔘",
    "emoticons": [],
    "keywords": [
        "` + _lt("button") + `",
        "` + _lt("geometric") + `",
        "` + _lt("radio") + `"
    ],
    "name": "` + _lt("radio button") + `",
    "shortcodes": [
        ":radio_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔳",
    "emoticons": [],
    "keywords": [
        "` + _lt("button") + `",
        "` + _lt("geometric") + `",
        "` + _lt("outlined") + `",
        "` + _lt("square") + `",
        "` + _lt("white square button") + `"
    ],
    "name": "` + _lt("white square button") + `",
    "shortcodes": [
        ":white_square_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔲",
    "emoticons": [],
    "keywords": [
        "` + _lt("black square button") + `",
        "` + _lt("button") + `",
        "` + _lt("geometric") + `",
        "` + _lt("square") + `"
    ],
    "name": "` + _lt("black square button") + `",
    "shortcodes": [
        ":black_square_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏁",
    "emoticons": [],
    "keywords": [
        "` + _lt("checkered") + `",
        "` + _lt("chequered") + `",
        "` + _lt("chequered flag") + `",
        "` + _lt("racing") + `",
        "` + _lt("checkered flag") + `"
    ],
    "name": "` + _lt("chequered flag") + `",
    "shortcodes": [
        ":chequered_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚩",
    "emoticons": [],
    "keywords": [
        "` + _lt("post") + `",
        "` + _lt("triangular flag") + `",
        "` + _lt("red flag") + `"
    ],
    "name": "` + _lt("triangular flag") + `",
    "shortcodes": [
        ":triangular_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🎌",
    "emoticons": [],
    "keywords": [
        "` + _lt("celebration") + `",
        "` + _lt("cross") + `",
        "` + _lt("crossed") + `",
        "` + _lt("crossed flags") + `",
        "` + _lt("Japanese") + `"
    ],
    "name": "` + _lt("crossed flags") + `",
    "shortcodes": [
        ":crossed_flags:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴",
    "emoticons": [],
    "keywords": [
        "` + _lt("black flag") + `",
        "` + _lt("waving") + `"
    ],
    "name": "` + _lt("black flag") + `",
    "shortcodes": [
        ":black_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏳️",
    "emoticons": [],
    "keywords": [
        "` + _lt("waving") + `",
        "` + _lt("white flag") + `",
        "` + _lt("surrender") + `"
    ],
    "name": "` + _lt("white flag") + `",
    "shortcodes": [
        ":white_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏳️‍🌈",
    "emoticons": [],
    "keywords": [
        "` + _lt("pride") + `",
        "` + _lt("rainbow") + `",
        "` + _lt("rainbow flag") + `"
    ],
    "name": "` + _lt("rainbow flag") + `",
    "shortcodes": [
        ":rainbow_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴‍☠️",
    "emoticons": [],
    "keywords": [
        "` + _lt("Jolly Roger") + `",
        "` + _lt("pirate") + `",
        "` + _lt("pirate flag") + `",
        "` + _lt("plunder") + `",
        "` + _lt("treasure") + `"
    ],
    "name": "` + _lt("pirate flag") + `",
    "shortcodes": [
        ":pirate_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "emoticons": [],
    "keywords": [
        "` + _lt("flag") + `"
    ],
    "name": "` + _lt("flag: England") + `",
    "shortcodes": [
        ":england:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "emoticons": [],
    "keywords": [
        "` + _lt("flag") + `"
    ],
    "name": "` + _lt("flag: Scotland") + `",
    "shortcodes": [
        ":scotland:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "emoticons": [],
    "keywords": [
        "` + _lt("flag") + `"
    ],
    "name": "` + _lt("flag: Wales") + `",
    "shortcodes": [
        ":wales:"
    ]
}`;

export const emojisData = JSON.parse(`[
    ${emojisData1}
    ${emojisData2}
    ${emojisData3}
    ${emojisData4}
    ${emojisData5}
    ${emojisData6}
    ${emojisData7}
    ${emojisData8}
]`)
