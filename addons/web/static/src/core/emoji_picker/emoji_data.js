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

import { _t as realT } from "@web/core/l10n/translation";

// replace all double quotes with escaped double quotes
const _t = (str) => realT(str).replace(/"/g, '\\"')

const _getCategories = () => `[
    {
        "name": "Smileys & Emotion",
        "displayName": "`+ _t("Smileys & Emotion") + `",
        "title": "🙂",
        "sortId": 1
    },
    {
        "name": "People & Body",
        "displayName": "`+ _t("People & Body") + `",
        "title": "🤟",
        "sortId": 2
    },
    {
        "name": "Animals & Nature",
        "displayName": "`+ _t("Animals & Nature") + `",
        "title": "🐢",
        "sortId": 3
    },
    {
        "name": "Food & Drink",
        "displayName": "`+ _t("Food & Drink") + `",
        "title": "🍭",
        "sortId": 4
    },
    {
        "name": "Travel & Places",
        "displayName": "`+ _t("Travel & Places") + `",
        "title": "🚗",
        "sortId": 5
    },
    {
        "name": "Activities",
        "displayName": "`+ _t("Activities") + `",
        "title": "🏈",
        "sortId": 6
    },
    {
        "name": "Objects",
        "displayName": "`+ _t("Objects") + `",
        "title": "📕",
        "sortId": 7
    },
    {
        "name": "Symbols",
        "displayName": "`+ _t("Symbols") + `",
        "title": "🔠",
        "sortId": 8
    }
]`;

const _getEmojisData1 = () => `{
    "category": "Smileys & Emotion",
    "codepoints": "😀",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("grin") + `",
        "` + _t("grinning face") + `"
    ],
    "name": "` + _t("grinning face") + `",
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
        "` + _t("face") + `",
        "` + _t("grinning face with big eyes") + `",
        "` + _t("mouth") + `",
        "` + _t("open") + `",
        "` + _t("smile") + `"
    ],
    "name": "` + _t("grinning face with big eyes") + `",
    "shortcodes": [
        ":smiley:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😄",
    "emoticons": [],
    "keywords": [
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("grinning face with smiling eyes") + `",
        "` + _t("mouth") + `",
        "` + _t("open") + `",
        "` + _t("smile") + `"
    ],
    "name": "` + _t("grinning face with smiling eyes") + `",
    "shortcodes": [
        ":smile:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😁",
    "emoticons": [],
    "keywords": [
        "` + _t("beaming face with smiling eyes") + `",
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("grin") + `",
        "` + _t("smile") + `"
    ],
    "name": "` + _t("beaming face with smiling eyes") + `",
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
        "` + _t("face") + `",
        "` + _t("grinning squinting face") + `",
        "` + _t("laugh") + `",
        "` + _t("mouth") + `",
        "` + _t("satisfied") + `",
        "` + _t("smile") + `"
    ],
    "name": "` + _t("grinning squinting face") + `",
    "shortcodes": [
        ":laughing:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😅",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("face") + `",
        "` + _t("grinning face with sweat") + `",
        "` + _t("open") + `",
        "` + _t("smile") + `",
        "` + _t("sweat") + `"
    ],
    "name": "` + _t("grinning face with sweat") + `",
    "shortcodes": [
        ":sweat_smile:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤣",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("floor") + `",
        "` + _t("laugh") + `",
        "` + _t("rofl") + `",
        "` + _t("rolling") + `",
        "` + _t("rolling on the floor laughing") + `",
        "` + _t("rotfl") + `"
    ],
    "name": "` + _t("rolling on the floor laughing") + `",
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
        "` + _t("face") + `",
        "` + _t("face with tears of joy") + `",
        "` + _t("joy") + `",
        "` + _t("laugh") + `",
        "` + _t("tear") + `"
    ],
    "name": "` + _t("face with tears of joy") + `",
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
        "` + _t("face") + `",
        "` + _t("slightly smiling face") + `",
        "` + _t("smile") + `"
    ],
    "name": "` + _t("slightly smiling face") + `",
    "shortcodes": [
        ":slight_smile:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙃",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("upside-down") + `",
        "` + _t("upside down") + `",
        "` + _t("upside-down face") + `"
    ],
    "name": "` + _t("upside-down face") + `",
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
        "` + _t("face") + `",
        "` + _t("wink") + `",
        "` + _t("winking face") + `"
    ],
    "name": "` + _t("winking face") + `",
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
        "` + _t("blush") + `",
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("smile") + `",
        "` + _t("smiling face with smiling eyes") + `"
    ],
    "name": "` + _t("smiling face with smiling eyes") + `",
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
        "` + _t("angel") + `",
        "` + _t("face") + `",
        "` + _t("fantasy") + `",
        "` + _t("halo") + `",
        "` + _t("innocent") + `",
        "` + _t("smiling face with halo") + `"
    ],
    "name": "` + _t("smiling face with halo") + `",
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
        "` + _t("adore") + `",
        "` + _t("crush") + `",
        "` + _t("hearts") + `",
        "` + _t("in love") + `",
        "` + _t("smiling face with hearts") + `"
    ],
    "name": "` + _t("smiling face with hearts") + `",
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
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("love") + `",
        "` + _t("smile") + `",
        "` + _t("smiling face with heart-eyes") + `",
        "` + _t("smiling face with heart eyes") + `"
    ],
    "name": "` + _t("smiling face with heart-eyes") + `",
    "shortcodes": [
        ":heart_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤩",
    "emoticons": [],
    "keywords": [
        "` + _t("eyes") + `",
        "` + _t("face") + `",
        "` + _t("grinning") + `",
        "` + _t("star") + `",
        "` + _t("star-struck") + `"
    ],
    "name": "` + _t("star-struck") + `",
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
        "` + _t("face") + `",
        "` + _t("face blowing a kiss") + `",
        "` + _t("kiss") + `"
    ],
    "name": "` + _t("face blowing a kiss") + `",
    "shortcodes": [
        ":kissing_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😗",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("kiss") + `",
        "` + _t("kissing face") + `"
    ],
    "name": "` + _t("kissing face") + `",
    "shortcodes": [
        ":kissing:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😚",
    "emoticons": [],
    "keywords": [
        "` + _t("closed") + `",
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("kiss") + `",
        "` + _t("kissing face with closed eyes") + `"
    ],
    "name": "` + _t("kissing face with closed eyes") + `",
    "shortcodes": [
        ":kissing_closed_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😙",
    "emoticons": [],
    "keywords": [
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("kiss") + `",
        "` + _t("kissing face with smiling eyes") + `",
        "` + _t("smile") + `"
    ],
    "name": "` + _t("kissing face with smiling eyes") + `",
    "shortcodes": [
        ":kissing_smiling_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😋",
    "emoticons": [],
    "keywords": [
        "` + _t("delicious") + `",
        "` + _t("face") + `",
        "` + _t("face savoring food") + `",
        "` + _t("savouring") + `",
        "` + _t("smile") + `",
        "` + _t("yum") + `",
        "` + _t("face savouring food") + `",
        "` + _t("savoring") + `"
    ],
    "name": "` + _t("face savoring food") + `",
    "shortcodes": [
        ":yum:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😛",
    "emoticons": [
        ":p",
        ":P",
        ":-p",
        ":-P",
        "=P"
    ],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("face with tongue") + `",
        "` + _t("tongue") + `"
    ],
    "name": "` + _t("face with tongue") + `",
    "shortcodes": [
        ":stuck_out_tongue:"
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
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("joke") + `",
        "` + _t("tongue") + `",
        "` + _t("wink") + `",
        "` + _t("winking face with tongue") + `"
    ],
    "name": "` + _t("winking face with tongue") + `",
    "shortcodes": [
        ":stuck_out_tongue_winking_eye:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤪",
    "emoticons": [],
    "keywords": [
        "` + _t("eye") + `",
        "` + _t("goofy") + `",
        "` + _t("large") + `",
        "` + _t("small") + `",
        "` + _t("zany face") + `"
    ],
    "name": "` + _t("zany face") + `",
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
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("horrible") + `",
        "` + _t("squinting face with tongue") + `",
        "` + _t("taste") + `",
        "` + _t("tongue") + `"
    ],
    "name": "` + _t("squinting face with tongue") + `",
    "shortcodes": [
        ":stuck_out_tongue_closed_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤑",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("money") + `",
        "` + _t("money-mouth face") + `",
        "` + _t("mouth") + `"
    ],
    "name": "` + _t("money-mouth face") + `",
    "shortcodes": [
        ":money_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤗",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("hug") + `",
        "` + _t("hugging") + `",
        "` + _t("open hands") + `",
        "` + _t("smiling face") + `",
        "` + _t("smiling face with open hands") + `"
    ],
    "name": "` + _t("smiling face with open hands") + `",
    "shortcodes": [
        ":hugging_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤭",
    "emoticons": [],
    "keywords": [
        "` + _t("face with hand over mouth") + `",
        "` + _t("whoops") + `",
        "` + _t("oops") + `",
        "` + _t("embarrassed") + `"
    ],
    "name": "` + _t("face with hand over mouth") + `",
    "shortcodes": [
        ":hand_over_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤫",
    "emoticons": [],
    "keywords": [
        "` + _t("quiet") + `",
        "` + _t("shooshing face") + `",
        "` + _t("shush") + `",
        "` + _t("shushing face") + `"
    ],
    "name": "` + _t("shushing face") + `",
    "shortcodes": [
        ":shush:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤔",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("thinking") + `"
    ],
    "name": "` + _t("thinking face") + `",
    "shortcodes": [
        ":thinking:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤐",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("mouth") + `",
        "` + _t("zipper") + `",
        "` + _t("zipper-mouth face") + `"
    ],
    "name": "` + _t("zipper-mouth face") + `",
    "shortcodes": [
        ":zipper_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤨",
    "emoticons": [],
    "keywords": [
        "` + _t("distrust") + `",
        "` + _t("face with raised eyebrow") + `",
        "` + _t("skeptic") + `"
    ],
    "name": "` + _t("face with raised eyebrow") + `",
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
        "` + _t("deadpan") + `",
        "` + _t("face") + `",
        "` + _t("meh") + `",
        "` + _t("neutral") + `"
    ],
    "name": "` + _t("neutral face") + `",
    "shortcodes": [
        ":neutral:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😑",
    "emoticons": [],
    "keywords": [
        "` + _t("expressionless") + `",
        "` + _t("face") + `",
        "` + _t("inexpressive") + `",
        "` + _t("meh") + `",
        "` + _t("unexpressive") + `"
    ],
    "name": "` + _t("expressionless face") + `",
    "shortcodes": [
        ":expressionless:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😶",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("face without mouth") + `",
        "` + _t("mouth") + `",
        "` + _t("quiet") + `",
        "` + _t("silent") + `"
    ],
    "name": "` + _t("face without mouth") + `",
    "shortcodes": [
        ":no_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😏",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("smirk") + `",
        "` + _t("smirking face") + `"
    ],
    "name": "` + _t("smirking face") + `",
    "shortcodes": [
        ":smirk:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😒",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("unamused") + `",
        "` + _t("unhappy") + `"
    ],
    "name": "` + _t("unamused face") + `",
    "shortcodes": [
        ":unamused_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙄",
    "emoticons": [],
    "keywords": [
        "` + _t("eyeroll") + `",
        "` + _t("eyes") + `",
        "` + _t("face") + `",
        "` + _t("face with rolling eyes") + `",
        "` + _t("rolling") + `"
    ],
    "name": "` + _t("face with rolling eyes") + `",
    "shortcodes": [
        ":face_with_rolling_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😬",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("grimace") + `",
        "` + _t("grimacing face") + `"
    ],
    "name": "` + _t("grimacing face") + `",
    "shortcodes": [
        ":grimacing_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤥",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("lie") + `",
        "` + _t("lying face") + `",
        "` + _t("pinocchio") + `"
    ],
    "name": "` + _t("lying face") + `",
    "shortcodes": [
        ":lying_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😌",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("relieved") + `"
    ],
    "name": "` + _t("relieved face") + `",
    "shortcodes": [
        ":relieved_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😔",
    "emoticons": [],
    "keywords": [
        "` + _t("dejected") + `",
        "` + _t("face") + `",
        "` + _t("pensive") + `"
    ],
    "name": "` + _t("pensive face") + `",
    "shortcodes": [
        ":pensive_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😪",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("good night") + `",
        "` + _t("sleep") + `",
        "` + _t("sleepy face") + `"
    ],
    "name": "` + _t("sleepy face") + `",
    "shortcodes": [
        ":sleepy_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤤",
    "emoticons": [],
    "keywords": [
        "` + _t("drooling") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("drooling face") + `",
    "shortcodes": [
        ":drooling_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😴",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("good night") + `",
        "` + _t("sleep") + `",
        "` + _t("sleeping face") + `",
        "` + _t("ZZZ") + `"
    ],
    "name": "` + _t("sleeping face") + `",
    "shortcodes": [
        ":sleeping_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😷",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("doctor") + `",
        "` + _t("face") + `",
        "` + _t("face with medical mask") + `",
        "` + _t("mask") + `",
        "` + _t("sick") + `",
        "` + _t("ill") + `",
        "` + _t("medicine") + `",
        "` + _t("poorly") + `"
    ],
    "name": "` + _t("face with medical mask") + `",
    "shortcodes": [
        ":face_with_medical_mask:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤒",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("face with thermometer") + `",
        "` + _t("ill") + `",
        "` + _t("sick") + `",
        "` + _t("thermometer") + `"
    ],
    "name": "` + _t("face with thermometer") + `",
    "shortcodes": [
        ":face_with_thermometer:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤕",
    "emoticons": [],
    "keywords": [
        "` + _t("bandage") + `",
        "` + _t("face") + `",
        "` + _t("face with head-bandage") + `",
        "` + _t("hurt") + `",
        "` + _t("injury") + `",
        "` + _t("face with head bandage") + `"
    ],
    "name": "` + _t("face with head-bandage") + `",
    "shortcodes": [
        ":face_with_head-bandage:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤢",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("nauseated") + `",
        "` + _t("vomit") + `"
    ],
    "name": "` + _t("nauseated face") + `",
    "shortcodes": [
        ":nauseated_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤮",
    "emoticons": [],
    "keywords": [
        "` + _t("face vomiting") + `",
        "` + _t("puke") + `",
        "` + _t("sick") + `",
        "` + _t("vomit") + `"
    ],
    "name": "` + _t("face vomiting") + `",
    "shortcodes": [
        ":face_vomiting:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤧",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("gesundheit") + `",
        "` + _t("sneeze") + `",
        "` + _t("sneezing face") + `",
        "` + _t("bless you") + `"
    ],
    "name": "` + _t("sneezing face") + `",
    "shortcodes": [
        ":sneezing_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥵",
    "emoticons": [],
    "keywords": [
        "` + _t("feverish") + `",
        "` + _t("flushed") + `",
        "` + _t("heat stroke") + `",
        "` + _t("hot") + `",
        "` + _t("hot face") + `",
        "` + _t("red-faced") + `",
        "` + _t("sweating") + `"
    ],
    "name": "` + _t("hot face") + `",
    "shortcodes": [
        ":hot_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥶",
    "emoticons": [],
    "keywords": [
        "` + _t("blue-faced") + `",
        "` + _t("cold") + `",
        "` + _t("cold face") + `",
        "` + _t("freezing") + `",
        "` + _t("frostbite") + `",
        "` + _t("icicles") + `"
    ],
    "name": "` + _t("cold face") + `",
    "shortcodes": [
        ":cold_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥴",
    "emoticons": [],
    "keywords": [
        "` + _t("dizzy") + `",
        "` + _t("intoxicated") + `",
        "` + _t("tipsy") + `",
        "` + _t("uneven eyes") + `",
        "` + _t("wavy mouth") + `",
        "` + _t("woozy face") + `"
    ],
    "name": "` + _t("woozy face") + `",
    "shortcodes": [
        ":woozy_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😵",
    "emoticons": [],
    "keywords": [
        "` + _t("crossed-out eyes") + `",
        "` + _t("dead") + `",
        "` + _t("face") + `",
        "` + _t("face with crossed-out eyes") + `",
        "` + _t("knocked out") + `"
    ],
    "name": "` + _t("face with crossed-out eyes") + `",
    "shortcodes": [
        ":face_with_crossed-out_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤯",
    "emoticons": [],
    "keywords": [
        "` + _t("exploding head") + `",
        "` + _t("mind blown") + `",
        "` + _t("shocked") + `"
    ],
    "name": "` + _t("exploding head") + `",
    "shortcodes": [
        ":exploding_head:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤠",
    "emoticons": [],
    "keywords": [
        "` + _t("cowboy") + `",
        "` + _t("cowgirl") + `",
        "` + _t("face") + `",
        "` + _t("hat") + `"
    ],
    "name": "` + _t("cowboy hat face") + `",
    "shortcodes": [
        ":cowboy_hat_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥳",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("hat") + `",
        "` + _t("horn") + `",
        "` + _t("party") + `",
        "` + _t("partying face") + `"
    ],
    "name": "` + _t("partying face") + `",
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
        "` + _t("bright") + `",
        "` + _t("cool") + `",
        "` + _t("face") + `",
        "` + _t("smiling face with sunglasses") + `",
        "` + _t("sun") + `",
        "` + _t("sunglasses") + `"
    ],
    "name": "` + _t("smiling face with sunglasses") + `",
    "shortcodes": [
        ":smiling_face_with_sunglasses:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤓",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("geek") + `",
        "` + _t("nerd") + `"
    ],
    "name": "` + _t("nerd face") + `",
    "shortcodes": [
        ":nerd_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🧐",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("face with monocle") + `",
        "` + _t("monocle") + `",
        "` + _t("stuffy") + `"
    ],
    "name": "` + _t("face with monocle") + `",
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
        "` + _t("confused") + `",
        "` + _t("face") + `",
        "` + _t("meh") + `"
    ],
    "name": "` + _t("confused face") + `",
    "shortcodes": [
        ":confused_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😟",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("worried") + `"
    ],
    "name": "` + _t("worried face") + `",
    "shortcodes": [
        ":worried_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙁",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("frown") + `",
        "` + _t("slightly frowning face") + `"
    ],
    "name": "` + _t("slightly frowning face") + `",
    "shortcodes": [
        ":slightly_frowning_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😮",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("face with open mouth") + `",
        "` + _t("mouth") + `",
        "` + _t("open") + `",
        "` + _t("sympathy") + `"
    ],
    "name": "` + _t("face with open mouth") + `",
    "shortcodes": [
        ":face_with_open_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😯",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("hushed") + `",
        "` + _t("stunned") + `",
        "` + _t("surprised") + `"
    ],
    "name": "` + _t("hushed face") + `",
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
        "` + _t("astonished") + `",
        "` + _t("face") + `",
        "` + _t("shocked") + `",
        "` + _t("totally") + `"
    ],
    "name": "` + _t("astonished face") + `",
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
        "` + _t("dazed") + `",
        "` + _t("face") + `",
        "` + _t("flushed") + `"
    ],
    "name": "` + _t("flushed face") + `",
    "shortcodes": [
        ":flushed_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥺",
    "emoticons": [],
    "keywords": [
        "` + _t("begging") + `",
        "` + _t("mercy") + `",
        "` + _t("pleading face") + `",
        "` + _t("puppy eyes") + `"
    ],
    "name": "` + _t("pleading face") + `",
    "shortcodes": [
        ":pleading_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😦",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("frown") + `",
        "` + _t("frowning face with open mouth") + `",
        "` + _t("mouth") + `",
        "` + _t("open") + `"
    ],
    "name": "` + _t("frowning face with open mouth") + `",
    "shortcodes": [
        ":frowning_face_with_open_mouth:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😧",
    "emoticons": [],
    "keywords": [
        "` + _t("anguished") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("anguished face") + `",
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
        "` + _t("face") + `",
        "` + _t("fear") + `",
        "` + _t("fearful") + `",
        "` + _t("scared") + `"
    ],
    "name": "` + _t("fearful face") + `",
    "shortcodes": [
        ":fearful_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😰",
    "emoticons": [],
    "keywords": [
        "` + _t("anxious face with sweat") + `",
        "` + _t("blue") + `",
        "` + _t("cold") + `",
        "` + _t("face") + `",
        "` + _t("rushed") + `",
        "` + _t("sweat") + `"
    ],
    "name": "` + _t("anxious face with sweat") + `",
    "shortcodes": [
        ":anxious_face_with_sweat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😥",
    "emoticons": [],
    "keywords": [
        "` + _t("disappointed") + `",
        "` + _t("face") + `",
        "` + _t("relieved") + `",
        "` + _t("sad but relieved face") + `",
        "` + _t("whew") + `"
    ],
    "name": "` + _t("sad but relieved face") + `",
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
        "` + _t("cry") + `",
        "` + _t("crying face") + `",
        "` + _t("face") + `",
        "` + _t("sad") + `",
        "` + _t("tear") + `"
    ],
    "name": "` + _t("crying face") + `",
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
        "` + _t("cry") + `",
        "` + _t("face") + `",
        "` + _t("loudly crying face") + `",
        "` + _t("sad") + `",
        "` + _t("sob") + `",
        "` + _t("tear") + `"
    ],
    "name": "` + _t("loudly crying face") + `",
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
        "` + _t("face") + `",
        "` + _t("face screaming in fear") + `",
        "` + _t("fear") + `",
        "` + _t("Munch") + `",
        "` + _t("scared") + `",
        "` + _t("scream") + `",
        "` + _t("munch") + `"
    ],
    "name": "` + _t("face screaming in fear") + `",
    "shortcodes": [
        ":face_screaming_in_fear:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😖",
    "emoticons": [],
    "keywords": [
        "` + _t("confounded") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("confounded face") + `",
    "shortcodes": [
        ":confounded_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😣",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("persevere") + `",
        "` + _t("persevering face") + `"
    ],
    "name": "` + _t("persevering face") + `",
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
        "` + _t("disappointed") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("disappointed face") + `",
    "shortcodes": [
        ":disappointed_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😓",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("downcast face with sweat") + `",
        "` + _t("face") + `",
        "` + _t("sweat") + `"
    ],
    "name": "` + _t("downcast face with sweat") + `",
    "shortcodes": [
        ":downcast_face_with_sweat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😩",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("tired") + `",
        "` + _t("weary") + `"
    ],
    "name": "` + _t("weary face") + `",
    "shortcodes": [
        ":weary_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😫",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("tired") + `"
    ],
    "name": "` + _t("tired face") + `",
    "shortcodes": [
        ":tired_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🥱",
    "emoticons": [],
    "keywords": [
        "` + _t("bored") + `",
        "` + _t("tired") + `",
        "` + _t("yawn") + `",
        "` + _t("yawning face") + `"
    ],
    "name": "` + _t("yawning face") + `",
    "shortcodes": [
        ":yawning_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😤",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("face with steam from nose") + `",
        "` + _t("triumph") + `",
        "` + _t("won") + `",
        "` + _t("angry") + `",
        "` + _t("frustration") + `"
    ],
    "name": "` + _t("face with steam from nose") + `",
    "shortcodes": [
        ":face_with_steam_from_nose:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😡",
    "emoticons": [],
    "keywords": [
        "` + _t("angry") + `",
        "` + _t("enraged") + `",
        "` + _t("face") + `",
        "` + _t("mad") + `",
        "` + _t("pouting") + `",
        "` + _t("rage") + `",
        "` + _t("red") + `"
    ],
    "name": "` + _t("enraged face") + `",
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
        "` + _t("anger") + `",
        "` + _t("angry") + `",
        "` + _t("face") + `",
        "` + _t("mad") + `"
    ],
    "name": "` + _t("angry face") + `",
    "shortcodes": [
        ":angry_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤬",
    "emoticons": [],
    "keywords": [
        "` + _t("face with symbols on mouth") + `",
        "` + _t("swearing") + `"
    ],
    "name": "` + _t("face with symbols on mouth") + `",
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
        "` + _t("devil") + `",
        "` + _t("face") + `",
        "` + _t("fantasy") + `",
        "` + _t("horns") + `",
        "` + _t("smile") + `",
        "` + _t("smiling face with horns") + `",
        "` + _t("fairy tale") + `"
    ],
    "name": "` + _t("smiling face with horns") + `",
    "shortcodes": [
        ":smiling_face_with_horns:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👿",
    "emoticons": [],
    "keywords": [
        "` + _t("angry face with horns") + `",
        "` + _t("demon") + `",
        "` + _t("devil") + `",
        "` + _t("face") + `",
        "` + _t("fantasy") + `",
        "` + _t("imp") + `"
    ],
    "name": "` + _t("angry face with horns") + `",
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
        "` + _t("death") + `",
        "` + _t("face") + `",
        "` + _t("fairy tale") + `",
        "` + _t("monster") + `",
        "` + _t("skull") + `"
    ],
    "name": "` + _t("skull") + `",
    "shortcodes": [
        ":skull:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "☠️",
    "emoticons": [],
    "keywords": [
        "` + _t("crossbones") + `",
        "` + _t("death") + `",
        "` + _t("face") + `",
        "` + _t("monster") + `",
        "` + _t("skull") + `",
        "` + _t("skull and crossbones") + `"
    ],
    "name": "` + _t("skull and crossbones") + `",
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
        "` + _t("dung") + `",
        "` + _t("face") + `",
        "` + _t("monster") + `",
        "` + _t("pile of poo") + `",
        "` + _t("poo") + `",
        "` + _t("poop") + `"
    ],
    "name": "` + _t("pile of poo") + `",
    "shortcodes": [
        ":pile_of_poo:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤡",
    "emoticons": [],
    "keywords": [
        "` + _t("clown") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("clown face") + `",
    "shortcodes": [
        ":clown_face:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👹",
    "emoticons": [],
    "keywords": [
        "` + _t("creature") + `",
        "` + _t("face") + `",
        "` + _t("fairy tale") + `",
        "` + _t("fantasy") + `",
        "` + _t("monster") + `",
        "` + _t("ogre") + `"
    ],
    "name": "` + _t("ogre") + `",
    "shortcodes": [
        ":ogre:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👺",
    "emoticons": [],
    "keywords": [
        "` + _t("creature") + `",
        "` + _t("face") + `",
        "` + _t("fairy tale") + `",
        "` + _t("fantasy") + `",
        "` + _t("goblin") + `",
        "` + _t("monster") + `"
    ],
    "name": "` + _t("goblin") + `",
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
        "` + _t("creature") + `",
        "` + _t("face") + `",
        "` + _t("fairy tale") + `",
        "` + _t("fantasy") + `",
        "` + _t("ghost") + `",
        "` + _t("monster") + `"
    ],
    "name": "` + _t("ghost") + `",
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
        "` + _t("alien") + `",
        "` + _t("creature") + `",
        "` + _t("extraterrestrial") + `",
        "` + _t("face") + `",
        "` + _t("fantasy") + `",
        "` + _t("ufo") + `"
    ],
    "name": "` + _t("alien") + `",
    "shortcodes": [
        ":alien:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👾",
    "emoticons": [],
    "keywords": [
        "` + _t("alien") + `",
        "` + _t("creature") + `",
        "` + _t("extraterrestrial") + `",
        "` + _t("face") + `",
        "` + _t("monster") + `",
        "` + _t("ufo") + `"
    ],
    "name": "` + _t("alien monster") + `",
    "shortcodes": [
        ":alien_monster:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤖",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("monster") + `",
        "` + _t("robot") + `"
    ],
    "name": "` + _t("robot") + `",
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
        "` + _t("cat") + `",
        "` + _t("face") + `",
        "` + _t("grinning") + `",
        "` + _t("mouth") + `",
        "` + _t("open") + `",
        "` + _t("smile") + `"
    ],
    "name": "` + _t("grinning cat") + `",
    "shortcodes": [
        ":grinning_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😸",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("grin") + `",
        "` + _t("grinning cat with smiling eyes") + `",
        "` + _t("smile") + `"
    ],
    "name": "` + _t("grinning cat with smiling eyes") + `",
    "shortcodes": [
        ":grinning_cat_with_smiling_eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😹",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("cat with tears of joy") + `",
        "` + _t("face") + `",
        "` + _t("joy") + `",
        "` + _t("tear") + `"
    ],
    "name": "` + _t("cat with tears of joy") + `",
    "shortcodes": [
        ":cat_with_tears_of_joy:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😻",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("heart") + `",
        "` + _t("love") + `",
        "` + _t("smile") + `",
        "` + _t("smiling cat with heart-eyes") + `",
        "` + _t("smiling cat face with heart eyes") + `",
        "` + _t("smiling cat face with heart-eyes") + `"
    ],
    "name": "` + _t("smiling cat with heart-eyes") + `",
    "shortcodes": [
        ":smiling_cat_with_heart-eyes:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😼",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("cat with wry smile") + `",
        "` + _t("face") + `",
        "` + _t("ironic") + `",
        "` + _t("smile") + `",
        "` + _t("wry") + `"
    ],
    "name": "` + _t("cat with wry smile") + `",
    "shortcodes": [
        ":cat_with_wry_smile:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😽",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("eye") + `",
        "` + _t("face") + `",
        "` + _t("kiss") + `",
        "` + _t("kissing cat") + `"
    ],
    "name": "` + _t("kissing cat") + `",
    "shortcodes": [
        ":kissing_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🙀",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("face") + `",
        "` + _t("oh") + `",
        "` + _t("surprised") + `",
        "` + _t("weary") + `"
    ],
    "name": "` + _t("weary cat") + `",
    "shortcodes": [
        ":weary_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😿",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("cry") + `",
        "` + _t("crying cat") + `",
        "` + _t("face") + `",
        "` + _t("sad") + `",
        "` + _t("tear") + `"
    ],
    "name": "` + _t("crying cat") + `",
    "shortcodes": [
        ":crying_cat:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "😾",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("face") + `",
        "` + _t("pouting") + `"
    ],
    "name": "` + _t("pouting cat") + `",
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
        "` + _t("evil") + `",
        "` + _t("face") + `",
        "` + _t("forbidden") + `",
        "` + _t("monkey") + `",
        "` + _t("see") + `",
        "` + _t("see-no-evil monkey") + `"
    ],
    "name": "` + _t("see-no-evil monkey") + `",
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
        "` + _t("evil") + `",
        "` + _t("face") + `",
        "` + _t("forbidden") + `",
        "` + _t("hear") + `",
        "` + _t("hear-no-evil monkey") + `",
        "` + _t("monkey") + `"
    ],
    "name": "` + _t("hear-no-evil monkey") + `",
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
        "` + _t("evil") + `",
        "` + _t("face") + `",
        "` + _t("forbidden") + `",
        "` + _t("monkey") + `",
        "` + _t("speak") + `",
        "` + _t("speak-no-evil monkey") + `"
    ],
    "name": "` + _t("speak-no-evil monkey") + `",
    "shortcodes": [
        ":speak-no-evil_monkey:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💋",
    "emoticons": [],
    "keywords": [
        "` + _t("kiss") + `",
        "` + _t("kiss mark") + `",
        "` + _t("lips") + `"
    ],
    "name": "` + _t("kiss mark") + `",
    "shortcodes": [
        ":kiss_mark:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💌",
    "emoticons": [],
    "keywords": [
        "` + _t("heart") + `",
        "` + _t("letter") + `",
        "` + _t("love") + `",
        "` + _t("mail") + `"
    ],
    "name": "` + _t("love letter") + `",
    "shortcodes": [
        ":love_letter:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💘",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("cupid") + `",
        "` + _t("heart with arrow") + `"
    ],
    "name": "` + _t("heart with arrow") + `",
    "shortcodes": [
        ":heart_with_arrow:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💝",
    "emoticons": [],
    "keywords": [
        "` + _t("heart with ribbon") + `",
        "` + _t("ribbon") + `",
        "` + _t("valentine") + `"
    ],
    "name": "` + _t("heart with ribbon") + `",
    "shortcodes": [
        ":heart_with_ribbon:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💖",
    "emoticons": [],
    "keywords": [
        "` + _t("excited") + `",
        "` + _t("sparkle") + `",
        "` + _t("sparkling heart") + `"
    ],
    "name": "` + _t("sparkling heart") + `",
    "shortcodes": [
        ":sparkling_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💗",
    "emoticons": [],
    "keywords": [
        "` + _t("excited") + `",
        "` + _t("growing") + `",
        "` + _t("growing heart") + `",
        "` + _t("nervous") + `",
        "` + _t("pulse") + `"
    ],
    "name": "` + _t("growing heart") + `",
    "shortcodes": [
        ":growing_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💓",
    "emoticons": [],
    "keywords": [
        "` + _t("beating") + `",
        "` + _t("beating heart") + `",
        "` + _t("heartbeat") + `",
        "` + _t("pulsating") + `"
    ],
    "name": "` + _t("beating heart") + `",
    "shortcodes": [
        ":beating_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💞",
    "emoticons": [],
    "keywords": [
        "` + _t("revolving") + `",
        "` + _t("revolving hearts") + `"
    ],
    "name": "` + _t("revolving hearts") + `",
    "shortcodes": [
        ":revolving_hearts:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💕",
    "emoticons": [],
    "keywords": [
        "` + _t("love") + `",
        "` + _t("two hearts") + `"
    ],
    "name": "` + _t("two hearts") + `",
    "shortcodes": [
        ":two_hearts:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💟",
    "emoticons": [],
    "keywords": [
        "` + _t("heart") + `",
        "` + _t("heart decoration") + `"
    ],
    "name": "` + _t("heart decoration") + `",
    "shortcodes": [
        ":heart_decoration:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "❣️",
    "emoticons": [],
    "keywords": [
        "` + _t("exclamation") + `",
        "` + _t("heart exclamation") + `",
        "` + _t("mark") + `",
        "` + _t("punctuation") + `"
    ],
    "name": "` + _t("heart exclamation") + `",
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
        "` + _t("break") + `",
        "` + _t("broken") + `",
        "` + _t("broken heart") + `"
    ],
    "name": "` + _t("broken heart") + `",
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
        "` + _t("heart") + `",
        "` + _t("red heart") + `"
    ],
    "name": "` + _t("red heart") + `",
    "shortcodes": [
        ":red_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🧡",
    "emoticons": [],
    "keywords": [
        "` + _t("orange") + `",
        "` + _t("orange heart") + `"
    ],
    "name": "` + _t("orange heart") + `",
    "shortcodes": [
        ":orange_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💛",
    "emoticons": [],
    "keywords": [
        "` + _t("yellow") + `",
        "` + _t("yellow heart") + `"
    ],
    "name": "` + _t("yellow heart") + `",
    "shortcodes": [
        ":yellow_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💚",
    "emoticons": [],
    "keywords": [
        "` + _t("green") + `",
        "` + _t("green heart") + `"
    ],
    "name": "` + _t("green heart") + `",
    "shortcodes": [
        ":green_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💙",
    "emoticons": [],
    "keywords": [
        "` + _t("blue") + `",
        "` + _t("blue heart") + `"
    ],
    "name": "` + _t("blue heart") + `",
    "shortcodes": [
        ":blue_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💜",
    "emoticons": [],
    "keywords": [
        "` + _t("purple") + `",
        "` + _t("purple heart") + `"
    ],
    "name": "` + _t("purple heart") + `",
    "shortcodes": [
        ":purple_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤎",
    "emoticons": [],
    "keywords": [
        "` + _t("brown") + `",
        "` + _t("heart") + `"
    ],
    "name": "` + _t("brown heart") + `",
    "shortcodes": [
        ":brown_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🖤",
    "emoticons": [],
    "keywords": [
        "` + _t("black") + `",
        "` + _t("black heart") + `",
        "` + _t("evil") + `",
        "` + _t("wicked") + `"
    ],
    "name": "` + _t("black heart") + `",
    "shortcodes": [
        ":black_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🤍",
    "emoticons": [],
    "keywords": [
        "` + _t("heart") + `",
        "` + _t("white") + `"
    ],
    "name": "` + _t("white heart") + `",
    "shortcodes": [
        ":white_heart:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💯",
    "emoticons": [],
    "keywords": [
        "` + _t("100") + `",
        "` + _t("full") + `",
        "` + _t("hundred") + `",
        "` + _t("hundred points") + `",
        "` + _t("score") + `"
    ],
    "name": "` + _t("hundred points") + `",
    "shortcodes": [
        ":hundred_points:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💢",
    "emoticons": [],
    "keywords": [
        "` + _t("anger symbol") + `",
        "` + _t("angry") + `",
        "` + _t("comic") + `",
        "` + _t("mad") + `"
    ],
    "name": "` + _t("anger symbol") + `",
    "shortcodes": [
        ":anger_symbol:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💥",
    "emoticons": [],
    "keywords": [
        "` + _t("boom") + `",
        "` + _t("collision") + `",
        "` + _t("comic") + `"
    ],
    "name": "` + _t("collision") + `",
    "shortcodes": [
        ":collision:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💫",
    "emoticons": [],
    "keywords": [
        "` + _t("comic") + `",
        "` + _t("dizzy") + `",
        "` + _t("star") + `"
    ],
    "name": "` + _t("dizzy") + `",
    "shortcodes": [
        ":dizzy:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💦",
    "emoticons": [],
    "keywords": [
        "` + _t("comic") + `",
        "` + _t("splashing") + `",
        "` + _t("sweat") + `",
        "` + _t("sweat droplets") + `"
    ],
    "name": "` + _t("sweat droplets") + `",
    "shortcodes": [
        ":sweat_droplets:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💨",
    "emoticons": [],
    "keywords": [
        "` + _t("comic") + `",
        "` + _t("dash") + `",
        "` + _t("dashing away") + `",
        "` + _t("running") + `"
    ],
    "name": "` + _t("dashing away") + `",
    "shortcodes": [
        ":dashing_away:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🕳️",
    "emoticons": [],
    "keywords": [
        "` + _t("hole") + `"
    ],
    "name": "` + _t("hole") + `",
    "shortcodes": [
        ":hole:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💣",
    "emoticons": [],
    "keywords": [
        "` + _t("bomb") + `",
        "` + _t("comic") + `"
    ],
    "name": "` + _t("bomb") + `",
    "shortcodes": [
        ":bomb:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💬",
    "emoticons": [],
    "keywords": [
        "` + _t("balloon") + `",
        "` + _t("bubble") + `",
        "` + _t("comic") + `",
        "` + _t("dialog") + `",
        "` + _t("speech") + `"
    ],
    "name": "` + _t("speech balloon") + `",
    "shortcodes": [
        ":speech_balloon:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "👁️‍🗨️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("eye in speech bubble") + `",
    "shortcodes": [
        ":eye_in_speech_bubble:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🗨️",
    "emoticons": [],
    "keywords": [
        "` + _t("balloon") + `",
        "` + _t("bubble") + `",
        "` + _t("dialog") + `",
        "` + _t("left speech bubble") + `",
        "` + _t("speech") + `",
        "` + _t("dialogue") + `"
    ],
    "name": "` + _t("left speech bubble") + `",
    "shortcodes": [
        ":left_speech_bubble:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "🗯️",
    "emoticons": [],
    "keywords": [
        "` + _t("angry") + `",
        "` + _t("balloon") + `",
        "` + _t("bubble") + `",
        "` + _t("mad") + `",
        "` + _t("right anger bubble") + `"
    ],
    "name": "` + _t("right anger bubble") + `",
    "shortcodes": [
        ":right_anger_bubble:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💭",
    "emoticons": [],
    "keywords": [
        "` + _t("balloon") + `",
        "` + _t("bubble") + `",
        "` + _t("comic") + `",
        "` + _t("thought") + `"
    ],
    "name": "` + _t("thought balloon") + `",
    "shortcodes": [
        ":thought_balloon:"
    ]
},
{
    "category": "Smileys & Emotion",
    "codepoints": "💤",
    "emoticons": [],
    "keywords": [
        "` + _t("comic") + `",
        "` + _t("good night") + `",
        "` + _t("sleep") + `",
        "` + _t("ZZZ") + `"
    ],
    "name": "` + _t("ZZZ") + `",
    "shortcodes": [
        ":ZZZ:"
    ]
},`;

const _getEmojisData2 = () => `{
    "category": "People & Body",
    "codepoints": "👋",
    "emoticons": [],
    "keywords": [
        "` + _t("hand") + `",
        "` + _t("wave") + `",
        "` + _t("waving") + `"
    ],
    "name": "` + _t("waving hand") + `",
    "shortcodes": [
        ":waving_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤚",
    "emoticons": [],
    "keywords": [
        "` + _t("backhand") + `",
        "` + _t("raised") + `",
        "` + _t("raised back of hand") + `"
    ],
    "name": "` + _t("raised back of hand") + `",
    "shortcodes": [
        ":raised_back_of_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🖐️",
    "emoticons": [],
    "keywords": [
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("hand with fingers splayed") + `",
        "` + _t("splayed") + `"
    ],
    "name": "` + _t("hand with fingers splayed") + `",
    "shortcodes": [
        ":hand_with_fingers_splayed:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "✋",
    "emoticons": [],
    "keywords": [
        "` + _t("hand") + `",
        "` + _t("high 5") + `",
        "` + _t("high five") + `",
        "` + _t("raised hand") + `"
    ],
    "name": "` + _t("raised hand") + `",
    "shortcodes": [
        ":raised_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🖖",
    "emoticons": [],
    "keywords": [
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("spock") + `",
        "` + _t("vulcan") + `",
        "` + _t("Vulcan salute") + `",
        "` + _t("vulcan salute") + `"
    ],
    "name": "` + _t("vulcan salute") + `",
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
        "` + _t("hand") + `",
        "` + _t("OK") + `",
        "` + _t("perfect") + `"
    ],
    "name": "` + _t("OK hand") + `",
    "shortcodes": [
        ":OK_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤏",
    "emoticons": [],
    "keywords": [
        "` + _t("pinching hand") + `",
        "` + _t("small amount") + `"
    ],
    "name": "` + _t("pinching hand") + `",
    "shortcodes": [
        ":pinching_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "✌️",
    "emoticons": [],
    "keywords": [
        "` + _t("hand") + `",
        "` + _t("v") + `",
        "` + _t("victory") + `"
    ],
    "name": "` + _t("victory hand") + `",
    "shortcodes": [
        ":victory_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤞",
    "emoticons": [],
    "keywords": [
        "` + _t("cross") + `",
        "` + _t("crossed fingers") + `",
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("luck") + `",
        "` + _t("good luck") + `"
    ],
    "name": "` + _t("crossed fingers") + `",
    "shortcodes": [
        ":crossed_fingers:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤟",
    "emoticons": [],
    "keywords": [
        "` + _t("hand") + `",
        "` + _t("ILY") + `",
        "` + _t("love-you gesture") + `",
        "` + _t("love you gesture") + `"
    ],
    "name": "` + _t("love-you gesture") + `",
    "shortcodes": [
        ":love-you_gesture:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤘",
    "emoticons": [],
    "keywords": [
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("horns") + `",
        "` + _t("rock-on") + `",
        "` + _t("sign of the horns") + `",
        "` + _t("rock on") + `"
    ],
    "name": "` + _t("sign of the horns") + `",
    "shortcodes": [
        ":sign_of_the_horns:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤙",
    "emoticons": [],
    "keywords": [
        "` + _t("call") + `",
        "` + _t("call me hand") + `",
        "` + _t("call-me hand") + `",
        "` + _t("hand") + `",
        "` + _t("shaka") + `",
        "` + _t("hang loose") + `",
        "` + _t("Shaka") + `"
    ],
    "name": "` + _t("call me hand") + `",
    "shortcodes": [
        ":call_me_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👈",
    "emoticons": [],
    "keywords": [
        "` + _t("backhand") + `",
        "` + _t("backhand index pointing left") + `",
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("index") + `",
        "` + _t("point") + `"
    ],
    "name": "` + _t("backhand index pointing left") + `",
    "shortcodes": [
        ":backhand_index_pointing_left:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👉",
    "emoticons": [],
    "keywords": [
        "` + _t("backhand") + `",
        "` + _t("backhand index pointing right") + `",
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("index") + `",
        "` + _t("point") + `"
    ],
    "name": "` + _t("backhand index pointing right") + `",
    "shortcodes": [
        ":backhand_index_pointing_right:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👆",
    "emoticons": [],
    "keywords": [
        "` + _t("backhand") + `",
        "` + _t("backhand index pointing up") + `",
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("point") + `",
        "` + _t("up") + `"
    ],
    "name": "` + _t("backhand index pointing up") + `",
    "shortcodes": [
        ":backhand_index_pointing_up:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🖕",
    "emoticons": [],
    "keywords": [
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("middle finger") + `"
    ],
    "name": "` + _t("middle finger") + `",
    "shortcodes": [
        ":middle_finger:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👇",
    "emoticons": [],
    "keywords": [
        "` + _t("backhand") + `",
        "` + _t("backhand index pointing down") + `",
        "` + _t("down") + `",
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("point") + `"
    ],
    "name": "` + _t("backhand index pointing down") + `",
    "shortcodes": [
        ":backhand_index_pointing_down:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "☝️",
    "emoticons": [],
    "keywords": [
        "` + _t("finger") + `",
        "` + _t("hand") + `",
        "` + _t("index") + `",
        "` + _t("index pointing up") + `",
        "` + _t("point") + `",
        "` + _t("up") + `"
    ],
    "name": "` + _t("index pointing up") + `",
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
        "` + _t("+1") + `",
        "` + _t("hand") + `",
        "` + _t("thumb") + `",
        "` + _t("thumbs up") + `",
        "` + _t("up") + `"
    ],
    "name": "` + _t("thumbs up") + `",
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
        "` + _t("-1") + `",
        "` + _t("down") + `",
        "` + _t("hand") + `",
        "` + _t("thumb") + `",
        "` + _t("thumbs down") + `"
    ],
    "name": "` + _t("thumbs down") + `",
    "shortcodes": [
        ":thumbs_down:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "✊",
    "emoticons": [],
    "keywords": [
        "` + _t("clenched") + `",
        "` + _t("fist") + `",
        "` + _t("hand") + `",
        "` + _t("punch") + `",
        "` + _t("raised fist") + `"
    ],
    "name": "` + _t("raised fist") + `",
    "shortcodes": [
        ":raised_fist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👊",
    "emoticons": [],
    "keywords": [
        "` + _t("clenched") + `",
        "` + _t("fist") + `",
        "` + _t("hand") + `",
        "` + _t("oncoming fist") + `",
        "` + _t("punch") + `"
    ],
    "name": "` + _t("oncoming fist") + `",
    "shortcodes": [
        ":oncoming_fist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤛",
    "emoticons": [],
    "keywords": [
        "` + _t("fist") + `",
        "` + _t("left-facing fist") + `",
        "` + _t("leftwards") + `",
        "` + _t("leftward") + `"
    ],
    "name": "` + _t("left-facing fist") + `",
    "shortcodes": [
        ":left-facing_fist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤜",
    "emoticons": [],
    "keywords": [
        "` + _t("fist") + `",
        "` + _t("right-facing fist") + `",
        "` + _t("rightwards") + `",
        "` + _t("rightward") + `"
    ],
    "name": "` + _t("right-facing fist") + `",
    "shortcodes": [
        ":right-facing_fist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👏",
    "emoticons": [],
    "keywords": [
        "` + _t("clap") + `",
        "` + _t("clapping hands") + `",
        "` + _t("hand") + `"
    ],
    "name": "` + _t("clapping hands") + `",
    "shortcodes": [
        ":clapping_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙌",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("gesture") + `",
        "` + _t("hand") + `",
        "` + _t("hooray") + `",
        "` + _t("raised") + `",
        "` + _t("raising hands") + `",
        "` + _t("woo hoo") + `",
        "` + _t("yay") + `"
    ],
    "name": "` + _t("raising hands") + `",
    "shortcodes": [
        ":raising_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👐",
    "emoticons": [],
    "keywords": [
        "` + _t("hand") + `",
        "` + _t("open") + `",
        "` + _t("open hands") + `"
    ],
    "name": "` + _t("open hands") + `",
    "shortcodes": [
        ":open_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤲",
    "emoticons": [],
    "keywords": [
        "` + _t("palms up together") + `",
        "` + _t("prayer") + `"
    ],
    "name": "` + _t("palms up together") + `",
    "shortcodes": [
        ":palms_up_together:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤝",
    "emoticons": [],
    "keywords": [
        "` + _t("agreement") + `",
        "` + _t("hand") + `",
        "` + _t("handshake") + `",
        "` + _t("meeting") + `",
        "` + _t("shake") + `"
    ],
    "name": "` + _t("handshake") + `",
    "shortcodes": [
        ":handshake:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙏",
    "emoticons": [],
    "keywords": [
        "` + _t("ask") + `",
        "` + _t("folded hands") + `",
        "` + _t("hand") + `",
        "` + _t("high 5") + `",
        "` + _t("high five") + `",
        "` + _t("please") + `",
        "` + _t("pray") + `",
        "` + _t("thanks") + `"
    ],
    "name": "` + _t("folded hands") + `",
    "shortcodes": [
        ":folded_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "✍️",
    "emoticons": [],
    "keywords": [
        "` + _t("hand") + `",
        "` + _t("write") + `",
        "` + _t("writing hand") + `"
    ],
    "name": "` + _t("writing hand") + `",
    "shortcodes": [
        ":writing_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💅",
    "emoticons": [],
    "keywords": [
        "` + _t("care") + `",
        "` + _t("cosmetics") + `",
        "` + _t("manicure") + `",
        "` + _t("nail") + `",
        "` + _t("polish") + `"
    ],
    "name": "` + _t("nail polish") + `",
    "shortcodes": [
        ":nail_polish:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤳",
    "emoticons": [],
    "keywords": [
        "` + _t("camera") + `",
        "` + _t("phone") + `",
        "` + _t("selfie") + `"
    ],
    "name": "` + _t("selfie") + `",
    "shortcodes": [
        ":selfie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💪",
    "emoticons": [],
    "keywords": [
        "` + _t("biceps") + `",
        "` + _t("comic") + `",
        "` + _t("flex") + `",
        "` + _t("flexed biceps") + `",
        "` + _t("muscle") + `"
    ],
    "name": "` + _t("flexed biceps") + `",
    "shortcodes": [
        ":flexed_biceps:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦾",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("mechanical arm") + `",
        "` + _t("prosthetic") + `"
    ],
    "name": "` + _t("mechanical arm") + `",
    "shortcodes": [
        ":mechanical_arm:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦿",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("mechanical leg") + `",
        "` + _t("prosthetic") + `"
    ],
    "name": "` + _t("mechanical leg") + `",
    "shortcodes": [
        ":mechanical_leg:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦵",
    "emoticons": [],
    "keywords": [
        "` + _t("kick") + `",
        "` + _t("leg") + `",
        "` + _t("limb") + `"
    ],
    "name": "` + _t("leg") + `",
    "shortcodes": [
        ":leg:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦶",
    "emoticons": [],
    "keywords": [
        "` + _t("foot") + `",
        "` + _t("kick") + `",
        "` + _t("stomp") + `"
    ],
    "name": "` + _t("foot") + `",
    "shortcodes": [
        ":foot:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👂",
    "emoticons": [],
    "keywords": [
        "` + _t("body") + `",
        "` + _t("ear") + `"
    ],
    "name": "` + _t("ear") + `",
    "shortcodes": [
        ":ear:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦻",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("ear with hearing aid") + `",
        "` + _t("hard of hearing") + `",
        "` + _t("hearing impaired") + `"
    ],
    "name": "` + _t("ear with hearing aid") + `",
    "shortcodes": [
        ":ear_with_hearing_aid:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👃",
    "emoticons": [],
    "keywords": [
        "` + _t("body") + `",
        "` + _t("nose") + `"
    ],
    "name": "` + _t("nose") + `",
    "shortcodes": [
        ":nose:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧠",
    "emoticons": [],
    "keywords": [
        "` + _t("brain") + `",
        "` + _t("intelligent") + `"
    ],
    "name": "` + _t("brain") + `",
    "shortcodes": [
        ":brain:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦷",
    "emoticons": [],
    "keywords": [
        "` + _t("dentist") + `",
        "` + _t("tooth") + `"
    ],
    "name": "` + _t("tooth") + `",
    "shortcodes": [
        ":tooth:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦴",
    "emoticons": [],
    "keywords": [
        "` + _t("bone") + `",
        "` + _t("skeleton") + `"
    ],
    "name": "` + _t("bone") + `",
    "shortcodes": [
        ":bone:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👀",
    "emoticons": [],
    "keywords": [
        "` + _t("eye") + `",
        "` + _t("eyes") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("eyes") + `",
    "shortcodes": [
        ":eyes:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👁️",
    "emoticons": [],
    "keywords": [
        "` + _t("body") + `",
        "` + _t("eye") + `"
    ],
    "name": "` + _t("eye") + `",
    "shortcodes": [
        ":eye:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👅",
    "emoticons": [],
    "keywords": [
        "` + _t("body") + `",
        "` + _t("tongue") + `"
    ],
    "name": "` + _t("tongue") + `",
    "shortcodes": [
        ":tongue:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👄",
    "emoticons": [],
    "keywords": [
        "` + _t("lips") + `",
        "` + _t("mouth") + `"
    ],
    "name": "` + _t("mouth") + `",
    "shortcodes": [
        ":mouth:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👶",
    "emoticons": [],
    "keywords": [
        "` + _t("baby") + `",
        "` + _t("young") + `"
    ],
    "name": "` + _t("baby") + `",
    "shortcodes": [
        ":baby:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧒",
    "emoticons": [],
    "keywords": [
        "` + _t("child") + `",
        "` + _t("gender-neutral") + `",
        "` + _t("unspecified gender") + `",
        "` + _t("young") + `"
    ],
    "name": "` + _t("child") + `",
    "shortcodes": [
        ":child:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("young") + `",
        "` + _t("young person") + `"
    ],
    "name": "` + _t("boy") + `",
    "shortcodes": [
        ":boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👧",
    "emoticons": [],
    "keywords": [
        "` + _t("girl") + `",
        "` + _t("Virgo") + `",
        "` + _t("young person") + `",
        "` + _t("zodiac") + `",
        "` + _t("young") + `"
    ],
    "name": "` + _t("girl") + `",
    "shortcodes": [
        ":girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧑",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("gender-neutral") + `",
        "` + _t("person") + `",
        "` + _t("unspecified gender") + `"
    ],
    "name": "` + _t("person") + `",
    "shortcodes": [
        ":person:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👱",
    "emoticons": [],
    "keywords": [
        "` + _t("blond") + `",
        "` + _t("blond-haired person") + `",
        "` + _t("hair") + `",
        "` + _t("person: blond hair") + `"
    ],
    "name": "` + _t("person: blond hair") + `",
    "shortcodes": [
        ":person:_blond_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("man") + `",
    "shortcodes": [
        ":man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧔",
    "emoticons": [],
    "keywords": [
        "` + _t("beard") + `",
        "` + _t("person") + `",
        "` + _t("person: beard") + `"
    ],
    "name": "` + _t("person: beard") + `",
    "shortcodes": [
        ":person:_beard:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦰",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("man") + `",
        "` + _t("red hair") + `"
    ],
    "name": "` + _t("man: red hair") + `",
    "shortcodes": [
        ":man:_red_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦱",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("curly hair") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("man: curly hair") + `",
    "shortcodes": [
        ":man:_curly_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦳",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("man") + `",
        "` + _t("white hair") + `"
    ],
    "name": "` + _t("man: white hair") + `",
    "shortcodes": [
        ":man:_white_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦲",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("bald") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("man: bald") + `",
    "shortcodes": [
        ":man:_bald:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman") + `",
    "shortcodes": [
        ":woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦰",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("red hair") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman: red hair") + `",
    "shortcodes": [
        ":woman:_red_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦱",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("curly hair") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman: curly hair") + `",
    "shortcodes": [
        ":woman:_curly_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦳",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("white hair") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman: white hair") + `",
    "shortcodes": [
        ":woman:_white_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦲",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("bald") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman: bald") + `",
    "shortcodes": [
        ":woman:_bald:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👱‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("blond-haired woman") + `",
        "` + _t("blonde") + `",
        "` + _t("hair") + `",
        "` + _t("woman") + `",
        "` + _t("woman: blond hair") + `"
    ],
    "name": "` + _t("woman: blond hair") + `",
    "shortcodes": [
        ":woman:_blond_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👱‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("blond") + `",
        "` + _t("blond-haired man") + `",
        "` + _t("hair") + `",
        "` + _t("man") + `",
        "` + _t("man: blond hair") + `"
    ],
    "name": "` + _t("man: blond hair") + `",
    "shortcodes": [
        ":man:_blond_hair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧓",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("gender-neutral") + `",
        "` + _t("old") + `",
        "` + _t("older person") + `",
        "` + _t("unspecified gender") + `"
    ],
    "name": "` + _t("older person") + `",
    "shortcodes": [
        ":older_person:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👴",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("man") + `",
        "` + _t("old") + `"
    ],
    "name": "` + _t("old man") + `",
    "shortcodes": [
        ":old_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👵",
    "emoticons": [],
    "keywords": [
        "` + _t("adult") + `",
        "` + _t("old") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("old woman") + `",
    "shortcodes": [
        ":old_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙍",
    "emoticons": [],
    "keywords": [
        "` + _t("frown") + `",
        "` + _t("gesture") + `",
        "` + _t("person frowning") + `"
    ],
    "name": "` + _t("person frowning") + `",
    "shortcodes": [
        ":person_frowning:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙍‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("frowning") + `",
        "` + _t("gesture") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("man frowning") + `",
    "shortcodes": [
        ":man_frowning:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙍‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("frowning") + `",
        "` + _t("gesture") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman frowning") + `",
    "shortcodes": [
        ":woman_frowning:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙎",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("person pouting") + `",
        "` + _t("pouting") + `"
    ],
    "name": "` + _t("person pouting") + `",
    "shortcodes": [
        ":person_pouting:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙎‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("man") + `",
        "` + _t("pouting") + `"
    ],
    "name": "` + _t("man pouting") + `",
    "shortcodes": [
        ":man_pouting:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙎‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("pouting") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman pouting") + `",
    "shortcodes": [
        ":woman_pouting:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙅",
    "emoticons": [],
    "keywords": [
        "` + _t("forbidden") + `",
        "` + _t("gesture") + `",
        "` + _t("hand") + `",
        "` + _t("person gesturing NO") + `",
        "` + _t("prohibited") + `"
    ],
    "name": "` + _t("person gesturing NO") + `",
    "shortcodes": [
        ":person_gesturing_NO:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙅‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("forbidden") + `",
        "` + _t("gesture") + `",
        "` + _t("hand") + `",
        "` + _t("man") + `",
        "` + _t("man gesturing NO") + `",
        "` + _t("prohibited") + `"
    ],
    "name": "` + _t("man gesturing NO") + `",
    "shortcodes": [
        ":man_gesturing_NO:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙅‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("forbidden") + `",
        "` + _t("gesture") + `",
        "` + _t("hand") + `",
        "` + _t("prohibited") + `",
        "` + _t("woman") + `",
        "` + _t("woman gesturing NO") + `"
    ],
    "name": "` + _t("woman gesturing NO") + `",
    "shortcodes": [
        ":woman_gesturing_NO:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙆",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("hand") + `",
        "` + _t("OK") + `",
        "` + _t("person gesturing OK") + `"
    ],
    "name": "` + _t("person gesturing OK") + `",
    "shortcodes": [
        ":person_gesturing_OK:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙆‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("hand") + `",
        "` + _t("man") + `",
        "` + _t("man gesturing OK") + `",
        "` + _t("OK") + `"
    ],
    "name": "` + _t("man gesturing OK") + `",
    "shortcodes": [
        ":man_gesturing_OK:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙆‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("hand") + `",
        "` + _t("OK") + `",
        "` + _t("woman") + `",
        "` + _t("woman gesturing OK") + `"
    ],
    "name": "` + _t("woman gesturing OK") + `",
    "shortcodes": [
        ":woman_gesturing_OK:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💁",
    "emoticons": [],
    "keywords": [
        "` + _t("hand") + `",
        "` + _t("help") + `",
        "` + _t("information") + `",
        "` + _t("person tipping hand") + `",
        "` + _t("sassy") + `",
        "` + _t("tipping") + `"
    ],
    "name": "` + _t("person tipping hand") + `",
    "shortcodes": [
        ":person_tipping_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💁‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man") + `",
        "` + _t("man tipping hand") + `",
        "` + _t("sassy") + `",
        "` + _t("tipping hand") + `"
    ],
    "name": "` + _t("man tipping hand") + `",
    "shortcodes": [
        ":man_tipping_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💁‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("sassy") + `",
        "` + _t("tipping hand") + `",
        "` + _t("woman") + `",
        "` + _t("woman tipping hand") + `"
    ],
    "name": "` + _t("woman tipping hand") + `",
    "shortcodes": [
        ":woman_tipping_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙋",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("hand") + `",
        "` + _t("happy") + `",
        "` + _t("person raising hand") + `",
        "` + _t("raised") + `"
    ],
    "name": "` + _t("person raising hand") + `",
    "shortcodes": [
        ":person_raising_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙋‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("man") + `",
        "` + _t("man raising hand") + `",
        "` + _t("raising hand") + `"
    ],
    "name": "` + _t("man raising hand") + `",
    "shortcodes": [
        ":man_raising_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙋‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("gesture") + `",
        "` + _t("raising hand") + `",
        "` + _t("woman") + `",
        "` + _t("woman raising hand") + `"
    ],
    "name": "` + _t("woman raising hand") + `",
    "shortcodes": [
        ":woman_raising_hand:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧏",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("deaf") + `",
        "` + _t("deaf person") + `",
        "` + _t("ear") + `",
        "` + _t("hear") + `",
        "` + _t("hearing impaired") + `"
    ],
    "name": "` + _t("deaf person") + `",
    "shortcodes": [
        ":deaf_person:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧏‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("deaf") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("deaf man") + `",
    "shortcodes": [
        ":deaf_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧏‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("deaf") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("deaf woman") + `",
    "shortcodes": [
        ":deaf_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙇",
    "emoticons": [],
    "keywords": [
        "` + _t("apology") + `",
        "` + _t("bow") + `",
        "` + _t("gesture") + `",
        "` + _t("person bowing") + `",
        "` + _t("sorry") + `"
    ],
    "name": "` + _t("person bowing") + `",
    "shortcodes": [
        ":person_bowing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙇‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("apology") + `",
        "` + _t("bowing") + `",
        "` + _t("favor") + `",
        "` + _t("gesture") + `",
        "` + _t("man") + `",
        "` + _t("sorry") + `"
    ],
    "name": "` + _t("man bowing") + `",
    "shortcodes": [
        ":man_bowing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🙇‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("apology") + `",
        "` + _t("bowing") + `",
        "` + _t("favor") + `",
        "` + _t("gesture") + `",
        "` + _t("sorry") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman bowing") + `",
    "shortcodes": [
        ":woman_bowing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤦",
    "emoticons": [],
    "keywords": [
        "` + _t("disbelief") + `",
        "` + _t("exasperation") + `",
        "` + _t("face") + `",
        "` + _t("palm") + `",
        "` + _t("person facepalming") + `"
    ],
    "name": "` + _t("person facepalming") + `",
    "shortcodes": [
        ":person_facepalming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤦‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("disbelief") + `",
        "` + _t("exasperation") + `",
        "` + _t("facepalm") + `",
        "` + _t("man") + `",
        "` + _t("man facepalming") + `"
    ],
    "name": "` + _t("man facepalming") + `",
    "shortcodes": [
        ":man_facepalming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤦‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("disbelief") + `",
        "` + _t("exasperation") + `",
        "` + _t("facepalm") + `",
        "` + _t("woman") + `",
        "` + _t("woman facepalming") + `"
    ],
    "name": "` + _t("woman facepalming") + `",
    "shortcodes": [
        ":woman_facepalming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤷",
    "emoticons": [],
    "keywords": [
        "` + _t("doubt") + `",
        "` + _t("ignorance") + `",
        "` + _t("indifference") + `",
        "` + _t("person shrugging") + `",
        "` + _t("shrug") + `"
    ],
    "name": "` + _t("person shrugging") + `",
    "shortcodes": [
        ":person_shrugging:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤷‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("doubt") + `",
        "` + _t("ignorance") + `",
        "` + _t("indifference") + `",
        "` + _t("man") + `",
        "` + _t("man shrugging") + `",
        "` + _t("shrug") + `"
    ],
    "name": "` + _t("man shrugging") + `",
    "shortcodes": [
        ":man_shrugging:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤷‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("doubt") + `",
        "` + _t("ignorance") + `",
        "` + _t("indifference") + `",
        "` + _t("shrug") + `",
        "` + _t("woman") + `",
        "` + _t("woman shrugging") + `"
    ],
    "name": "` + _t("woman shrugging") + `",
    "shortcodes": [
        ":woman_shrugging:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍⚕️",
    "emoticons": [],
    "keywords": [
        "` + _t("doctor") + `",
        "` + _t("healthcare") + `",
        "` + _t("man") + `",
        "` + _t("man health worker") + `",
        "` + _t("nurse") + `",
        "` + _t("therapist") + `",
        "` + _t("health care") + `"
    ],
    "name": "` + _t("man health worker") + `",
    "shortcodes": [
        ":man_health_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍⚕️",
    "emoticons": [],
    "keywords": [
        "` + _t("doctor") + `",
        "` + _t("healthcare") + `",
        "` + _t("nurse") + `",
        "` + _t("therapist") + `",
        "` + _t("woman") + `",
        "` + _t("woman health worker") + `",
        "` + _t("health care") + `"
    ],
    "name": "` + _t("woman health worker") + `",
    "shortcodes": [
        ":woman_health_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🎓",
    "emoticons": [],
    "keywords": [
        "` + _t("graduate") + `",
        "` + _t("man") + `",
        "` + _t("student") + `"
    ],
    "name": "` + _t("man student") + `",
    "shortcodes": [
        ":man_student:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🎓",
    "emoticons": [],
    "keywords": [
        "` + _t("graduate") + `",
        "` + _t("student") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman student") + `",
    "shortcodes": [
        ":woman_student:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🏫",
    "emoticons": [],
    "keywords": [
        "` + _t("instructor") + `",
        "` + _t("man") + `",
        "` + _t("professor") + `",
        "` + _t("teacher") + `"
    ],
    "name": "` + _t("man teacher") + `",
    "shortcodes": [
        ":man_teacher:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🏫",
    "emoticons": [],
    "keywords": [
        "` + _t("instructor") + `",
        "` + _t("professor") + `",
        "` + _t("teacher") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman teacher") + `",
    "shortcodes": [
        ":woman_teacher:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍⚖️",
    "emoticons": [],
    "keywords": [
        "` + _t("judge") + `",
        "` + _t("justice") + `",
        "` + _t("man") + `",
        "` + _t("scales") + `"
    ],
    "name": "` + _t("man judge") + `",
    "shortcodes": [
        ":man_judge:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍⚖️",
    "emoticons": [],
    "keywords": [
        "` + _t("judge") + `",
        "` + _t("justice") + `",
        "` + _t("scales") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman judge") + `",
    "shortcodes": [
        ":woman_judge:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🌾",
    "emoticons": [],
    "keywords": [
        "` + _t("farmer") + `",
        "` + _t("gardener") + `",
        "` + _t("man") + `",
        "` + _t("rancher") + `"
    ],
    "name": "` + _t("man farmer") + `",
    "shortcodes": [
        ":man_farmer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🌾",
    "emoticons": [],
    "keywords": [
        "` + _t("farmer") + `",
        "` + _t("gardener") + `",
        "` + _t("rancher") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman farmer") + `",
    "shortcodes": [
        ":woman_farmer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🍳",
    "emoticons": [],
    "keywords": [
        "` + _t("chef") + `",
        "` + _t("cook") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("man cook") + `",
    "shortcodes": [
        ":man_cook:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🍳",
    "emoticons": [],
    "keywords": [
        "` + _t("chef") + `",
        "` + _t("cook") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman cook") + `",
    "shortcodes": [
        ":woman_cook:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🔧",
    "emoticons": [],
    "keywords": [
        "` + _t("electrician") + `",
        "` + _t("man") + `",
        "` + _t("mechanic") + `",
        "` + _t("plumber") + `",
        "` + _t("tradesperson") + `"
    ],
    "name": "` + _t("man mechanic") + `",
    "shortcodes": [
        ":man_mechanic:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🔧",
    "emoticons": [],
    "keywords": [
        "` + _t("electrician") + `",
        "` + _t("mechanic") + `",
        "` + _t("plumber") + `",
        "` + _t("tradesperson") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman mechanic") + `",
    "shortcodes": [
        ":woman_mechanic:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🏭",
    "emoticons": [],
    "keywords": [
        "` + _t("assembly") + `",
        "` + _t("factory") + `",
        "` + _t("industrial") + `",
        "` + _t("man") + `",
        "` + _t("worker") + `"
    ],
    "name": "` + _t("man factory worker") + `",
    "shortcodes": [
        ":man_factory_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🏭",
    "emoticons": [],
    "keywords": [
        "` + _t("assembly") + `",
        "` + _t("factory") + `",
        "` + _t("industrial") + `",
        "` + _t("woman") + `",
        "` + _t("worker") + `"
    ],
    "name": "` + _t("woman factory worker") + `",
    "shortcodes": [
        ":woman_factory_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍💼",
    "emoticons": [],
    "keywords": [
        "` + _t("business man") + `",
        "` + _t("man office worker") + `",
        "` + _t("manager") + `",
        "` + _t("office worker") + `",
        "` + _t("white collar") + `",
        "` + _t("architect") + `",
        "` + _t("business") + `",
        "` + _t("man") + `",
        "` + _t("white-collar") + `"
    ],
    "name": "` + _t("man office worker") + `",
    "shortcodes": [
        ":man_office_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍💼",
    "emoticons": [],
    "keywords": [
        "` + _t("business woman") + `",
        "` + _t("manager") + `",
        "` + _t("office worker") + `",
        "` + _t("white collar") + `",
        "` + _t("woman office worker") + `",
        "` + _t("architect") + `",
        "` + _t("business") + `",
        "` + _t("white-collar") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman office worker") + `",
    "shortcodes": [
        ":woman_office_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🔬",
    "emoticons": [],
    "keywords": [
        "` + _t("biologist") + `",
        "` + _t("chemist") + `",
        "` + _t("engineer") + `",
        "` + _t("man") + `",
        "` + _t("physicist") + `",
        "` + _t("scientist") + `"
    ],
    "name": "` + _t("man scientist") + `",
    "shortcodes": [
        ":man_scientist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🔬",
    "emoticons": [],
    "keywords": [
        "` + _t("biologist") + `",
        "` + _t("chemist") + `",
        "` + _t("engineer") + `",
        "` + _t("physicist") + `",
        "` + _t("scientist") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman scientist") + `",
    "shortcodes": [
        ":woman_scientist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍💻",
    "emoticons": [],
    "keywords": [
        "` + _t("coder") + `",
        "` + _t("developer") + `",
        "` + _t("inventor") + `",
        "` + _t("man") + `",
        "` + _t("software") + `",
        "` + _t("technologist") + `"
    ],
    "name": "` + _t("man technologist") + `",
    "shortcodes": [
        ":man_technologist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍💻",
    "emoticons": [],
    "keywords": [
        "` + _t("coder") + `",
        "` + _t("developer") + `",
        "` + _t("inventor") + `",
        "` + _t("software") + `",
        "` + _t("technologist") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman technologist") + `",
    "shortcodes": [
        ":woman_technologist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🎤",
    "emoticons": [],
    "keywords": [
        "` + _t("entertainer") + `",
        "` + _t("man") + `",
        "` + _t("man singer") + `",
        "` + _t("performer") + `",
        "` + _t("rock singer") + `",
        "` + _t("star") + `",
        "` + _t("actor") + `",
        "` + _t("rock") + `",
        "` + _t("singer") + `"
    ],
    "name": "` + _t("man singer") + `",
    "shortcodes": [
        ":man_singer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🎤",
    "emoticons": [],
    "keywords": [
        "` + _t("entertainer") + `",
        "` + _t("performer") + `",
        "` + _t("rock singer") + `",
        "` + _t("star") + `",
        "` + _t("woman") + `",
        "` + _t("woman singer") + `",
        "` + _t("actor") + `",
        "` + _t("rock") + `",
        "` + _t("singer") + `"
    ],
    "name": "` + _t("woman singer") + `",
    "shortcodes": [
        ":woman_singer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🎨",
    "emoticons": [],
    "keywords": [
        "` + _t("artist") + `",
        "` + _t("man") + `",
        "` + _t("painter") + `",
        "` + _t("palette") + `"
    ],
    "name": "` + _t("man artist") + `",
    "shortcodes": [
        ":man_artist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🎨",
    "emoticons": [],
    "keywords": [
        "` + _t("artist") + `",
        "` + _t("painter") + `",
        "` + _t("palette") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman artist") + `",
    "shortcodes": [
        ":woman_artist:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍✈️",
    "emoticons": [],
    "keywords": [
        "` + _t("man") + `",
        "` + _t("pilot") + `",
        "` + _t("plane") + `"
    ],
    "name": "` + _t("man pilot") + `",
    "shortcodes": [
        ":man_pilot:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍✈️",
    "emoticons": [],
    "keywords": [
        "` + _t("pilot") + `",
        "` + _t("plane") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman pilot") + `",
    "shortcodes": [
        ":woman_pilot:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🚀",
    "emoticons": [],
    "keywords": [
        "` + _t("astronaut") + `",
        "` + _t("man") + `",
        "` + _t("rocket") + `"
    ],
    "name": "` + _t("man astronaut") + `",
    "shortcodes": [
        ":man_astronaut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🚀",
    "emoticons": [],
    "keywords": [
        "` + _t("astronaut") + `",
        "` + _t("rocket") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman astronaut") + `",
    "shortcodes": [
        ":woman_astronaut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🚒",
    "emoticons": [],
    "keywords": [
        "` + _t("fire truck") + `",
        "` + _t("firefighter") + `",
        "` + _t("man") + `",
        "` + _t("firetruck") + `",
        "` + _t("fireman") + `"
    ],
    "name": "` + _t("man firefighter") + `",
    "shortcodes": [
        ":man_firefighter:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🚒",
    "emoticons": [],
    "keywords": [
        "` + _t("fire truck") + `",
        "` + _t("firefighter") + `",
        "` + _t("woman") + `",
        "` + _t("firetruck") + `",
        "` + _t("engine") + `",
        "` + _t("fire") + `",
        "` + _t("firewoman") + `",
        "` + _t("truck") + `"
    ],
    "name": "` + _t("woman firefighter") + `",
    "shortcodes": [
        ":woman_firefighter:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👮",
    "emoticons": [],
    "keywords": [
        "` + _t("cop") + `",
        "` + _t("officer") + `",
        "` + _t("police") + `"
    ],
    "name": "` + _t("police officer") + `",
    "shortcodes": [
        ":police_officer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👮‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("cop") + `",
        "` + _t("man") + `",
        "` + _t("officer") + `",
        "` + _t("police") + `"
    ],
    "name": "` + _t("man police officer") + `",
    "shortcodes": [
        ":man_police_officer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👮‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("cop") + `",
        "` + _t("officer") + `",
        "` + _t("police") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman police officer") + `",
    "shortcodes": [
        ":woman_police_officer:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕵️",
    "emoticons": [],
    "keywords": [
        "` + _t("detective") + `",
        "` + _t("investigator") + `",
        "` + _t("sleuth") + `",
        "` + _t("spy") + `"
    ],
    "name": "` + _t("detective") + `",
    "shortcodes": [
        ":detective:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕵️‍♂️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("man detective") + `",
    "shortcodes": [
        ":man_detective:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕵️‍♀️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("woman detective") + `",
    "shortcodes": [
        ":woman_detective:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💂",
    "emoticons": [],
    "keywords": [
        "` + _t("guard") + `"
    ],
    "name": "` + _t("guard") + `",
    "shortcodes": [
        ":guard:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💂‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("guard") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("man guard") + `",
    "shortcodes": [
        ":man_guard:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💂‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("guard") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman guard") + `",
    "shortcodes": [
        ":woman_guard:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👷",
    "emoticons": [],
    "keywords": [
        "` + _t("construction") + `",
        "` + _t("hat") + `",
        "` + _t("worker") + `"
    ],
    "name": "` + _t("construction worker") + `",
    "shortcodes": [
        ":construction_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👷‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("construction") + `",
        "` + _t("man") + `",
        "` + _t("worker") + `"
    ],
    "name": "` + _t("man construction worker") + `",
    "shortcodes": [
        ":man_construction_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👷‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("construction") + `",
        "` + _t("woman") + `",
        "` + _t("worker") + `"
    ],
    "name": "` + _t("woman construction worker") + `",
    "shortcodes": [
        ":woman_construction_worker:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤴",
    "emoticons": [],
    "keywords": [
        "` + _t("prince") + `"
    ],
    "name": "` + _t("prince") + `",
    "shortcodes": [
        ":prince:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👸",
    "emoticons": [],
    "keywords": [
        "` + _t("fairy tale") + `",
        "` + _t("fantasy") + `",
        "` + _t("princess") + `"
    ],
    "name": "` + _t("princess") + `",
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
        "` + _t("person wearing turban") + `",
        "` + _t("turban") + `"
    ],
    "name": "` + _t("person wearing turban") + `",
    "shortcodes": [
        ":person_wearing_turban:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👳‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man") + `",
        "` + _t("man wearing turban") + `",
        "` + _t("turban") + `"
    ],
    "name": "` + _t("man wearing turban") + `",
    "shortcodes": [
        ":man_wearing_turban:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👳‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("turban") + `",
        "` + _t("woman") + `",
        "` + _t("woman wearing turban") + `"
    ],
    "name": "` + _t("woman wearing turban") + `",
    "shortcodes": [
        ":woman_wearing_turban:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👲",
    "emoticons": [],
    "keywords": [
        "` + _t("cap") + `",
        "` + _t("gua pi mao") + `",
        "` + _t("hat") + `",
        "` + _t("person") + `",
        "` + _t("person with skullcap") + `",
        "` + _t("skullcap") + `"
    ],
    "name": "` + _t("person with skullcap") + `",
    "shortcodes": [
        ":person_with_skullcap:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧕",
    "emoticons": [],
    "keywords": [
        "` + _t("headscarf") + `",
        "` + _t("hijab") + `",
        "` + _t("mantilla") + `",
        "` + _t("tichel") + `",
        "` + _t("woman with headscarf") + `"
    ],
    "name": "` + _t("woman with headscarf") + `",
    "shortcodes": [
        ":woman_with_headscarf:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤵",
    "emoticons": [],
    "keywords": [
        "` + _t("groom") + `",
        "` + _t("person") + `",
        "` + _t("person in tux") + `",
        "` + _t("person in tuxedo") + `",
        "` + _t("tuxedo") + `"
    ],
    "name": "` + _t("person in tuxedo") + `",
    "shortcodes": [
        ":person_in_tuxedo:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👰",
    "emoticons": [],
    "keywords": [
        "` + _t("bride") + `",
        "` + _t("person") + `",
        "` + _t("person with veil") + `",
        "` + _t("veil") + `",
        "` + _t("wedding") + `"
    ],
    "name": "` + _t("person with veil") + `",
    "shortcodes": [
        ":person_with_veil:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤰",
    "emoticons": [],
    "keywords": [
        "` + _t("pregnant") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("pregnant woman") + `",
    "shortcodes": [
        ":pregnant_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤱",
    "emoticons": [],
    "keywords": [
        "` + _t("baby") + `",
        "` + _t("breast") + `",
        "` + _t("breast-feeding") + `",
        "` + _t("nursing") + `"
    ],
    "name": "` + _t("breast-feeding") + `",
    "shortcodes": [
        ":breast-feeding:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👼",
    "emoticons": [],
    "keywords": [
        "` + _t("angel") + `",
        "` + _t("baby") + `",
        "` + _t("face") + `",
        "` + _t("fairy tale") + `",
        "` + _t("fantasy") + `"
    ],
    "name": "` + _t("baby angel") + `",
    "shortcodes": [
        ":baby_angel:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🎅",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("Christmas") + `",
        "` + _t("Father Christmas") + `",
        "` + _t("Santa") + `",
        "` + _t("Santa Claus") + `",
        "` + _t("claus") + `",
        "` + _t("father") + `",
        "` + _t("santa") + `",
        "` + _t("Claus") + `",
        "` + _t("Father") + `"
    ],
    "name": "` + _t("Santa Claus") + `",
    "shortcodes": [
        ":Santa_Claus:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤶",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("Christmas") + `",
        "` + _t("Mrs Claus") + `",
        "` + _t("Mrs Santa Claus") + `",
        "` + _t("Mrs. Claus") + `",
        "` + _t("claus") + `",
        "` + _t("mother") + `",
        "` + _t("Mrs.") + `",
        "` + _t("Claus") + `",
        "` + _t("Mother") + `"
    ],
    "name": "` + _t("Mrs. Claus") + `",
    "shortcodes": [
        ":Mrs._Claus:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦸",
    "emoticons": [],
    "keywords": [
        "` + _t("good") + `",
        "` + _t("hero") + `",
        "` + _t("heroine") + `",
        "` + _t("superhero") + `",
        "` + _t("superpower") + `"
    ],
    "name": "` + _t("superhero") + `",
    "shortcodes": [
        ":superhero:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦸‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("good") + `",
        "` + _t("hero") + `",
        "` + _t("man") + `",
        "` + _t("man superhero") + `",
        "` + _t("superpower") + `"
    ],
    "name": "` + _t("man superhero") + `",
    "shortcodes": [
        ":man_superhero:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦸‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("good") + `",
        "` + _t("hero") + `",
        "` + _t("heroine") + `",
        "` + _t("superpower") + `",
        "` + _t("woman") + `",
        "` + _t("woman superhero") + `"
    ],
    "name": "` + _t("woman superhero") + `",
    "shortcodes": [
        ":woman_superhero:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦹",
    "emoticons": [],
    "keywords": [
        "` + _t("criminal") + `",
        "` + _t("evil") + `",
        "` + _t("superpower") + `",
        "` + _t("supervillain") + `",
        "` + _t("villain") + `"
    ],
    "name": "` + _t("supervillain") + `",
    "shortcodes": [
        ":supervillain:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦹‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("criminal") + `",
        "` + _t("evil") + `",
        "` + _t("man") + `",
        "` + _t("man supervillain") + `",
        "` + _t("superpower") + `",
        "` + _t("villain") + `"
    ],
    "name": "` + _t("man supervillain") + `",
    "shortcodes": [
        ":man_supervillain:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🦹‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("criminal") + `",
        "` + _t("evil") + `",
        "` + _t("superpower") + `",
        "` + _t("villain") + `",
        "` + _t("woman") + `",
        "` + _t("woman supervillain") + `"
    ],
    "name": "` + _t("woman supervillain") + `",
    "shortcodes": [
        ":woman_supervillain:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧙",
    "emoticons": [],
    "keywords": [
        "` + _t("mage") + `",
        "` + _t("sorcerer") + `",
        "` + _t("sorceress") + `",
        "` + _t("witch") + `",
        "` + _t("wizard") + `"
    ],
    "name": "` + _t("mage") + `",
    "shortcodes": [
        ":mage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧙‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man mage") + `",
        "` + _t("sorcerer") + `",
        "` + _t("wizard") + `"
    ],
    "name": "` + _t("man mage") + `",
    "shortcodes": [
        ":man_mage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧙‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("sorceress") + `",
        "` + _t("witch") + `",
        "` + _t("woman mage") + `"
    ],
    "name": "` + _t("woman mage") + `",
    "shortcodes": [
        ":woman_mage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧚",
    "emoticons": [],
    "keywords": [
        "` + _t("fairy") + `",
        "` + _t("Oberon") + `",
        "` + _t("Puck") + `",
        "` + _t("Titania") + `"
    ],
    "name": "` + _t("fairy") + `",
    "shortcodes": [
        ":fairy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧚‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man fairy") + `",
        "` + _t("Oberon") + `",
        "` + _t("Puck") + `"
    ],
    "name": "` + _t("man fairy") + `",
    "shortcodes": [
        ":man_fairy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧚‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("Titania") + `",
        "` + _t("woman fairy") + `"
    ],
    "name": "` + _t("woman fairy") + `",
    "shortcodes": [
        ":woman_fairy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧛",
    "emoticons": [],
    "keywords": [
        "` + _t("Dracula") + `",
        "` + _t("undead") + `",
        "` + _t("vampire") + `"
    ],
    "name": "` + _t("vampire") + `",
    "shortcodes": [
        ":vampire:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧛‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("Dracula") + `",
        "` + _t("man vampire") + `",
        "` + _t("undead") + `"
    ],
    "name": "` + _t("man vampire") + `",
    "shortcodes": [
        ":man_vampire:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧛‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("undead") + `",
        "` + _t("woman vampire") + `"
    ],
    "name": "` + _t("woman vampire") + `",
    "shortcodes": [
        ":woman_vampire:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧜",
    "emoticons": [],
    "keywords": [
        "` + _t("mermaid") + `",
        "` + _t("merman") + `",
        "` + _t("merperson") + `",
        "` + _t("merwoman") + `"
    ],
    "name": "` + _t("merperson") + `",
    "shortcodes": [
        ":merperson:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧜‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("merman") + `",
        "` + _t("Triton") + `"
    ],
    "name": "` + _t("merman") + `",
    "shortcodes": [
        ":merman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧜‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("mermaid") + `",
        "` + _t("merwoman") + `"
    ],
    "name": "` + _t("mermaid") + `",
    "shortcodes": [
        ":mermaid:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧝",
    "emoticons": [],
    "keywords": [
        "` + _t("elf") + `",
        "` + _t("magical") + `"
    ],
    "name": "` + _t("elf") + `",
    "shortcodes": [
        ":elf:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧝‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("magical") + `",
        "` + _t("man elf") + `"
    ],
    "name": "` + _t("man elf") + `",
    "shortcodes": [
        ":man_elf:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧝‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("magical") + `",
        "` + _t("woman elf") + `"
    ],
    "name": "` + _t("woman elf") + `",
    "shortcodes": [
        ":woman_elf:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧞",
    "emoticons": [],
    "keywords": [
        "` + _t("djinn") + `",
        "` + _t("genie") + `"
    ],
    "name": "` + _t("genie") + `",
    "shortcodes": [
        ":genie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧞‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("djinn") + `",
        "` + _t("man genie") + `"
    ],
    "name": "` + _t("man genie") + `",
    "shortcodes": [
        ":man_genie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧞‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("djinn") + `",
        "` + _t("woman genie") + `"
    ],
    "name": "` + _t("woman genie") + `",
    "shortcodes": [
        ":woman_genie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧟",
    "emoticons": [],
    "keywords": [
        "` + _t("undead") + `",
        "` + _t("walking dead") + `",
        "` + _t("zombie") + `"
    ],
    "name": "` + _t("zombie") + `",
    "shortcodes": [
        ":zombie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧟‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man zombie") + `",
        "` + _t("undead") + `",
        "` + _t("walking dead") + `"
    ],
    "name": "` + _t("man zombie") + `",
    "shortcodes": [
        ":man_zombie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧟‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("undead") + `",
        "` + _t("walking dead") + `",
        "` + _t("woman zombie") + `"
    ],
    "name": "` + _t("woman zombie") + `",
    "shortcodes": [
        ":woman_zombie:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💆",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("massage") + `",
        "` + _t("person getting massage") + `",
        "` + _t("salon") + `"
    ],
    "name": "` + _t("person getting massage") + `",
    "shortcodes": [
        ":person_getting_massage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💆‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("man") + `",
        "` + _t("man getting massage") + `",
        "` + _t("massage") + `"
    ],
    "name": "` + _t("man getting massage") + `",
    "shortcodes": [
        ":man_getting_massage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💆‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("massage") + `",
        "` + _t("woman") + `",
        "` + _t("woman getting massage") + `"
    ],
    "name": "` + _t("woman getting massage") + `",
    "shortcodes": [
        ":woman_getting_massage:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💇",
    "emoticons": [],
    "keywords": [
        "` + _t("barber") + `",
        "` + _t("beauty") + `",
        "` + _t("haircut") + `",
        "` + _t("parlor") + `",
        "` + _t("person getting haircut") + `",
        "` + _t("parlour") + `"
    ],
    "name": "` + _t("person getting haircut") + `",
    "shortcodes": [
        ":person_getting_haircut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💇‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("haircut") + `",
        "` + _t("hairdresser") + `",
        "` + _t("man") + `",
        "` + _t("man getting haircut") + `"
    ],
    "name": "` + _t("man getting haircut") + `",
    "shortcodes": [
        ":man_getting_haircut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💇‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("haircut") + `",
        "` + _t("hairdresser") + `",
        "` + _t("woman") + `",
        "` + _t("woman getting haircut") + `"
    ],
    "name": "` + _t("woman getting haircut") + `",
    "shortcodes": [
        ":woman_getting_haircut:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚶",
    "emoticons": [],
    "keywords": [
        "` + _t("hike") + `",
        "` + _t("person walking") + `",
        "` + _t("walk") + `",
        "` + _t("walking") + `"
    ],
    "name": "` + _t("person walking") + `",
    "shortcodes": [
        ":person_walking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚶‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("hike") + `",
        "` + _t("man") + `",
        "` + _t("man walking") + `",
        "` + _t("walk") + `"
    ],
    "name": "` + _t("man walking") + `",
    "shortcodes": [
        ":man_walking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚶‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("hike") + `",
        "` + _t("walk") + `",
        "` + _t("woman") + `",
        "` + _t("woman walking") + `"
    ],
    "name": "` + _t("woman walking") + `",
    "shortcodes": [
        ":woman_walking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧍",
    "emoticons": [],
    "keywords": [
        "` + _t("person standing") + `",
        "` + _t("stand") + `",
        "` + _t("standing") + `"
    ],
    "name": "` + _t("person standing") + `",
    "shortcodes": [
        ":person_standing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧍‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man") + `",
        "` + _t("standing") + `"
    ],
    "name": "` + _t("man standing") + `",
    "shortcodes": [
        ":man_standing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧍‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("standing") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman standing") + `",
    "shortcodes": [
        ":woman_standing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧎",
    "emoticons": [],
    "keywords": [
        "` + _t("kneel") + `",
        "` + _t("kneeling") + `",
        "` + _t("person kneeling") + `"
    ],
    "name": "` + _t("person kneeling") + `",
    "shortcodes": [
        ":person_kneeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧎‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("kneeling") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("man kneeling") + `",
    "shortcodes": [
        ":man_kneeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧎‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("kneeling") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman kneeling") + `",
    "shortcodes": [
        ":woman_kneeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦯",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("blind") + `",
        "` + _t("man") + `",
        "` + _t("man with white cane") + `",
        "` + _t("man with guide cane") + `"
    ],
    "name": "` + _t("man with white cane") + `",
    "shortcodes": [
        ":man_with_white_cane:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦯",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("blind") + `",
        "` + _t("woman") + `",
        "` + _t("woman with white cane") + `",
        "` + _t("woman with guide cane") + `"
    ],
    "name": "` + _t("woman with white cane") + `",
    "shortcodes": [
        ":woman_with_white_cane:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦼",
    "emoticons": [],
    "keywords": [
        "` + _t("man in motorised wheelchair") + `",
        "` + _t("accessibility") + `",
        "` + _t("man") + `",
        "` + _t("man in motorized wheelchair") + `",
        "` + _t("wheelchair") + `",
        "` + _t("man in powered wheelchair") + `"
    ],
    "name": "` + _t("man in motorized wheelchair") + `",
    "shortcodes": [
        ":man_in_motorized_wheelchair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦼",
    "emoticons": [],
    "keywords": [
        "` + _t("woman in motorised wheelchair") + `",
        "` + _t("accessibility") + `",
        "` + _t("wheelchair") + `",
        "` + _t("woman") + `",
        "` + _t("woman in motorized wheelchair") + `",
        "` + _t("woman in powered wheelchair") + `"
    ],
    "name": "` + _t("woman in motorized wheelchair") + `",
    "shortcodes": [
        ":woman_in_motorized_wheelchair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍🦽",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("man") + `",
        "` + _t("man in manual wheelchair") + `",
        "` + _t("wheelchair") + `"
    ],
    "name": "` + _t("man in manual wheelchair") + `",
    "shortcodes": [
        ":man_in_manual_wheelchair:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍🦽",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("wheelchair") + `",
        "` + _t("woman") + `",
        "` + _t("woman in manual wheelchair") + `"
    ],
    "name": "` + _t("woman in manual wheelchair") + `",
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
        "` + _t("marathon") + `",
        "` + _t("person running") + `",
        "` + _t("running") + `"
    ],
    "name": "` + _t("person running") + `",
    "shortcodes": [
        ":person_running:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏃‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man") + `",
        "` + _t("marathon") + `",
        "` + _t("racing") + `",
        "` + _t("running") + `"
    ],
    "name": "` + _t("man running") + `",
    "shortcodes": [
        ":man_running:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏃‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("marathon") + `",
        "` + _t("racing") + `",
        "` + _t("running") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman running") + `",
    "shortcodes": [
        ":woman_running:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💃",
    "emoticons": [],
    "keywords": [
        "` + _t("dance") + `",
        "` + _t("dancing") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman dancing") + `",
    "shortcodes": [
        ":woman_dancing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕺",
    "emoticons": [],
    "keywords": [
        "` + _t("dance") + `",
        "` + _t("dancing") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("man dancing") + `",
    "shortcodes": [
        ":man_dancing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🕴️",
    "emoticons": [],
    "keywords": [
        "` + _t("business") + `",
        "` + _t("person") + `",
        "` + _t("person in suit levitating") + `",
        "` + _t("suit") + `"
    ],
    "name": "` + _t("person in suit levitating") + `",
    "shortcodes": [
        ":person_in_suit_levitating:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👯",
    "emoticons": [],
    "keywords": [
        "` + _t("bunny ear") + `",
        "` + _t("dancer") + `",
        "` + _t("partying") + `",
        "` + _t("people with bunny ears") + `"
    ],
    "name": "` + _t("people with bunny ears") + `",
    "shortcodes": [
        ":people_with_bunny_ears:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👯‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("bunny ear") + `",
        "` + _t("dancer") + `",
        "` + _t("men") + `",
        "` + _t("men with bunny ears") + `",
        "` + _t("partying") + `"
    ],
    "name": "` + _t("men with bunny ears") + `",
    "shortcodes": [
        ":men_with_bunny_ears:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👯‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("bunny ear") + `",
        "` + _t("dancer") + `",
        "` + _t("partying") + `",
        "` + _t("women") + `",
        "` + _t("women with bunny ears") + `"
    ],
    "name": "` + _t("women with bunny ears") + `",
    "shortcodes": [
        ":women_with_bunny_ears:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧖",
    "emoticons": [],
    "keywords": [
        "` + _t("person in steamy room") + `",
        "` + _t("sauna") + `",
        "` + _t("steam room") + `"
    ],
    "name": "` + _t("person in steamy room") + `",
    "shortcodes": [
        ":person_in_steamy_room:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧖‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man in steam room") + `",
        "` + _t("man in steamy room") + `",
        "` + _t("sauna") + `",
        "` + _t("steam room") + `"
    ],
    "name": "` + _t("man in steamy room") + `",
    "shortcodes": [
        ":man_in_steamy_room:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧖‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("sauna") + `",
        "` + _t("steam room") + `",
        "` + _t("woman in steam room") + `",
        "` + _t("woman in steamy room") + `"
    ],
    "name": "` + _t("woman in steamy room") + `",
    "shortcodes": [
        ":woman_in_steamy_room:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧗",
    "emoticons": [],
    "keywords": [
        "` + _t("climber") + `",
        "` + _t("person climbing") + `"
    ],
    "name": "` + _t("person climbing") + `",
    "shortcodes": [
        ":person_climbing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧗‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("climber") + `",
        "` + _t("man climbing") + `"
    ],
    "name": "` + _t("man climbing") + `",
    "shortcodes": [
        ":man_climbing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧗‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("climber") + `",
        "` + _t("woman climbing") + `"
    ],
    "name": "` + _t("woman climbing") + `",
    "shortcodes": [
        ":woman_climbing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤺",
    "emoticons": [],
    "keywords": [
        "` + _t("fencer") + `",
        "` + _t("fencing") + `",
        "` + _t("person fencing") + `",
        "` + _t("sword") + `"
    ],
    "name": "` + _t("person fencing") + `",
    "shortcodes": [
        ":person_fencing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏇",
    "emoticons": [],
    "keywords": [
        "` + _t("horse") + `",
        "` + _t("jockey") + `",
        "` + _t("racehorse") + `",
        "` + _t("racing") + `"
    ],
    "name": "` + _t("horse racing") + `",
    "shortcodes": [
        ":horse_racing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "⛷️",
    "emoticons": [],
    "keywords": [
        "` + _t("ski") + `",
        "` + _t("skier") + `",
        "` + _t("snow") + `"
    ],
    "name": "` + _t("skier") + `",
    "shortcodes": [
        ":skier:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏂",
    "emoticons": [],
    "keywords": [
        "` + _t("ski") + `",
        "` + _t("snow") + `",
        "` + _t("snowboard") + `",
        "` + _t("snowboarder") + `"
    ],
    "name": "` + _t("snowboarder") + `",
    "shortcodes": [
        ":snowboarder:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏌️",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("golf") + `",
        "` + _t("golfer") + `",
        "` + _t("person golfing") + `"
    ],
    "name": "` + _t("person golfing") + `",
    "shortcodes": [
        ":person_golfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏌️‍♂️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("man golfing") + `",
    "shortcodes": [
        ":man_golfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏌️‍♀️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("woman golfing") + `",
    "shortcodes": [
        ":woman_golfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏄",
    "emoticons": [],
    "keywords": [
        "` + _t("person surfing") + `",
        "` + _t("surfer") + `",
        "` + _t("surfing") + `"
    ],
    "name": "` + _t("person surfing") + `",
    "shortcodes": [
        ":person_surfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏄‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man") + `",
        "` + _t("surfer") + `",
        "` + _t("surfing") + `"
    ],
    "name": "` + _t("man surfing") + `",
    "shortcodes": [
        ":man_surfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏄‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("surfer") + `",
        "` + _t("surfing") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman surfing") + `",
    "shortcodes": [
        ":woman_surfing:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚣",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("person") + `",
        "` + _t("person rowing boat") + `",
        "` + _t("rowboat") + `"
    ],
    "name": "` + _t("person rowing boat") + `",
    "shortcodes": [
        ":person_rowing_boat:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚣‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("man") + `",
        "` + _t("man rowing boat") + `",
        "` + _t("rowboat") + `"
    ],
    "name": "` + _t("man rowing boat") + `",
    "shortcodes": [
        ":man_rowing_boat:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚣‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("rowboat") + `",
        "` + _t("woman") + `",
        "` + _t("woman rowing boat") + `"
    ],
    "name": "` + _t("woman rowing boat") + `",
    "shortcodes": [
        ":woman_rowing_boat:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏊",
    "emoticons": [],
    "keywords": [
        "` + _t("person swimming") + `",
        "` + _t("swim") + `",
        "` + _t("swimmer") + `"
    ],
    "name": "` + _t("person swimming") + `",
    "shortcodes": [
        ":person_swimming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏊‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man") + `",
        "` + _t("man swimming") + `",
        "` + _t("swim") + `",
        "` + _t("swimmer") + `"
    ],
    "name": "` + _t("man swimming") + `",
    "shortcodes": [
        ":man_swimming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏊‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("swim") + `",
        "` + _t("swimmer") + `",
        "` + _t("woman") + `",
        "` + _t("woman swimming") + `"
    ],
    "name": "` + _t("woman swimming") + `",
    "shortcodes": [
        ":woman_swimming:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "⛹️",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("person bouncing ball") + `"
    ],
    "name": "` + _t("person bouncing ball") + `",
    "shortcodes": [
        ":person_bouncing_ball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "⛹️‍♂️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("man bouncing ball") + `",
    "shortcodes": [
        ":man_bouncing_ball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "⛹️‍♀️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("woman bouncing ball") + `",
    "shortcodes": [
        ":woman_bouncing_ball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏋️",
    "emoticons": [],
    "keywords": [
        "` + _t("lifter") + `",
        "` + _t("person lifting weights") + `",
        "` + _t("weight") + `",
        "` + _t("weightlifter") + `"
    ],
    "name": "` + _t("person lifting weights") + `",
    "shortcodes": [
        ":person_lifting_weights:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏋️‍♂️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("man lifting weights") + `",
    "shortcodes": [
        ":man_lifting_weights:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🏋️‍♀️",
    "emoticons": [],
    "keywords": [],
    "name": "` + _t("woman lifting weights") + `",
    "shortcodes": [
        ":woman_lifting_weights:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚴",
    "emoticons": [],
    "keywords": [
        "` + _t("bicycle") + `",
        "` + _t("biking") + `",
        "` + _t("cyclist") + `",
        "` + _t("person biking") + `",
        "` + _t("person riding a bike") + `"
    ],
    "name": "` + _t("person biking") + `",
    "shortcodes": [
        ":person_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚴‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("bicycle") + `",
        "` + _t("biking") + `",
        "` + _t("cyclist") + `",
        "` + _t("man") + `",
        "` + _t("man riding a bike") + `"
    ],
    "name": "` + _t("man biking") + `",
    "shortcodes": [
        ":man_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚴‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("bicycle") + `",
        "` + _t("biking") + `",
        "` + _t("cyclist") + `",
        "` + _t("woman") + `",
        "` + _t("woman riding a bike") + `"
    ],
    "name": "` + _t("woman biking") + `",
    "shortcodes": [
        ":woman_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚵",
    "emoticons": [],
    "keywords": [
        "` + _t("bicycle") + `",
        "` + _t("bicyclist") + `",
        "` + _t("bike") + `",
        "` + _t("cyclist") + `",
        "` + _t("mountain") + `",
        "` + _t("person mountain biking") + `"
    ],
    "name": "` + _t("person mountain biking") + `",
    "shortcodes": [
        ":person_mountain_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚵‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("bicycle") + `",
        "` + _t("bike") + `",
        "` + _t("cyclist") + `",
        "` + _t("man") + `",
        "` + _t("man mountain biking") + `",
        "` + _t("mountain") + `"
    ],
    "name": "` + _t("man mountain biking") + `",
    "shortcodes": [
        ":man_mountain_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🚵‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("bicycle") + `",
        "` + _t("bike") + `",
        "` + _t("biking") + `",
        "` + _t("cyclist") + `",
        "` + _t("mountain") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("woman mountain biking") + `",
    "shortcodes": [
        ":woman_mountain_biking:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤸",
    "emoticons": [],
    "keywords": [
        "` + _t("cartwheel") + `",
        "` + _t("gymnastics") + `",
        "` + _t("person cartwheeling") + `"
    ],
    "name": "` + _t("person cartwheeling") + `",
    "shortcodes": [
        ":person_cartwheeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤸‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("cartwheel") + `",
        "` + _t("gymnastics") + `",
        "` + _t("man") + `",
        "` + _t("man cartwheeling") + `"
    ],
    "name": "` + _t("man cartwheeling") + `",
    "shortcodes": [
        ":man_cartwheeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤸‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("cartwheel") + `",
        "` + _t("gymnastics") + `",
        "` + _t("woman") + `",
        "` + _t("woman cartwheeling") + `"
    ],
    "name": "` + _t("woman cartwheeling") + `",
    "shortcodes": [
        ":woman_cartwheeling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤼",
    "emoticons": [],
    "keywords": [
        "` + _t("people wrestling") + `",
        "` + _t("wrestle") + `",
        "` + _t("wrestler") + `"
    ],
    "name": "` + _t("people wrestling") + `",
    "shortcodes": [
        ":people_wrestling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤼‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("men") + `",
        "` + _t("men wrestling") + `",
        "` + _t("wrestle") + `"
    ],
    "name": "` + _t("men wrestling") + `",
    "shortcodes": [
        ":men_wrestling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤼‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("women") + `",
        "` + _t("women wrestling") + `",
        "` + _t("wrestle") + `"
    ],
    "name": "` + _t("women wrestling") + `",
    "shortcodes": [
        ":women_wrestling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤽",
    "emoticons": [],
    "keywords": [
        "` + _t("person playing water polo") + `",
        "` + _t("polo") + `",
        "` + _t("water") + `"
    ],
    "name": "` + _t("person playing water polo") + `",
    "shortcodes": [
        ":person_playing_water_polo:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤽‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man") + `",
        "` + _t("man playing water polo") + `",
        "` + _t("water polo") + `"
    ],
    "name": "` + _t("man playing water polo") + `",
    "shortcodes": [
        ":man_playing_water_polo:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤽‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("water polo") + `",
        "` + _t("woman") + `",
        "` + _t("woman playing water polo") + `"
    ],
    "name": "` + _t("woman playing water polo") + `",
    "shortcodes": [
        ":woman_playing_water_polo:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤾",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("handball") + `",
        "` + _t("person playing handball") + `"
    ],
    "name": "` + _t("person playing handball") + `",
    "shortcodes": [
        ":person_playing_handball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤾‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("handball") + `",
        "` + _t("man") + `",
        "` + _t("man playing handball") + `"
    ],
    "name": "` + _t("man playing handball") + `",
    "shortcodes": [
        ":man_playing_handball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤾‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("handball") + `",
        "` + _t("woman") + `",
        "` + _t("woman playing handball") + `"
    ],
    "name": "` + _t("woman playing handball") + `",
    "shortcodes": [
        ":woman_playing_handball:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤹",
    "emoticons": [],
    "keywords": [
        "` + _t("balance") + `",
        "` + _t("juggle") + `",
        "` + _t("multi-task") + `",
        "` + _t("person juggling") + `",
        "` + _t("skill") + `",
        "` + _t("multitask") + `"
    ],
    "name": "` + _t("person juggling") + `",
    "shortcodes": [
        ":person_juggling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤹‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("juggling") + `",
        "` + _t("man") + `",
        "` + _t("multi-task") + `",
        "` + _t("multitask") + `"
    ],
    "name": "` + _t("man juggling") + `",
    "shortcodes": [
        ":man_juggling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🤹‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("juggling") + `",
        "` + _t("multi-task") + `",
        "` + _t("woman") + `",
        "` + _t("multitask") + `"
    ],
    "name": "` + _t("woman juggling") + `",
    "shortcodes": [
        ":woman_juggling:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧘",
    "emoticons": [],
    "keywords": [
        "` + _t("meditation") + `",
        "` + _t("person in lotus position") + `",
        "` + _t("yoga") + `"
    ],
    "name": "` + _t("person in lotus position") + `",
    "shortcodes": [
        ":person_in_lotus_position:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧘‍♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("man in lotus position") + `",
        "` + _t("meditation") + `",
        "` + _t("yoga") + `"
    ],
    "name": "` + _t("man in lotus position") + `",
    "shortcodes": [
        ":man_in_lotus_position:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧘‍♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("meditation") + `",
        "` + _t("woman in lotus position") + `",
        "` + _t("yoga") + `"
    ],
    "name": "` + _t("woman in lotus position") + `",
    "shortcodes": [
        ":woman_in_lotus_position:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🛀",
    "emoticons": [],
    "keywords": [
        "` + _t("bath") + `",
        "` + _t("bathtub") + `",
        "` + _t("person taking bath") + `",
        "` + _t("tub") + `"
    ],
    "name": "` + _t("person taking bath") + `",
    "shortcodes": [
        ":person_taking_bath:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🛌",
    "emoticons": [],
    "keywords": [
        "` + _t("hotel") + `",
        "` + _t("person in bed") + `",
        "` + _t("sleep") + `",
        "` + _t("sleeping") + `",
        "` + _t("good night") + `"
    ],
    "name": "` + _t("person in bed") + `",
    "shortcodes": [
        ":person_in_bed:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🧑‍🤝‍🧑",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("hand") + `",
        "` + _t("hold") + `",
        "` + _t("holding hands") + `",
        "` + _t("people holding hands") + `",
        "` + _t("person") + `"
    ],
    "name": "` + _t("people holding hands") + `",
    "shortcodes": [
        ":people_holding_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👭",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("hand") + `",
        "` + _t("holding hands") + `",
        "` + _t("women") + `",
        "` + _t("women holding hands") + `",
        "` + _t("two women holding hands") + `"
    ],
    "name": "` + _t("women holding hands") + `",
    "shortcodes": [
        ":women_holding_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👫",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("hand") + `",
        "` + _t("hold") + `",
        "` + _t("holding hands") + `",
        "` + _t("man") + `",
        "` + _t("woman") + `",
        "` + _t("woman and man holding hands") + `",
        "` + _t("man and woman holding hands") + `"
    ],
    "name": "` + _t("woman and man holding hands") + `",
    "shortcodes": [
        ":woman_and_man_holding_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👬",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("Gemini") + `",
        "` + _t("holding hands") + `",
        "` + _t("man") + `",
        "` + _t("men") + `",
        "` + _t("men holding hands") + `",
        "` + _t("twins") + `",
        "` + _t("zodiac") + `",
        "` + _t("two men holding hands") + `"
    ],
    "name": "` + _t("men holding hands") + `",
    "shortcodes": [
        ":men_holding_hands:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💏",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("kiss") + `"
    ],
    "name": "` + _t("kiss") + `",
    "shortcodes": [
        ":kiss:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍❤️‍💋‍👨",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("kiss") + `",
        "` + _t("man") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("kiss: woman, man") + `",
    "shortcodes": [
        ":kiss:_woman,_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍❤️‍💋‍👨",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("kiss") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("kiss: man, man") + `",
    "shortcodes": [
        ":kiss:_man,_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍❤️‍💋‍👩",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("kiss") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("kiss: woman, woman") + `",
    "shortcodes": [
        ":kiss:_woman,_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "💑",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("couple with heart") + `",
        "` + _t("love") + `"
    ],
    "name": "` + _t("couple with heart") + `",
    "shortcodes": [
        ":couple_with_heart:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍❤️‍👨",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("couple with heart") + `",
        "` + _t("love") + `",
        "` + _t("man") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("couple with heart: woman, man") + `",
    "shortcodes": [
        ":couple_with_heart:_woman,_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍❤️‍👨",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("couple with heart") + `",
        "` + _t("love") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("couple with heart: man, man") + `",
    "shortcodes": [
        ":couple_with_heart:_man,_man:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍❤️‍👩",
    "emoticons": [],
    "keywords": [
        "` + _t("couple") + `",
        "` + _t("couple with heart") + `",
        "` + _t("love") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("couple with heart: woman, woman") + `",
    "shortcodes": [
        ":couple_with_heart:_woman,_woman:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👪",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `"
    ],
    "name": "` + _t("family") + `",
    "shortcodes": [
        ":family:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("man") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: man, woman, boy") + `",
    "shortcodes": [
        ":family:_man,_woman,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: man, woman, girl") + `",
    "shortcodes": [
        ":family:_man,_woman,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: man, woman, girl, boy") + `",
    "shortcodes": [
        ":family:_man,_woman,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("man") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: man, woman, boy, boy") + `",
    "shortcodes": [
        ":family:_man,_woman,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👩‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: man, woman, girl, girl") + `",
    "shortcodes": [
        ":family:_man,_woman,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, man, boy") + `",
    "shortcodes": [
        ":family:_man,_man,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, man, girl") + `",
    "shortcodes": [
        ":family:_man,_man,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, man, girl, boy") + `",
    "shortcodes": [
        ":family:_man,_man,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, man, boy, boy") + `",
    "shortcodes": [
        ":family:_man,_man,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👨‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, man, girl, girl") + `",
    "shortcodes": [
        ":family:_man,_man,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, woman, boy") + `",
    "shortcodes": [
        ":family:_woman,_woman,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, woman, girl") + `",
    "shortcodes": [
        ":family:_woman,_woman,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, woman, girl, boy") + `",
    "shortcodes": [
        ":family:_woman,_woman,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, woman, boy, boy") + `",
    "shortcodes": [
        ":family:_woman,_woman,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👩‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, woman, girl, girl") + `",
    "shortcodes": [
        ":family:_woman,_woman,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, boy") + `",
    "shortcodes": [
        ":family:_man,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, boy, boy") + `",
    "shortcodes": [
        ":family:_man,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, girl") + `",
    "shortcodes": [
        ":family:_man,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, girl, boy") + `",
    "shortcodes": [
        ":family:_man,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👨‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("family: man, girl, girl") + `",
    "shortcodes": [
        ":family:_man,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, boy") + `",
    "shortcodes": [
        ":family:_woman,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👦‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, boy, boy") + `",
    "shortcodes": [
        ":family:_woman,_boy,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, girl") + `",
    "shortcodes": [
        ":family:_woman,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👧‍👦",
    "emoticons": [],
    "keywords": [
        "` + _t("boy") + `",
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, girl, boy") + `",
    "shortcodes": [
        ":family:_woman,_girl,_boy:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👩‍👧‍👧",
    "emoticons": [],
    "keywords": [
        "` + _t("family") + `",
        "` + _t("girl") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("family: woman, girl, girl") + `",
    "shortcodes": [
        ":family:_woman,_girl,_girl:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "🗣️",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("head") + `",
        "` + _t("silhouette") + `",
        "` + _t("speak") + `",
        "` + _t("speaking") + `"
    ],
    "name": "` + _t("speaking head") + `",
    "shortcodes": [
        ":speaking_head:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👤",
    "emoticons": [],
    "keywords": [
        "` + _t("bust") + `",
        "` + _t("bust in silhouette") + `",
        "` + _t("silhouette") + `"
    ],
    "name": "` + _t("bust in silhouette") + `",
    "shortcodes": [
        ":bust_in_silhouette:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👥",
    "emoticons": [],
    "keywords": [
        "` + _t("bust") + `",
        "` + _t("busts in silhouette") + `",
        "` + _t("silhouette") + `"
    ],
    "name": "` + _t("busts in silhouette") + `",
    "shortcodes": [
        ":busts_in_silhouette:"
    ]
},
{
    "category": "People & Body",
    "codepoints": "👣",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("footprint") + `",
        "` + _t("footprints") + `",
        "` + _t("print") + `"
    ],
    "name": "` + _t("footprints") + `",
    "shortcodes": [
        ":footprints:"
    ]
},`;

const _getEmojisData3 = () => `{
    "category": "Animals & Nature",
    "codepoints": "🐵",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("monkey") + `"
    ],
    "name": "` + _t("monkey face") + `",
    "shortcodes": [
        ":monkey_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐒",
    "emoticons": [],
    "keywords": [
        "` + _t("monkey") + `"
    ],
    "name": "` + _t("monkey") + `",
    "shortcodes": [
        ":monkey:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦍",
    "emoticons": [],
    "keywords": [
        "` + _t("gorilla") + `"
    ],
    "name": "` + _t("gorilla") + `",
    "shortcodes": [
        ":gorilla:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦧",
    "emoticons": [],
    "keywords": [
        "` + _t("ape") + `",
        "` + _t("orangutan") + `"
    ],
    "name": "` + _t("orangutan") + `",
    "shortcodes": [
        ":orangutan:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐶",
    "emoticons": [],
    "keywords": [
        "` + _t("dog") + `",
        "` + _t("face") + `",
        "` + _t("pet") + `"
    ],
    "name": "` + _t("dog face") + `",
    "shortcodes": [
        ":dog_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐕",
    "emoticons": [],
    "keywords": [
        "` + _t("dog") + `",
        "` + _t("pet") + `"
    ],
    "name": "` + _t("dog") + `",
    "shortcodes": [
        ":dog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦮",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("blind") + `",
        "` + _t("guide") + `",
        "` + _t("guide dog") + `"
    ],
    "name": "` + _t("guide dog") + `",
    "shortcodes": [
        ":guide_dog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐕‍🦺",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("assistance") + `",
        "` + _t("dog") + `",
        "` + _t("service") + `"
    ],
    "name": "` + _t("service dog") + `",
    "shortcodes": [
        ":service_dog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐩",
    "emoticons": [],
    "keywords": [
        "` + _t("dog") + `",
        "` + _t("poodle") + `"
    ],
    "name": "` + _t("poodle") + `",
    "shortcodes": [
        ":poodle:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐺",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("wolf") + `"
    ],
    "name": "` + _t("wolf") + `",
    "shortcodes": [
        ":wolf:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦊",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("fox") + `"
    ],
    "name": "` + _t("fox") + `",
    "shortcodes": [
        ":fox:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦝",
    "emoticons": [],
    "keywords": [
        "` + _t("curious") + `",
        "` + _t("raccoon") + `",
        "` + _t("sly") + `"
    ],
    "name": "` + _t("raccoon") + `",
    "shortcodes": [
        ":raccoon:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐱",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("face") + `",
        "` + _t("pet") + `"
    ],
    "name": "` + _t("cat face") + `",
    "shortcodes": [
        ":cat_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐈",
    "emoticons": [],
    "keywords": [
        "` + _t("cat") + `",
        "` + _t("pet") + `"
    ],
    "name": "` + _t("cat") + `",
    "shortcodes": [
        ":cat:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦁",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("Leo") + `",
        "` + _t("lion") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("lion") + `",
    "shortcodes": [
        ":lion:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐯",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("tiger") + `"
    ],
    "name": "` + _t("tiger face") + `",
    "shortcodes": [
        ":tiger_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐅",
    "emoticons": [],
    "keywords": [
        "` + _t("tiger") + `"
    ],
    "name": "` + _t("tiger") + `",
    "shortcodes": [
        ":tiger:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐆",
    "emoticons": [],
    "keywords": [
        "` + _t("leopard") + `"
    ],
    "name": "` + _t("leopard") + `",
    "shortcodes": [
        ":leopard:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐴",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("horse") + `"
    ],
    "name": "` + _t("horse face") + `",
    "shortcodes": [
        ":horse_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐎",
    "emoticons": [],
    "keywords": [
        "` + _t("equestrian") + `",
        "` + _t("horse") + `",
        "` + _t("racehorse") + `",
        "` + _t("racing") + `"
    ],
    "name": "` + _t("horse") + `",
    "shortcodes": [
        ":horse:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦄",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("unicorn") + `"
    ],
    "name": "` + _t("unicorn") + `",
    "shortcodes": [
        ":unicorn:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦓",
    "emoticons": [],
    "keywords": [
        "` + _t("stripe") + `",
        "` + _t("zebra") + `"
    ],
    "name": "` + _t("zebra") + `",
    "shortcodes": [
        ":zebra:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦌",
    "emoticons": [],
    "keywords": [
        "` + _t("deer") + `",
        "` + _t("stag") + `"
    ],
    "name": "` + _t("deer") + `",
    "shortcodes": [
        ":deer:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐮",
    "emoticons": [],
    "keywords": [
        "` + _t("cow") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("cow face") + `",
    "shortcodes": [
        ":cow_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐂",
    "emoticons": [],
    "keywords": [
        "` + _t("bull") + `",
        "` + _t("ox") + `",
        "` + _t("Taurus") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("ox") + `",
    "shortcodes": [
        ":ox:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐃",
    "emoticons": [],
    "keywords": [
        "` + _t("buffalo") + `",
        "` + _t("water") + `"
    ],
    "name": "` + _t("water buffalo") + `",
    "shortcodes": [
        ":water_buffalo:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐄",
    "emoticons": [],
    "keywords": [
        "` + _t("cow") + `"
    ],
    "name": "` + _t("cow") + `",
    "shortcodes": [
        ":cow:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐷",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("pig") + `"
    ],
    "name": "` + _t("pig face") + `",
    "shortcodes": [
        ":pig_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐖",
    "emoticons": [],
    "keywords": [
        "` + _t("pig") + `",
        "` + _t("sow") + `"
    ],
    "name": "` + _t("pig") + `",
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
        "` + _t("boar") + `",
        "` + _t("pig") + `"
    ],
    "name": "` + _t("boar") + `",
    "shortcodes": [
        ":boar:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐽",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("nose") + `",
        "` + _t("pig") + `"
    ],
    "name": "` + _t("pig nose") + `",
    "shortcodes": [
        ":pig_nose:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐏",
    "emoticons": [],
    "keywords": [
        "` + _t("Aries") + `",
        "` + _t("male") + `",
        "` + _t("ram") + `",
        "` + _t("sheep") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("ram") + `",
    "shortcodes": [
        ":ram:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐑",
    "emoticons": [],
    "keywords": [
        "` + _t("ewe") + `",
        "` + _t("female") + `",
        "` + _t("sheep") + `"
    ],
    "name": "` + _t("ewe") + `",
    "shortcodes": [
        ":ewe:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐐",
    "emoticons": [],
    "keywords": [
        "` + _t("Capricorn") + `",
        "` + _t("goat") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("goat") + `",
    "shortcodes": [
        ":goat:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐪",
    "emoticons": [],
    "keywords": [
        "` + _t("camel") + `",
        "` + _t("dromedary") + `",
        "` + _t("hump") + `"
    ],
    "name": "` + _t("camel") + `",
    "shortcodes": [
        ":camel:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐫",
    "emoticons": [],
    "keywords": [
        "` + _t("bactrian") + `",
        "` + _t("camel") + `",
        "` + _t("hump") + `",
        "` + _t("two-hump camel") + `",
        "` + _t("Bactrian") + `"
    ],
    "name": "` + _t("two-hump camel") + `",
    "shortcodes": [
        ":two-hump_camel:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦙",
    "emoticons": [],
    "keywords": [
        "` + _t("alpaca") + `",
        "` + _t("guanaco") + `",
        "` + _t("llama") + `",
        "` + _t("vicuña") + `",
        "` + _t("wool") + `"
    ],
    "name": "` + _t("llama") + `",
    "shortcodes": [
        ":llama:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦒",
    "emoticons": [],
    "keywords": [
        "` + _t("giraffe") + `",
        "` + _t("spots") + `"
    ],
    "name": "` + _t("giraffe") + `",
    "shortcodes": [
        ":giraffe:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐘",
    "emoticons": [],
    "keywords": [
        "` + _t("elephant") + `"
    ],
    "name": "` + _t("elephant") + `",
    "shortcodes": [
        ":elephant:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦏",
    "emoticons": [],
    "keywords": [
        "` + _t("rhino") + `",
        "` + _t("rhinoceros") + `"
    ],
    "name": "` + _t("rhinoceros") + `",
    "shortcodes": [
        ":rhinoceros:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦛",
    "emoticons": [],
    "keywords": [
        "` + _t("hippo") + `",
        "` + _t("hippopotamus") + `"
    ],
    "name": "` + _t("hippopotamus") + `",
    "shortcodes": [
        ":hippopotamus:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐭",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("mouse") + `",
        "` + _t("pet") + `"
    ],
    "name": "` + _t("mouse face") + `",
    "shortcodes": [
        ":mouse_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐁",
    "emoticons": [],
    "keywords": [
        "` + _t("mouse") + `",
        "` + _t("pet") + `",
        "` + _t("rodent") + `"
    ],
    "name": "` + _t("mouse") + `",
    "shortcodes": [
        ":mouse:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐀",
    "emoticons": [],
    "keywords": [
        "` + _t("pet") + `",
        "` + _t("rat") + `",
        "` + _t("rodent") + `"
    ],
    "name": "` + _t("rat") + `",
    "shortcodes": [
        ":rat:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐹",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("hamster") + `",
        "` + _t("pet") + `"
    ],
    "name": "` + _t("hamster") + `",
    "shortcodes": [
        ":hamster:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐰",
    "emoticons": [],
    "keywords": [
        "` + _t("bunny") + `",
        "` + _t("face") + `",
        "` + _t("pet") + `",
        "` + _t("rabbit") + `"
    ],
    "name": "` + _t("rabbit face") + `",
    "shortcodes": [
        ":rabbit_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐇",
    "emoticons": [],
    "keywords": [
        "` + _t("bunny") + `",
        "` + _t("pet") + `",
        "` + _t("rabbit") + `"
    ],
    "name": "` + _t("rabbit") + `",
    "shortcodes": [
        ":rabbit:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐿️",
    "emoticons": [],
    "keywords": [
        "` + _t("chipmunk") + `",
        "` + _t("squirrel") + `"
    ],
    "name": "` + _t("chipmunk") + `",
    "shortcodes": [
        ":chipmunk:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦔",
    "emoticons": [],
    "keywords": [
        "` + _t("hedgehog") + `",
        "` + _t("spiny") + `"
    ],
    "name": "` + _t("hedgehog") + `",
    "shortcodes": [
        ":hedgehog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦇",
    "emoticons": [],
    "keywords": [
        "` + _t("bat") + `",
        "` + _t("vampire") + `"
    ],
    "name": "` + _t("bat") + `",
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
        "` + _t("bear") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("bear") + `",
    "shortcodes": [
        ":bear:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐨",
    "emoticons": [],
    "keywords": [
        "` + _t("koala") + `",
        "` + _t("marsupial") + `",
        "` + _t("face") + `"
    ],
    "name": "` + _t("koala") + `",
    "shortcodes": [
        ":koala:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐼",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("panda") + `"
    ],
    "name": "` + _t("panda") + `",
    "shortcodes": [
        ":panda:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦥",
    "emoticons": [],
    "keywords": [
        "` + _t("lazy") + `",
        "` + _t("sloth") + `",
        "` + _t("slow") + `"
    ],
    "name": "` + _t("sloth") + `",
    "shortcodes": [
        ":sloth:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦦",
    "emoticons": [],
    "keywords": [
        "` + _t("fishing") + `",
        "` + _t("otter") + `",
        "` + _t("playful") + `"
    ],
    "name": "` + _t("otter") + `",
    "shortcodes": [
        ":otter:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦨",
    "emoticons": [],
    "keywords": [
        "` + _t("skunk") + `",
        "` + _t("stink") + `"
    ],
    "name": "` + _t("skunk") + `",
    "shortcodes": [
        ":skunk:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦘",
    "emoticons": [],
    "keywords": [
        "` + _t("Australia") + `",
        "` + _t("joey") + `",
        "` + _t("jump") + `",
        "` + _t("kangaroo") + `",
        "` + _t("marsupial") + `"
    ],
    "name": "` + _t("kangaroo") + `",
    "shortcodes": [
        ":kangaroo:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦡",
    "emoticons": [],
    "keywords": [
        "` + _t("badger") + `",
        "` + _t("honey badger") + `",
        "` + _t("pester") + `"
    ],
    "name": "` + _t("badger") + `",
    "shortcodes": [
        ":badger:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐾",
    "emoticons": [],
    "keywords": [
        "` + _t("feet") + `",
        "` + _t("paw") + `",
        "` + _t("paw prints") + `",
        "` + _t("print") + `"
    ],
    "name": "` + _t("paw prints") + `",
    "shortcodes": [
        ":paw_prints:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦃",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("poultry") + `",
        "` + _t("turkey") + `"
    ],
    "name": "` + _t("turkey") + `",
    "shortcodes": [
        ":turkey:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐔",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("chicken") + `",
        "` + _t("poultry") + `"
    ],
    "name": "` + _t("chicken") + `",
    "shortcodes": [
        ":chicken:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐓",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("rooster") + `"
    ],
    "name": "` + _t("rooster") + `",
    "shortcodes": [
        ":rooster:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐣",
    "emoticons": [],
    "keywords": [
        "` + _t("baby") + `",
        "` + _t("bird") + `",
        "` + _t("chick") + `",
        "` + _t("hatching") + `"
    ],
    "name": "` + _t("hatching chick") + `",
    "shortcodes": [
        ":hatching_chick:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐤",
    "emoticons": [],
    "keywords": [
        "` + _t("baby") + `",
        "` + _t("bird") + `",
        "` + _t("chick") + `"
    ],
    "name": "` + _t("baby chick") + `",
    "shortcodes": [
        ":baby_chick:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐥",
    "emoticons": [],
    "keywords": [
        "` + _t("baby") + `",
        "` + _t("bird") + `",
        "` + _t("chick") + `",
        "` + _t("front-facing baby chick") + `"
    ],
    "name": "` + _t("front-facing baby chick") + `",
    "shortcodes": [
        ":front-facing_baby_chick:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐦",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `"
    ],
    "name": "` + _t("bird") + `",
    "shortcodes": [
        ":bird:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐧",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("penguin") + `"
    ],
    "name": "` + _t("penguin") + `",
    "shortcodes": [
        ":penguin:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🕊️",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("dove") + `",
        "` + _t("fly") + `",
        "` + _t("peace") + `"
    ],
    "name": "` + _t("dove") + `",
    "shortcodes": [
        ":dove:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦅",
    "emoticons": [],
    "keywords": [
        "` + _t("bird of prey") + `",
        "` + _t("eagle") + `",
        "` + _t("bird") + `"
    ],
    "name": "` + _t("eagle") + `",
    "shortcodes": [
        ":eagle:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦆",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("duck") + `"
    ],
    "name": "` + _t("duck") + `",
    "shortcodes": [
        ":duck:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦢",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("cygnet") + `",
        "` + _t("swan") + `",
        "` + _t("ugly duckling") + `"
    ],
    "name": "` + _t("swan") + `",
    "shortcodes": [
        ":swan:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦉",
    "emoticons": [],
    "keywords": [
        "` + _t("bird of prey") + `",
        "` + _t("owl") + `",
        "` + _t("wise") + `",
        "` + _t("bird") + `"
    ],
    "name": "` + _t("owl") + `",
    "shortcodes": [
        ":owl:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦩",
    "emoticons": [],
    "keywords": [
        "` + _t("flamboyant") + `",
        "` + _t("flamingo") + `",
        "` + _t("tropical") + `"
    ],
    "name": "` + _t("flamingo") + `",
    "shortcodes": [
        ":flamingo:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦚",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("ostentatious") + `",
        "` + _t("peacock") + `",
        "` + _t("peahen") + `",
        "` + _t("proud") + `"
    ],
    "name": "` + _t("peacock") + `",
    "shortcodes": [
        ":peacock:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦜",
    "emoticons": [],
    "keywords": [
        "` + _t("bird") + `",
        "` + _t("parrot") + `",
        "` + _t("pirate") + `",
        "` + _t("talk") + `"
    ],
    "name": "` + _t("parrot") + `",
    "shortcodes": [
        ":parrot:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐸",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("frog") + `"
    ],
    "name": "` + _t("frog") + `",
    "shortcodes": [
        ":frog:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐊",
    "emoticons": [],
    "keywords": [
        "` + _t("crocodile") + `"
    ],
    "name": "` + _t("crocodile") + `",
    "shortcodes": [
        ":crocodile:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐢",
    "emoticons": [],
    "keywords": [
        "` + _t("terrapin") + `",
        "` + _t("tortoise") + `",
        "` + _t("turtle") + `"
    ],
    "name": "` + _t("turtle") + `",
    "shortcodes": [
        ":turtle:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦎",
    "emoticons": [],
    "keywords": [
        "` + _t("lizard") + `",
        "` + _t("reptile") + `"
    ],
    "name": "` + _t("lizard") + `",
    "shortcodes": [
        ":lizard:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐍",
    "emoticons": [],
    "keywords": [
        "` + _t("bearer") + `",
        "` + _t("Ophiuchus") + `",
        "` + _t("serpent") + `",
        "` + _t("snake") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("snake") + `",
    "shortcodes": [
        ":snake:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐲",
    "emoticons": [],
    "keywords": [
        "` + _t("dragon") + `",
        "` + _t("face") + `",
        "` + _t("fairy tale") + `"
    ],
    "name": "` + _t("dragon face") + `",
    "shortcodes": [
        ":dragon_face:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐉",
    "emoticons": [],
    "keywords": [
        "` + _t("dragon") + `",
        "` + _t("fairy tale") + `"
    ],
    "name": "` + _t("dragon") + `",
    "shortcodes": [
        ":dragon:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦕",
    "emoticons": [],
    "keywords": [
        "` + _t("brachiosaurus") + `",
        "` + _t("brontosaurus") + `",
        "` + _t("diplodocus") + `",
        "` + _t("sauropod") + `"
    ],
    "name": "` + _t("sauropod") + `",
    "shortcodes": [
        ":sauropod:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦖",
    "emoticons": [],
    "keywords": [
        "` + _t("T-Rex") + `",
        "` + _t("Tyrannosaurus Rex") + `"
    ],
    "name": "` + _t("T-Rex") + `",
    "shortcodes": [
        ":T-Rex:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐳",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("spouting") + `",
        "` + _t("whale") + `"
    ],
    "name": "` + _t("spouting whale") + `",
    "shortcodes": [
        ":spouting_whale:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐋",
    "emoticons": [],
    "keywords": [
        "` + _t("whale") + `"
    ],
    "name": "` + _t("whale") + `",
    "shortcodes": [
        ":whale:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐬",
    "emoticons": [],
    "keywords": [
        "` + _t("dolphin") + `",
        "` + _t("porpoise") + `",
        "` + _t("flipper") + `"
    ],
    "name": "` + _t("dolphin") + `",
    "shortcodes": [
        ":dolphin:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐟",
    "emoticons": [],
    "keywords": [
        "` + _t("fish") + `",
        "` + _t("Pisces") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("fish") + `",
    "shortcodes": [
        ":fish:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐠",
    "emoticons": [],
    "keywords": [
        "` + _t("fish") + `",
        "` + _t("reef fish") + `",
        "` + _t("tropical") + `"
    ],
    "name": "` + _t("tropical fish") + `",
    "shortcodes": [
        ":tropical_fish:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐡",
    "emoticons": [],
    "keywords": [
        "` + _t("blowfish") + `",
        "` + _t("fish") + `"
    ],
    "name": "` + _t("blowfish") + `",
    "shortcodes": [
        ":blowfish:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦈",
    "emoticons": [],
    "keywords": [
        "` + _t("fish") + `",
        "` + _t("shark") + `"
    ],
    "name": "` + _t("shark") + `",
    "shortcodes": [
        ":shark:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐙",
    "emoticons": [],
    "keywords": [
        "` + _t("octopus") + `"
    ],
    "name": "` + _t("octopus") + `",
    "shortcodes": [
        ":octopus:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐚",
    "emoticons": [],
    "keywords": [
        "` + _t("shell") + `",
        "` + _t("spiral") + `"
    ],
    "name": "` + _t("spiral shell") + `",
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
        "` + _t("mollusc") + `",
        "` + _t("snail") + `"
    ],
    "name": "` + _t("snail") + `",
    "shortcodes": [
        ":snail:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦋",
    "emoticons": [],
    "keywords": [
        "` + _t("butterfly") + `",
        "` + _t("insect") + `",
        "` + _t("moth") + `",
        "` + _t("pretty") + `"
    ],
    "name": "` + _t("butterfly") + `",
    "shortcodes": [
        ":butterfly:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐛",
    "emoticons": [],
    "keywords": [
        "` + _t("bug") + `",
        "` + _t("caterpillar") + `",
        "` + _t("insect") + `",
        "` + _t("worm") + `"
    ],
    "name": "` + _t("bug") + `",
    "shortcodes": [
        ":bug:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐜",
    "emoticons": [],
    "keywords": [
        "` + _t("ant") + `",
        "` + _t("insect") + `"
    ],
    "name": "` + _t("ant") + `",
    "shortcodes": [
        ":ant:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🐝",
    "emoticons": [],
    "keywords": [
        "` + _t("bee") + `",
        "` + _t("honeybee") + `",
        "` + _t("insect") + `"
    ],
    "name": "` + _t("honeybee") + `",
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
        "` + _t("beetle") + `",
        "` + _t("insect") + `",
        "` + _t("lady beetle") + `",
        "` + _t("ladybird") + `",
        "` + _t("ladybug") + `"
    ],
    "name": "` + _t("lady beetle") + `",
    "shortcodes": [
        ":lady_beetle:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦗",
    "emoticons": [],
    "keywords": [
        "` + _t("cricket") + `",
        "` + _t("grasshopper") + `"
    ],
    "name": "` + _t("cricket") + `",
    "shortcodes": [
        ":cricket:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🕷️",
    "emoticons": [],
    "keywords": [
        "` + _t("arachnid") + `",
        "` + _t("spider") + `",
        "` + _t("insect") + `"
    ],
    "name": "` + _t("spider") + `",
    "shortcodes": [
        ":spider:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🕸️",
    "emoticons": [],
    "keywords": [
        "` + _t("spider") + `",
        "` + _t("web") + `"
    ],
    "name": "` + _t("spider web") + `",
    "shortcodes": [
        ":spider_web:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦂",
    "emoticons": [],
    "keywords": [
        "` + _t("scorpio") + `",
        "` + _t("Scorpio") + `",
        "` + _t("scorpion") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("scorpion") + `",
    "shortcodes": [
        ":scorpion:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦟",
    "emoticons": [],
    "keywords": [
        "` + _t("dengue") + `",
        "` + _t("fever") + `",
        "` + _t("insect") + `",
        "` + _t("malaria") + `",
        "` + _t("mosquito") + `",
        "` + _t("mozzie") + `",
        "` + _t("virus") + `",
        "` + _t("disease") + `",
        "` + _t("pest") + `"
    ],
    "name": "` + _t("mosquito") + `",
    "shortcodes": [
        ":mosquito:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🦠",
    "emoticons": [],
    "keywords": [
        "` + _t("amoeba") + `",
        "` + _t("bacteria") + `",
        "` + _t("microbe") + `",
        "` + _t("virus") + `"
    ],
    "name": "` + _t("microbe") + `",
    "shortcodes": [
        ":microbe:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "💐",
    "emoticons": [],
    "keywords": [
        "` + _t("bouquet") + `",
        "` + _t("flower") + `"
    ],
    "name": "` + _t("bouquet") + `",
    "shortcodes": [
        ":bouquet:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌸",
    "emoticons": [],
    "keywords": [
        "` + _t("blossom") + `",
        "` + _t("cherry") + `",
        "` + _t("flower") + `"
    ],
    "name": "` + _t("cherry blossom") + `",
    "shortcodes": [
        ":cherry_blossom:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "💮",
    "emoticons": [],
    "keywords": [
        "` + _t("flower") + `",
        "` + _t("white flower") + `"
    ],
    "name": "` + _t("white flower") + `",
    "shortcodes": [
        ":white_flower:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🏵️",
    "emoticons": [],
    "keywords": [
        "` + _t("plant") + `",
        "` + _t("rosette") + `"
    ],
    "name": "` + _t("rosette") + `",
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
        "` + _t("flower") + `",
        "` + _t("rose") + `"
    ],
    "name": "` + _t("rose") + `",
    "shortcodes": [
        ":rose:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🥀",
    "emoticons": [],
    "keywords": [
        "` + _t("flower") + `",
        "` + _t("wilted") + `"
    ],
    "name": "` + _t("wilted flower") + `",
    "shortcodes": [
        ":wilted_flower:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌺",
    "emoticons": [],
    "keywords": [
        "` + _t("flower") + `",
        "` + _t("hibiscus") + `"
    ],
    "name": "` + _t("hibiscus") + `",
    "shortcodes": [
        ":hibiscus:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌻",
    "emoticons": [],
    "keywords": [
        "` + _t("flower") + `",
        "` + _t("sun") + `",
        "` + _t("sunflower") + `"
    ],
    "name": "` + _t("sunflower") + `",
    "shortcodes": [
        ":sunflower:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌼",
    "emoticons": [],
    "keywords": [
        "` + _t("blossom") + `",
        "` + _t("flower") + `"
    ],
    "name": "` + _t("blossom") + `",
    "shortcodes": [
        ":blossom:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌷",
    "emoticons": [],
    "keywords": [
        "` + _t("flower") + `",
        "` + _t("tulip") + `"
    ],
    "name": "` + _t("tulip") + `",
    "shortcodes": [
        ":tulip:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌱",
    "emoticons": [],
    "keywords": [
        "` + _t("seedling") + `",
        "` + _t("young") + `"
    ],
    "name": "` + _t("seedling") + `",
    "shortcodes": [
        ":seedling:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌲",
    "emoticons": [],
    "keywords": [
        "` + _t("evergreen tree") + `",
        "` + _t("tree") + `"
    ],
    "name": "` + _t("evergreen tree") + `",
    "shortcodes": [
        ":evergreen_tree:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌳",
    "emoticons": [],
    "keywords": [
        "` + _t("deciduous") + `",
        "` + _t("shedding") + `",
        "` + _t("tree") + `"
    ],
    "name": "` + _t("deciduous tree") + `",
    "shortcodes": [
        ":deciduous_tree:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌴",
    "emoticons": [],
    "keywords": [
        "` + _t("palm") + `",
        "` + _t("tree") + `"
    ],
    "name": "` + _t("palm tree") + `",
    "shortcodes": [
        ":palm_tree:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌵",
    "emoticons": [],
    "keywords": [
        "` + _t("cactus") + `",
        "` + _t("plant") + `"
    ],
    "name": "` + _t("cactus") + `",
    "shortcodes": [
        ":cactus:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌾",
    "emoticons": [],
    "keywords": [
        "` + _t("ear") + `",
        "` + _t("grain") + `",
        "` + _t("rice") + `",
        "` + _t("sheaf of rice") + `",
        "` + _t("sheaf") + `"
    ],
    "name": "` + _t("sheaf of rice") + `",
    "shortcodes": [
        ":sheaf_of_rice:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🌿",
    "emoticons": [],
    "keywords": [
        "` + _t("herb") + `",
        "` + _t("leaf") + `"
    ],
    "name": "` + _t("herb") + `",
    "shortcodes": [
        ":herb:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "☘️",
    "emoticons": [],
    "keywords": [
        "` + _t("plant") + `",
        "` + _t("shamrock") + `"
    ],
    "name": "` + _t("shamrock") + `",
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
        "` + _t("4") + `",
        "` + _t("clover") + `",
        "` + _t("four") + `",
        "` + _t("four-leaf clover") + `",
        "` + _t("leaf") + `"
    ],
    "name": "` + _t("four leaf clover") + `",
    "shortcodes": [
        ":four_leaf_clover:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🍁",
    "emoticons": [],
    "keywords": [
        "` + _t("falling") + `",
        "` + _t("leaf") + `",
        "` + _t("maple") + `"
    ],
    "name": "` + _t("maple leaf") + `",
    "shortcodes": [
        ":maple_leaf:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🍂",
    "emoticons": [],
    "keywords": [
        "` + _t("fallen leaf") + `",
        "` + _t("falling") + `",
        "` + _t("leaf") + `"
    ],
    "name": "` + _t("fallen leaf") + `",
    "shortcodes": [
        ":fallen_leaf:"
    ]
},
{
    "category": "Animals & Nature",
    "codepoints": "🍃",
    "emoticons": [],
    "keywords": [
        "` + _t("blow") + `",
        "` + _t("flutter") + `",
        "` + _t("leaf") + `",
        "` + _t("leaf fluttering in wind") + `",
        "` + _t("wind") + `"
    ],
    "name": "` + _t("leaf fluttering in wind") + `",
    "shortcodes": [
        ":leaf_fluttering_in_wind:"
    ]
},`;

const _getEmojisData4 = () => `{
    "category": "Food & Drink",
    "codepoints": "🍇",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("grape") + `",
        "` + _t("grapes") + `"
    ],
    "name": "` + _t("grapes") + `",
    "shortcodes": [
        ":grapes:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍈",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("melon") + `"
    ],
    "name": "` + _t("melon") + `",
    "shortcodes": [
        ":melon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍉",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("watermelon") + `"
    ],
    "name": "` + _t("watermelon") + `",
    "shortcodes": [
        ":watermelon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍊",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("mandarin") + `",
        "` + _t("orange") + `",
        "` + _t("tangerine") + `"
    ],
    "name": "` + _t("tangerine") + `",
    "shortcodes": [
        ":tangerine:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍋",
    "emoticons": [],
    "keywords": [
        "` + _t("citrus") + `",
        "` + _t("fruit") + `",
        "` + _t("lemon") + `"
    ],
    "name": "` + _t("lemon") + `",
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
        "` + _t("banana") + `",
        "` + _t("fruit") + `"
    ],
    "name": "` + _t("banana") + `",
    "shortcodes": [
        ":banana:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍍",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("pineapple") + `"
    ],
    "name": "` + _t("pineapple") + `",
    "shortcodes": [
        ":pineapple:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥭",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("mango") + `",
        "` + _t("tropical") + `"
    ],
    "name": "` + _t("mango") + `",
    "shortcodes": [
        ":mango:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍎",
    "emoticons": [],
    "keywords": [
        "` + _t("apple") + `",
        "` + _t("fruit") + `",
        "` + _t("red") + `"
    ],
    "name": "` + _t("red apple") + `",
    "shortcodes": [
        ":red_apple:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍏",
    "emoticons": [],
    "keywords": [
        "` + _t("apple") + `",
        "` + _t("fruit") + `",
        "` + _t("green") + `"
    ],
    "name": "` + _t("green apple") + `",
    "shortcodes": [
        ":green_apple:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍐",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("pear") + `"
    ],
    "name": "` + _t("pear") + `",
    "shortcodes": [
        ":pear:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍑",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("peach") + `"
    ],
    "name": "` + _t("peach") + `",
    "shortcodes": [
        ":peach:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍒",
    "emoticons": [],
    "keywords": [
        "` + _t("berries") + `",
        "` + _t("cherries") + `",
        "` + _t("cherry") + `",
        "` + _t("fruit") + `",
        "` + _t("red") + `"
    ],
    "name": "` + _t("cherries") + `",
    "shortcodes": [
        ":cherries:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍓",
    "emoticons": [],
    "keywords": [
        "` + _t("berry") + `",
        "` + _t("fruit") + `",
        "` + _t("strawberry") + `"
    ],
    "name": "` + _t("strawberry") + `",
    "shortcodes": [
        ":strawberry:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥝",
    "emoticons": [],
    "keywords": [
        "` + _t("food") + `",
        "` + _t("fruit") + `",
        "` + _t("kiwi fruit") + `",
        "` + _t("kiwi") + `"
    ],
    "name": "` + _t("kiwi fruit") + `",
    "shortcodes": [
        ":kiwi_fruit:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍅",
    "emoticons": [],
    "keywords": [
        "` + _t("fruit") + `",
        "` + _t("tomato") + `",
        "` + _t("vegetable") + `"
    ],
    "name": "` + _t("tomato") + `",
    "shortcodes": [
        ":tomato:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥥",
    "emoticons": [],
    "keywords": [
        "` + _t("coconut") + `",
        "` + _t("palm") + `",
        "` + _t("piña colada") + `"
    ],
    "name": "` + _t("coconut") + `",
    "shortcodes": [
        ":coconut:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥑",
    "emoticons": [],
    "keywords": [
        "` + _t("avocado") + `",
        "` + _t("food") + `",
        "` + _t("fruit") + `"
    ],
    "name": "` + _t("avocado") + `",
    "shortcodes": [
        ":avocado:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍆",
    "emoticons": [],
    "keywords": [
        "` + _t("aubergine") + `",
        "` + _t("eggplant") + `",
        "` + _t("vegetable") + `"
    ],
    "name": "` + _t("eggplant") + `",
    "shortcodes": [
        ":eggplant:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥔",
    "emoticons": [],
    "keywords": [
        "` + _t("food") + `",
        "` + _t("potato") + `",
        "` + _t("vegetable") + `"
    ],
    "name": "` + _t("potato") + `",
    "shortcodes": [
        ":potato:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥕",
    "emoticons": [],
    "keywords": [
        "` + _t("carrot") + `",
        "` + _t("food") + `",
        "` + _t("vegetable") + `"
    ],
    "name": "` + _t("carrot") + `",
    "shortcodes": [
        ":carrot:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌽",
    "emoticons": [],
    "keywords": [
        "` + _t("corn") + `",
        "` + _t("corn on the cob") + `",
        "` + _t("sweetcorn") + `",
        "` + _t("ear") + `",
        "` + _t("ear of corn") + `",
        "` + _t("maize") + `",
        "` + _t("maze") + `"
    ],
    "name": "` + _t("ear of corn") + `",
    "shortcodes": [
        ":ear_of_corn:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌶️",
    "emoticons": [],
    "keywords": [
        "` + _t("chilli") + `",
        "` + _t("hot pepper") + `",
        "` + _t("pepper") + `",
        "` + _t("hot") + `"
    ],
    "name": "` + _t("hot pepper") + `",
    "shortcodes": [
        ":hot_pepper:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥒",
    "emoticons": [],
    "keywords": [
        "` + _t("cucumber") + `",
        "` + _t("food") + `",
        "` + _t("pickle") + `",
        "` + _t("vegetable") + `"
    ],
    "name": "` + _t("cucumber") + `",
    "shortcodes": [
        ":cucumber:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥬",
    "emoticons": [],
    "keywords": [
        "` + _t("bok choy") + `",
        "` + _t("leafy green") + `",
        "` + _t("pak choi") + `",
        "` + _t("cabbage") + `",
        "` + _t("kale") + `",
        "` + _t("lettuce") + `"
    ],
    "name": "` + _t("leafy green") + `",
    "shortcodes": [
        ":leafy_green:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥦",
    "emoticons": [],
    "keywords": [
        "` + _t("broccoli") + `",
        "` + _t("wild cabbage") + `"
    ],
    "name": "` + _t("broccoli") + `",
    "shortcodes": [
        ":broccoli:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧄",
    "emoticons": [],
    "keywords": [
        "` + _t("flavouring") + `",
        "` + _t("garlic") + `",
        "` + _t("flavoring") + `"
    ],
    "name": "` + _t("garlic") + `",
    "shortcodes": [
        ":garlic:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧅",
    "emoticons": [],
    "keywords": [
        "` + _t("flavouring") + `",
        "` + _t("onion") + `",
        "` + _t("flavoring") + `"
    ],
    "name": "` + _t("onion") + `",
    "shortcodes": [
        ":onion:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍄",
    "emoticons": [],
    "keywords": [
        "` + _t("mushroom") + `",
        "` + _t("toadstool") + `"
    ],
    "name": "` + _t("mushroom") + `",
    "shortcodes": [
        ":mushroom:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥜",
    "emoticons": [],
    "keywords": [
        "` + _t("food") + `",
        "` + _t("nut") + `",
        "` + _t("nuts") + `",
        "` + _t("peanut") + `",
        "` + _t("peanuts") + `",
        "` + _t("vegetable") + `"
    ],
    "name": "` + _t("peanuts") + `",
    "shortcodes": [
        ":peanuts:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌰",
    "emoticons": [],
    "keywords": [
        "` + _t("chestnut") + `",
        "` + _t("plant") + `",
        "` + _t("nut") + `"
    ],
    "name": "` + _t("chestnut") + `",
    "shortcodes": [
        ":chestnut:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍞",
    "emoticons": [],
    "keywords": [
        "` + _t("bread") + `",
        "` + _t("loaf") + `"
    ],
    "name": "` + _t("bread") + `",
    "shortcodes": [
        ":bread:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥐",
    "emoticons": [],
    "keywords": [
        "` + _t("bread") + `",
        "` + _t("breakfast") + `",
        "` + _t("croissant") + `",
        "` + _t("food") + `",
        "` + _t("french") + `",
        "` + _t("roll") + `",
        "` + _t("crescent roll") + `",
        "` + _t("French") + `"
    ],
    "name": "` + _t("croissant") + `",
    "shortcodes": [
        ":croissant:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥖",
    "emoticons": [],
    "keywords": [
        "` + _t("baguette") + `",
        "` + _t("bread") + `",
        "` + _t("food") + `",
        "` + _t("french") + `",
        "` + _t("French stick") + `",
        "` + _t("French") + `"
    ],
    "name": "` + _t("baguette bread") + `",
    "shortcodes": [
        ":baguette_bread:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥨",
    "emoticons": [],
    "keywords": [
        "` + _t("pretzel") + `",
        "` + _t("twisted") + `"
    ],
    "name": "` + _t("pretzel") + `",
    "shortcodes": [
        ":pretzel:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥯",
    "emoticons": [],
    "keywords": [
        "` + _t("bagel") + `",
        "` + _t("bakery") + `",
        "` + _t("breakfast") + `",
        "` + _t("schmear") + `"
    ],
    "name": "` + _t("bagel") + `",
    "shortcodes": [
        ":bagel:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥞",
    "emoticons": [],
    "keywords": [
        "` + _t("breakfast") + `",
        "` + _t("crêpe") + `",
        "` + _t("food") + `",
        "` + _t("hotcake") + `",
        "` + _t("pancake") + `",
        "` + _t("pancakes") + `"
    ],
    "name": "` + _t("pancakes") + `",
    "shortcodes": [
        ":pancakes:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧇",
    "emoticons": [],
    "keywords": [
        "` + _t("waffle") + `",
        "` + _t("waffle with butter") + `",
        "` + _t("breakfast") + `",
        "` + _t("indecisive") + `",
        "` + _t("iron") + `",
        "` + _t("unclear") + `",
        "` + _t("vague") + `"
    ],
    "name": "` + _t("waffle") + `",
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
        "` + _t("cheese") + `",
        "` + _t("cheese wedge") + `"
    ],
    "name": "` + _t("cheese wedge") + `",
    "shortcodes": [
        ":cheese_wedge:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍖",
    "emoticons": [],
    "keywords": [
        "` + _t("bone") + `",
        "` + _t("meat") + `",
        "` + _t("meat on bone") + `"
    ],
    "name": "` + _t("meat on bone") + `",
    "shortcodes": [
        ":meat_on_bone:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍗",
    "emoticons": [],
    "keywords": [
        "` + _t("bone") + `",
        "` + _t("chicken") + `",
        "` + _t("drumstick") + `",
        "` + _t("leg") + `",
        "` + _t("poultry") + `"
    ],
    "name": "` + _t("poultry leg") + `",
    "shortcodes": [
        ":poultry_leg:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥩",
    "emoticons": [],
    "keywords": [
        "` + _t("chop") + `",
        "` + _t("cut of meat") + `",
        "` + _t("lambchop") + `",
        "` + _t("porkchop") + `",
        "` + _t("steak") + `",
        "` + _t("lamb chop") + `",
        "` + _t("pork chop") + `"
    ],
    "name": "` + _t("cut of meat") + `",
    "shortcodes": [
        ":cut_of_meat:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥓",
    "emoticons": [],
    "keywords": [
        "` + _t("bacon") + `",
        "` + _t("breakfast") + `",
        "` + _t("food") + `",
        "` + _t("meat") + `"
    ],
    "name": "` + _t("bacon") + `",
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
        "` + _t("beefburger") + `",
        "` + _t("burger") + `",
        "` + _t("hamburger") + `"
    ],
    "name": "` + _t("hamburger") + `",
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
        "` + _t("chips") + `",
        "` + _t("french fries") + `",
        "` + _t("fries") + `",
        "` + _t("french") + `",
        "` + _t("French") + `"
    ],
    "name": "` + _t("french fries") + `",
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
        "` + _t("cheese") + `",
        "` + _t("pizza") + `",
        "` + _t("slice") + `"
    ],
    "name": "` + _t("pizza") + `",
    "shortcodes": [
        ":pizza:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌭",
    "emoticons": [],
    "keywords": [
        "` + _t("frankfurter") + `",
        "` + _t("hot dog") + `",
        "` + _t("hotdog") + `",
        "` + _t("sausage") + `"
    ],
    "name": "` + _t("hot dog") + `",
    "shortcodes": [
        ":hot_dog:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥪",
    "emoticons": [],
    "keywords": [
        "` + _t("bread") + `",
        "` + _t("sandwich") + `"
    ],
    "name": "` + _t("sandwich") + `",
    "shortcodes": [
        ":sandwich:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌮",
    "emoticons": [],
    "keywords": [
        "` + _t("mexican") + `",
        "` + _t("taco") + `",
        "` + _t("Mexican") + `"
    ],
    "name": "` + _t("taco") + `",
    "shortcodes": [
        ":taco:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🌯",
    "emoticons": [],
    "keywords": [
        "` + _t("burrito") + `",
        "` + _t("mexican") + `",
        "` + _t("wrap") + `",
        "` + _t("Mexican") + `"
    ],
    "name": "` + _t("burrito") + `",
    "shortcodes": [
        ":burrito:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥙",
    "emoticons": [],
    "keywords": [
        "` + _t("falafel") + `",
        "` + _t("flatbread") + `",
        "` + _t("food") + `",
        "` + _t("gyro") + `",
        "` + _t("kebab") + `",
        "` + _t("pita") + `",
        "` + _t("pita roll") + `",
        "` + _t("stuffed") + `"
    ],
    "name": "` + _t("stuffed flatbread") + `",
    "shortcodes": [
        ":stuffed_flatbread:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧆",
    "emoticons": [],
    "keywords": [
        "` + _t("chickpea") + `",
        "` + _t("falafel") + `",
        "` + _t("meatball") + `",
        "` + _t("chick pea") + `"
    ],
    "name": "` + _t("falafel") + `",
    "shortcodes": [
        ":falafel:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥚",
    "emoticons": [],
    "keywords": [
        "` + _t("breakfast") + `",
        "` + _t("egg") + `",
        "` + _t("food") + `"
    ],
    "name": "` + _t("egg") + `",
    "shortcodes": [
        ":egg:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍳",
    "emoticons": [],
    "keywords": [
        "` + _t("breakfast") + `",
        "` + _t("cooking") + `",
        "` + _t("egg") + `",
        "` + _t("frying") + `",
        "` + _t("pan") + `"
    ],
    "name": "` + _t("cooking") + `",
    "shortcodes": [
        ":cooking:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥘",
    "emoticons": [],
    "keywords": [
        "` + _t("casserole") + `",
        "` + _t("food") + `",
        "` + _t("paella") + `",
        "` + _t("pan") + `",
        "` + _t("shallow") + `",
        "` + _t("shallow pan of food") + `"
    ],
    "name": "` + _t("shallow pan of food") + `",
    "shortcodes": [
        ":shallow_pan_of_food:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍲",
    "emoticons": [],
    "keywords": [
        "` + _t("pot") + `",
        "` + _t("pot of food") + `",
        "` + _t("stew") + `"
    ],
    "name": "` + _t("pot of food") + `",
    "shortcodes": [
        ":pot_of_food:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥣",
    "emoticons": [],
    "keywords": [
        "` + _t("bowl with spoon") + `",
        "` + _t("breakfast") + `",
        "` + _t("cereal") + `",
        "` + _t("congee") + `"
    ],
    "name": "` + _t("bowl with spoon") + `",
    "shortcodes": [
        ":bowl_with_spoon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥗",
    "emoticons": [],
    "keywords": [
        "` + _t("food") + `",
        "` + _t("garden") + `",
        "` + _t("salad") + `",
        "` + _t("green") + `"
    ],
    "name": "` + _t("green salad") + `",
    "shortcodes": [
        ":green_salad:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍿",
    "emoticons": [],
    "keywords": [
        "` + _t("popcorn") + `"
    ],
    "name": "` + _t("popcorn") + `",
    "shortcodes": [
        ":popcorn:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧈",
    "emoticons": [],
    "keywords": [
        "` + _t("butter") + `",
        "` + _t("dairy") + `"
    ],
    "name": "` + _t("butter") + `",
    "shortcodes": [
        ":butter:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧂",
    "emoticons": [],
    "keywords": [
        "` + _t("condiment") + `",
        "` + _t("salt") + `",
        "` + _t("shaker") + `"
    ],
    "name": "` + _t("salt") + `",
    "shortcodes": [
        ":salt:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥫",
    "emoticons": [],
    "keywords": [
        "` + _t("can") + `",
        "` + _t("canned food") + `"
    ],
    "name": "` + _t("canned food") + `",
    "shortcodes": [
        ":canned_food:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍱",
    "emoticons": [],
    "keywords": [
        "` + _t("bento") + `",
        "` + _t("box") + `"
    ],
    "name": "` + _t("bento box") + `",
    "shortcodes": [
        ":bento_box:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍘",
    "emoticons": [],
    "keywords": [
        "` + _t("cracker") + `",
        "` + _t("rice") + `"
    ],
    "name": "` + _t("rice cracker") + `",
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
        "` + _t("ball") + `",
        "` + _t("Japanese") + `",
        "` + _t("rice") + `"
    ],
    "name": "` + _t("rice ball") + `",
    "shortcodes": [
        ":rice_ball:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍚",
    "emoticons": [],
    "keywords": [
        "` + _t("cooked") + `",
        "` + _t("rice") + `"
    ],
    "name": "` + _t("cooked rice") + `",
    "shortcodes": [
        ":cooked_rice:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍛",
    "emoticons": [],
    "keywords": [
        "` + _t("curry") + `",
        "` + _t("rice") + `"
    ],
    "name": "` + _t("curry rice") + `",
    "shortcodes": [
        ":curry_rice:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍜",
    "emoticons": [],
    "keywords": [
        "` + _t("bowl") + `",
        "` + _t("noodle") + `",
        "` + _t("ramen") + `",
        "` + _t("steaming") + `"
    ],
    "name": "` + _t("steaming bowl") + `",
    "shortcodes": [
        ":steaming_bowl:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍝",
    "emoticons": [],
    "keywords": [
        "` + _t("pasta") + `",
        "` + _t("spaghetti") + `"
    ],
    "name": "` + _t("spaghetti") + `",
    "shortcodes": [
        ":spaghetti:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍠",
    "emoticons": [],
    "keywords": [
        "` + _t("potato") + `",
        "` + _t("roasted") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("roasted sweet potato") + `",
    "shortcodes": [
        ":roasted_sweet_potato:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍢",
    "emoticons": [],
    "keywords": [
        "` + _t("kebab") + `",
        "` + _t("oden") + `",
        "` + _t("seafood") + `",
        "` + _t("skewer") + `",
        "` + _t("stick") + `"
    ],
    "name": "` + _t("oden") + `",
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
        "` + _t("sushi") + `"
    ],
    "name": "` + _t("sushi") + `",
    "shortcodes": [
        ":sushi:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍤",
    "emoticons": [],
    "keywords": [
        "` + _t("battered") + `",
        "` + _t("fried") + `",
        "` + _t("prawn") + `",
        "` + _t("shrimp") + `",
        "` + _t("tempura") + `"
    ],
    "name": "` + _t("fried shrimp") + `",
    "shortcodes": [
        ":fried_shrimp:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍥",
    "emoticons": [],
    "keywords": [
        "` + _t("cake") + `",
        "` + _t("fish") + `",
        "` + _t("fish cake with swirl") + `",
        "` + _t("pastry") + `",
        "` + _t("swirl") + `",
        "` + _t("narutomaki") + `"
    ],
    "name": "` + _t("fish cake with swirl") + `",
    "shortcodes": [
        ":fish_cake_with_swirl:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥮",
    "emoticons": [],
    "keywords": [
        "` + _t("autumn") + `",
        "` + _t("festival") + `",
        "` + _t("moon cake") + `",
        "` + _t("yuèbǐng") + `"
    ],
    "name": "` + _t("moon cake") + `",
    "shortcodes": [
        ":moon_cake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍡",
    "emoticons": [],
    "keywords": [
        "` + _t("dango") + `",
        "` + _t("dessert") + `",
        "` + _t("Japanese") + `",
        "` + _t("skewer") + `",
        "` + _t("stick") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("dango") + `",
    "shortcodes": [
        ":dango:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥟",
    "emoticons": [],
    "keywords": [
        "` + _t("dumpling") + `",
        "` + _t("empanada") + `",
        "` + _t("gyōza") + `",
        "` + _t("pastie") + `",
        "` + _t("samosa") + `",
        "` + _t("jiaozi") + `",
        "` + _t("pierogi") + `",
        "` + _t("potsticker") + `"
    ],
    "name": "` + _t("dumpling") + `",
    "shortcodes": [
        ":dumpling:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥠",
    "emoticons": [],
    "keywords": [
        "` + _t("fortune cookie") + `",
        "` + _t("prophecy") + `"
    ],
    "name": "` + _t("fortune cookie") + `",
    "shortcodes": [
        ":fortune_cookie:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥡",
    "emoticons": [],
    "keywords": [
        "` + _t("takeaway container") + `",
        "` + _t("takeout") + `",
        "` + _t("oyster pail") + `",
        "` + _t("takeout box") + `",
        "` + _t("takeaway box") + `"
    ],
    "name": "` + _t("takeout box") + `",
    "shortcodes": [
        ":takeout_box:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦀",
    "emoticons": [],
    "keywords": [
        "` + _t("crab") + `",
        "` + _t("crustacean") + `",
        "` + _t("seafood") + `",
        "` + _t("shellfish") + `",
        "` + _t("Cancer") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("crab") + `",
    "shortcodes": [
        ":crab:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦞",
    "emoticons": [],
    "keywords": [
        "` + _t("bisque") + `",
        "` + _t("claws") + `",
        "` + _t("lobster") + `",
        "` + _t("seafood") + `",
        "` + _t("shellfish") + `"
    ],
    "name": "` + _t("lobster") + `",
    "shortcodes": [
        ":lobster:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦐",
    "emoticons": [],
    "keywords": [
        "` + _t("prawn") + `",
        "` + _t("seafood") + `",
        "` + _t("shellfish") + `",
        "` + _t("shrimp") + `",
        "` + _t("food") + `",
        "` + _t("small") + `"
    ],
    "name": "` + _t("shrimp") + `",
    "shortcodes": [
        ":shrimp:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦑",
    "emoticons": [],
    "keywords": [
        "` + _t("decapod") + `",
        "` + _t("seafood") + `",
        "` + _t("squid") + `",
        "` + _t("food") + `",
        "` + _t("molusc") + `"
    ],
    "name": "` + _t("squid") + `",
    "shortcodes": [
        ":squid:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🦪",
    "emoticons": [],
    "keywords": [
        "` + _t("diving") + `",
        "` + _t("oyster") + `",
        "` + _t("pearl") + `"
    ],
    "name": "` + _t("oyster") + `",
    "shortcodes": [
        ":oyster:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍦",
    "emoticons": [],
    "keywords": [
        "` + _t("cream") + `",
        "` + _t("dessert") + `",
        "` + _t("ice cream") + `",
        "` + _t("soft serve") + `",
        "` + _t("sweet") + `",
        "` + _t("ice") + `",
        "` + _t("icecream") + `",
        "` + _t("soft") + `"
    ],
    "name": "` + _t("soft ice cream") + `",
    "shortcodes": [
        ":soft_ice_cream:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍧",
    "emoticons": [],
    "keywords": [
        "` + _t("dessert") + `",
        "` + _t("granita") + `",
        "` + _t("ice") + `",
        "` + _t("sweet") + `",
        "` + _t("shaved") + `"
    ],
    "name": "` + _t("shaved ice") + `",
    "shortcodes": [
        ":shaved_ice:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍨",
    "emoticons": [],
    "keywords": [
        "` + _t("cream") + `",
        "` + _t("dessert") + `",
        "` + _t("ice cream") + `",
        "` + _t("sweet") + `",
        "` + _t("ice") + `"
    ],
    "name": "` + _t("ice cream") + `",
    "shortcodes": [
        ":ice_cream:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍩",
    "emoticons": [],
    "keywords": [
        "` + _t("breakfast") + `",
        "` + _t("dessert") + `",
        "` + _t("donut") + `",
        "` + _t("doughnut") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("doughnut") + `",
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
        "` + _t("biscuit") + `",
        "` + _t("cookie") + `",
        "` + _t("dessert") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("cookie") + `",
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
        "` + _t("birthday") + `",
        "` + _t("cake") + `",
        "` + _t("celebration") + `",
        "` + _t("dessert") + `",
        "` + _t("pastry") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("birthday cake") + `",
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
        "` + _t("cake") + `",
        "` + _t("dessert") + `",
        "` + _t("pastry") + `",
        "` + _t("shortcake") + `",
        "` + _t("slice") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("shortcake") + `",
    "shortcodes": [
        ":shortcake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧁",
    "emoticons": [],
    "keywords": [
        "` + _t("bakery") + `",
        "` + _t("cupcake") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("cupcake") + `",
    "shortcodes": [
        ":cupcake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥧",
    "emoticons": [],
    "keywords": [
        "` + _t("filling") + `",
        "` + _t("pastry") + `",
        "` + _t("pie") + `"
    ],
    "name": "` + _t("pie") + `",
    "shortcodes": [
        ":pie:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍫",
    "emoticons": [],
    "keywords": [
        "` + _t("bar") + `",
        "` + _t("chocolate") + `",
        "` + _t("dessert") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("chocolate bar") + `",
    "shortcodes": [
        ":chocolate_bar:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍬",
    "emoticons": [],
    "keywords": [
        "` + _t("candy") + `",
        "` + _t("dessert") + `",
        "` + _t("sweet") + `",
        "` + _t("sweets") + `"
    ],
    "name": "` + _t("candy") + `",
    "shortcodes": [
        ":candy:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍭",
    "emoticons": [],
    "keywords": [
        "` + _t("candy") + `",
        "` + _t("dessert") + `",
        "` + _t("lollipop") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("lollipop") + `",
    "shortcodes": [
        ":lollipop:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍮",
    "emoticons": [],
    "keywords": [
        "` + _t("baked custard") + `",
        "` + _t("dessert") + `",
        "` + _t("pudding") + `",
        "` + _t("sweet") + `",
        "` + _t("custard") + `"
    ],
    "name": "` + _t("custard") + `",
    "shortcodes": [
        ":custard:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍯",
    "emoticons": [],
    "keywords": [
        "` + _t("honey") + `",
        "` + _t("honeypot") + `",
        "` + _t("pot") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("honey pot") + `",
    "shortcodes": [
        ":honey_pot:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍼",
    "emoticons": [],
    "keywords": [
        "` + _t("baby") + `",
        "` + _t("bottle") + `",
        "` + _t("drink") + `",
        "` + _t("milk") + `"
    ],
    "name": "` + _t("baby bottle") + `",
    "shortcodes": [
        ":baby_bottle:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥛",
    "emoticons": [],
    "keywords": [
        "` + _t("drink") + `",
        "` + _t("glass") + `",
        "` + _t("glass of milk") + `",
        "` + _t("milk") + `"
    ],
    "name": "` + _t("glass of milk") + `",
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
        "` + _t("beverage") + `",
        "` + _t("coffee") + `",
        "` + _t("drink") + `",
        "` + _t("hot") + `",
        "` + _t("steaming") + `",
        "` + _t("tea") + `"
    ],
    "name": "` + _t("hot beverage") + `",
    "shortcodes": [
        ":hot_beverage:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍵",
    "emoticons": [],
    "keywords": [
        "` + _t("beverage") + `",
        "` + _t("cup") + `",
        "` + _t("drink") + `",
        "` + _t("tea") + `",
        "` + _t("teacup") + `",
        "` + _t("teacup without handle") + `"
    ],
    "name": "` + _t("teacup without handle") + `",
    "shortcodes": [
        ":teacup_without_handle:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍶",
    "emoticons": [],
    "keywords": [
        "` + _t("bar") + `",
        "` + _t("beverage") + `",
        "` + _t("bottle") + `",
        "` + _t("cup") + `",
        "` + _t("drink") + `",
        "` + _t("sake") + `",
        "` + _t("saké") + `"
    ],
    "name": "` + _t("sake") + `",
    "shortcodes": [
        ":sake:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍾",
    "emoticons": [],
    "keywords": [
        "` + _t("bar") + `",
        "` + _t("bottle") + `",
        "` + _t("bottle with popping cork") + `",
        "` + _t("cork") + `",
        "` + _t("drink") + `",
        "` + _t("popping") + `"
    ],
    "name": "` + _t("bottle with popping cork") + `",
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
        "` + _t("bar") + `",
        "` + _t("beverage") + `",
        "` + _t("drink") + `",
        "` + _t("glass") + `",
        "` + _t("wine") + `"
    ],
    "name": "` + _t("wine glass") + `",
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
        "` + _t("bar") + `",
        "` + _t("cocktail") + `",
        "` + _t("drink") + `",
        "` + _t("glass") + `"
    ],
    "name": "` + _t("cocktail glass") + `",
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
        "` + _t("bar") + `",
        "` + _t("drink") + `",
        "` + _t("tropical") + `"
    ],
    "name": "` + _t("tropical drink") + `",
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
        "` + _t("bar") + `",
        "` + _t("beer") + `",
        "` + _t("drink") + `",
        "` + _t("mug") + `"
    ],
    "name": "` + _t("beer mug") + `",
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
        "` + _t("bar") + `",
        "` + _t("beer") + `",
        "` + _t("clink") + `",
        "` + _t("clinking beer mugs") + `",
        "` + _t("drink") + `",
        "` + _t("mug") + `"
    ],
    "name": "` + _t("clinking beer mugs") + `",
    "shortcodes": [
        ":clinking_beer_mugs:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥂",
    "emoticons": [],
    "keywords": [
        "` + _t("celebrate") + `",
        "` + _t("clink") + `",
        "` + _t("clinking glasses") + `",
        "` + _t("drink") + `",
        "` + _t("glass") + `"
    ],
    "name": "` + _t("clinking glasses") + `",
    "shortcodes": [
        ":clinking_glasses:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥃",
    "emoticons": [],
    "keywords": [
        "` + _t("glass") + `",
        "` + _t("liquor") + `",
        "` + _t("shot") + `",
        "` + _t("tumbler") + `",
        "` + _t("whisky") + `"
    ],
    "name": "` + _t("tumbler glass") + `",
    "shortcodes": [
        ":tumbler_glass:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥤",
    "emoticons": [],
    "keywords": [
        "` + _t("cup with straw") + `",
        "` + _t("juice") + `",
        "` + _t("soda") + `"
    ],
    "name": "` + _t("cup with straw") + `",
    "shortcodes": [
        ":cup_with_straw:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧃",
    "emoticons": [],
    "keywords": [
        "` + _t("drink carton") + `",
        "` + _t("juice box") + `",
        "` + _t("popper") + `",
        "` + _t("beverage") + `",
        "` + _t("box") + `",
        "` + _t("juice") + `",
        "` + _t("straw") + `",
        "` + _t("sweet") + `"
    ],
    "name": "` + _t("beverage box") + `",
    "shortcodes": [
        ":beverage_box:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧉",
    "emoticons": [],
    "keywords": [
        "` + _t("drink") + `",
        "` + _t("mate") + `",
        "` + _t("maté") + `"
    ],
    "name": "` + _t("mate") + `",
    "shortcodes": [
        ":mate:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🧊",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("ice") + `",
        "` + _t("ice cube") + `",
        "` + _t("iceberg") + `"
    ],
    "name": "` + _t("ice") + `",
    "shortcodes": [
        ":ice:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥢",
    "emoticons": [],
    "keywords": [
        "` + _t("chopsticks") + `",
        "` + _t("pair of chopsticks") + `",
        "` + _t("hashi") + `"
    ],
    "name": "` + _t("chopsticks") + `",
    "shortcodes": [
        ":chopsticks:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍽️",
    "emoticons": [],
    "keywords": [
        "` + _t("cooking") + `",
        "` + _t("fork") + `",
        "` + _t("fork and knife with plate") + `",
        "` + _t("knife") + `",
        "` + _t("plate") + `"
    ],
    "name": "` + _t("fork and knife with plate") + `",
    "shortcodes": [
        ":fork_and_knife_with_plate:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🍴",
    "emoticons": [],
    "keywords": [
        "` + _t("cooking") + `",
        "` + _t("cutlery") + `",
        "` + _t("fork") + `",
        "` + _t("fork and knife") + `",
        "` + _t("knife") + `",
        "` + _t("knife and fork") + `"
    ],
    "name": "` + _t("fork and knife") + `",
    "shortcodes": [
        ":fork_and_knife:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🥄",
    "emoticons": [],
    "keywords": [
        "` + _t("spoon") + `",
        "` + _t("tableware") + `"
    ],
    "name": "` + _t("spoon") + `",
    "shortcodes": [
        ":spoon:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🔪",
    "emoticons": [],
    "keywords": [
        "` + _t("cooking") + `",
        "` + _t("hocho") + `",
        "` + _t("kitchen knife") + `",
        "` + _t("knife") + `",
        "` + _t("tool") + `",
        "` + _t("weapon") + `"
    ],
    "name": "` + _t("kitchen knife") + `",
    "shortcodes": [
        ":kitchen_knife:"
    ]
},
{
    "category": "Food & Drink",
    "codepoints": "🏺",
    "emoticons": [],
    "keywords": [
        "` + _t("amphora") + `",
        "` + _t("Aquarius") + `",
        "` + _t("cooking") + `",
        "` + _t("drink") + `",
        "` + _t("jug") + `",
        "` + _t("zodiac") + `",
        "` + _t("jar") + `"
    ],
    "name": "` + _t("amphora") + `",
    "shortcodes": [
        ":amphora:"
    ]
},`;

const _getEmojisData5 = () => `{
    "category": "Travel & Places",
    "codepoints": "🌍",
    "emoticons": [],
    "keywords": [
        "` + _t("Africa") + `",
        "` + _t("earth") + `",
        "` + _t("Europe") + `",
        "` + _t("globe") + `",
        "` + _t("globe showing Europe-Africa") + `",
        "` + _t("world") + `"
    ],
    "name": "` + _t("globe showing Europe-Africa") + `",
    "shortcodes": [
        ":globe_showing_Europe-Africa:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌎",
    "emoticons": [],
    "keywords": [
        "` + _t("Americas") + `",
        "` + _t("earth") + `",
        "` + _t("globe") + `",
        "` + _t("globe showing Americas") + `",
        "` + _t("world") + `"
    ],
    "name": "` + _t("globe showing Americas") + `",
    "shortcodes": [
        ":globe_showing_Americas:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌏",
    "emoticons": [],
    "keywords": [
        "` + _t("Asia") + `",
        "` + _t("Australia") + `",
        "` + _t("earth") + `",
        "` + _t("globe") + `",
        "` + _t("globe showing Asia-Australia") + `",
        "` + _t("world") + `"
    ],
    "name": "` + _t("globe showing Asia-Australia") + `",
    "shortcodes": [
        ":globe_showing_Asia-Australia:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌐",
    "emoticons": [],
    "keywords": [
        "` + _t("earth") + `",
        "` + _t("globe") + `",
        "` + _t("globe with meridians") + `",
        "` + _t("meridians") + `",
        "` + _t("world") + `"
    ],
    "name": "` + _t("globe with meridians") + `",
    "shortcodes": [
        ":globe_with_meridians:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗺️",
    "emoticons": [],
    "keywords": [
        "` + _t("map") + `",
        "` + _t("world") + `"
    ],
    "name": "` + _t("world map") + `",
    "shortcodes": [
        ":world_map:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗾",
    "emoticons": [],
    "keywords": [
        "` + _t("Japan") + `",
        "` + _t("map") + `",
        "` + _t("map of Japan") + `"
    ],
    "name": "` + _t("map of Japan") + `",
    "shortcodes": [
        ":map_of_Japan:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🧭",
    "emoticons": [],
    "keywords": [
        "` + _t("compass") + `",
        "` + _t("magnetic") + `",
        "` + _t("navigation") + `",
        "` + _t("orienteering") + `"
    ],
    "name": "` + _t("compass") + `",
    "shortcodes": [
        ":compass:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏔️",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("mountain") + `",
        "` + _t("snow") + `",
        "` + _t("snow-capped mountain") + `"
    ],
    "name": "` + _t("snow-capped mountain") + `",
    "shortcodes": [
        ":snow-capped_mountain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛰️",
    "emoticons": [],
    "keywords": [
        "` + _t("mountain") + `"
    ],
    "name": "` + _t("mountain") + `",
    "shortcodes": [
        ":mountain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌋",
    "emoticons": [],
    "keywords": [
        "` + _t("eruption") + `",
        "` + _t("mountain") + `",
        "` + _t("volcano") + `"
    ],
    "name": "` + _t("volcano") + `",
    "shortcodes": [
        ":volcano:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗻",
    "emoticons": [],
    "keywords": [
        "` + _t("Fuji") + `",
        "` + _t("mount Fuji") + `",
        "` + _t("mountain") + `",
        "` + _t("fuji") + `",
        "` + _t("mount fuji") + `",
        "` + _t("Mount Fuji") + `"
    ],
    "name": "` + _t("mount fuji") + `",
    "shortcodes": [
        ":mount_fuji:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏕️",
    "emoticons": [],
    "keywords": [
        "` + _t("camping") + `"
    ],
    "name": "` + _t("camping") + `",
    "shortcodes": [
        ":camping:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏖️",
    "emoticons": [],
    "keywords": [
        "` + _t("beach") + `",
        "` + _t("beach with umbrella") + `",
        "` + _t("umbrella") + `"
    ],
    "name": "` + _t("beach with umbrella") + `",
    "shortcodes": [
        ":beach_with_umbrella:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏜️",
    "emoticons": [],
    "keywords": [
        "` + _t("desert") + `"
    ],
    "name": "` + _t("desert") + `",
    "shortcodes": [
        ":desert:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏝️",
    "emoticons": [],
    "keywords": [
        "` + _t("desert") + `",
        "` + _t("island") + `"
    ],
    "name": "` + _t("desert island") + `",
    "shortcodes": [
        ":desert_island:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏞️",
    "emoticons": [],
    "keywords": [
        "` + _t("national park") + `",
        "` + _t("park") + `"
    ],
    "name": "` + _t("national park") + `",
    "shortcodes": [
        ":national_park:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏟️",
    "emoticons": [],
    "keywords": [
        "` + _t("arena") + `",
        "` + _t("stadium") + `"
    ],
    "name": "` + _t("stadium") + `",
    "shortcodes": [
        ":stadium:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏛️",
    "emoticons": [],
    "keywords": [
        "` + _t("classical") + `",
        "` + _t("classical building") + `",
        "` + _t("column") + `"
    ],
    "name": "` + _t("classical building") + `",
    "shortcodes": [
        ":classical_building:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏗️",
    "emoticons": [],
    "keywords": [
        "` + _t("building construction") + `",
        "` + _t("construction") + `"
    ],
    "name": "` + _t("building construction") + `",
    "shortcodes": [
        ":building_construction:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🧱",
    "emoticons": [],
    "keywords": [
        "` + _t("brick") + `",
        "` + _t("bricks") + `",
        "` + _t("clay") + `",
        "` + _t("mortar") + `",
        "` + _t("wall") + `"
    ],
    "name": "` + _t("brick") + `",
    "shortcodes": [
        ":brick:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏘️",
    "emoticons": [],
    "keywords": [
        "` + _t("houses") + `"
    ],
    "name": "` + _t("houses") + `",
    "shortcodes": [
        ":houses:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏚️",
    "emoticons": [],
    "keywords": [
        "` + _t("derelict") + `",
        "` + _t("house") + `"
    ],
    "name": "` + _t("derelict house") + `",
    "shortcodes": [
        ":derelict_house:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏠",
    "emoticons": [],
    "keywords": [
        "` + _t("home") + `",
        "` + _t("house") + `"
    ],
    "name": "` + _t("house") + `",
    "shortcodes": [
        ":house:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏡",
    "emoticons": [],
    "keywords": [
        "` + _t("garden") + `",
        "` + _t("home") + `",
        "` + _t("house") + `",
        "` + _t("house with garden") + `"
    ],
    "name": "` + _t("house with garden") + `",
    "shortcodes": [
        ":house_with_garden:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏢",
    "emoticons": [],
    "keywords": [
        "` + _t("building") + `",
        "` + _t("office building") + `"
    ],
    "name": "` + _t("office building") + `",
    "shortcodes": [
        ":office_building:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏣",
    "emoticons": [],
    "keywords": [
        "` + _t("Japanese") + `",
        "` + _t("Japanese post office") + `",
        "` + _t("post") + `"
    ],
    "name": "` + _t("Japanese post office") + `",
    "shortcodes": [
        ":Japanese_post_office:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏤",
    "emoticons": [],
    "keywords": [
        "` + _t("European") + `",
        "` + _t("post") + `",
        "` + _t("post office") + `"
    ],
    "name": "` + _t("post office") + `",
    "shortcodes": [
        ":post_office:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏥",
    "emoticons": [],
    "keywords": [
        "` + _t("doctor") + `",
        "` + _t("hospital") + `",
        "` + _t("medicine") + `"
    ],
    "name": "` + _t("hospital") + `",
    "shortcodes": [
        ":hospital:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏦",
    "emoticons": [],
    "keywords": [
        "` + _t("bank") + `",
        "` + _t("building") + `"
    ],
    "name": "` + _t("bank") + `",
    "shortcodes": [
        ":bank:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏨",
    "emoticons": [],
    "keywords": [
        "` + _t("building") + `",
        "` + _t("hotel") + `"
    ],
    "name": "` + _t("hotel") + `",
    "shortcodes": [
        ":hotel:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏩",
    "emoticons": [],
    "keywords": [
        "` + _t("hotel") + `",
        "` + _t("love") + `"
    ],
    "name": "` + _t("love hotel") + `",
    "shortcodes": [
        ":love_hotel:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏪",
    "emoticons": [],
    "keywords": [
        "` + _t("convenience") + `",
        "` + _t("store") + `",
        "` + _t("dépanneur") + `"
    ],
    "name": "` + _t("convenience store") + `",
    "shortcodes": [
        ":convenience_store:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏫",
    "emoticons": [],
    "keywords": [
        "` + _t("building") + `",
        "` + _t("school") + `"
    ],
    "name": "` + _t("school") + `",
    "shortcodes": [
        ":school:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏬",
    "emoticons": [],
    "keywords": [
        "` + _t("department") + `",
        "` + _t("store") + `"
    ],
    "name": "` + _t("department store") + `",
    "shortcodes": [
        ":department_store:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏭",
    "emoticons": [],
    "keywords": [
        "` + _t("building") + `",
        "` + _t("factory") + `"
    ],
    "name": "` + _t("factory") + `",
    "shortcodes": [
        ":factory:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏯",
    "emoticons": [],
    "keywords": [
        "` + _t("castle") + `",
        "` + _t("Japanese") + `"
    ],
    "name": "` + _t("Japanese castle") + `",
    "shortcodes": [
        ":Japanese_castle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏰",
    "emoticons": [],
    "keywords": [
        "` + _t("castle") + `",
        "` + _t("European") + `"
    ],
    "name": "` + _t("castle") + `",
    "shortcodes": [
        ":castle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "💒",
    "emoticons": [],
    "keywords": [
        "` + _t("chapel") + `",
        "` + _t("romance") + `",
        "` + _t("wedding") + `"
    ],
    "name": "` + _t("wedding") + `",
    "shortcodes": [
        ":wedding:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗼",
    "emoticons": [],
    "keywords": [
        "` + _t("Tokyo") + `",
        "` + _t("tower") + `",
        "` + _t("Tower") + `"
    ],
    "name": "` + _t("Tokyo tower") + `",
    "shortcodes": [
        ":Tokyo_tower:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🗽",
    "emoticons": [],
    "keywords": [
        "` + _t("liberty") + `",
        "` + _t("statue") + `",
        "` + _t("Statue of Liberty") + `",
        "` + _t("Liberty") + `",
        "` + _t("Statue") + `"
    ],
    "name": "` + _t("Statue of Liberty") + `",
    "shortcodes": [
        ":Statue_of_Liberty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛪",
    "emoticons": [],
    "keywords": [
        "` + _t("Christian") + `",
        "` + _t("church") + `",
        "` + _t("cross") + `",
        "` + _t("religion") + `"
    ],
    "name": "` + _t("church") + `",
    "shortcodes": [
        ":church:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕌",
    "emoticons": [],
    "keywords": [
        "` + _t("Islam") + `",
        "` + _t("mosque") + `",
        "` + _t("Muslim") + `",
        "` + _t("religion") + `",
        "` + _t("islam") + `"
    ],
    "name": "` + _t("mosque") + `",
    "shortcodes": [
        ":mosque:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛕",
    "emoticons": [],
    "keywords": [
        "` + _t("hindu") + `",
        "` + _t("temple") + `",
        "` + _t("Hindu") + `"
    ],
    "name": "` + _t("hindu temple") + `",
    "shortcodes": [
        ":hindu_temple:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕍",
    "emoticons": [],
    "keywords": [
        "` + _t("Jew") + `",
        "` + _t("Jewish") + `",
        "` + _t("religion") + `",
        "` + _t("synagogue") + `",
        "` + _t("temple") + `",
        "` + _t("shul") + `"
    ],
    "name": "` + _t("synagogue") + `",
    "shortcodes": [
        ":synagogue:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛩️",
    "emoticons": [],
    "keywords": [
        "` + _t("religion") + `",
        "` + _t("Shinto") + `",
        "` + _t("shrine") + `",
        "` + _t("shinto") + `"
    ],
    "name": "` + _t("shinto shrine") + `",
    "shortcodes": [
        ":shinto_shrine:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕋",
    "emoticons": [],
    "keywords": [
        "` + _t("Islam") + `",
        "` + _t("Kaaba") + `",
        "` + _t("Muslim") + `",
        "` + _t("religion") + `",
        "` + _t("islam") + `",
        "` + _t("kaaba") + `"
    ],
    "name": "` + _t("kaaba") + `",
    "shortcodes": [
        ":kaaba:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛲",
    "emoticons": [],
    "keywords": [
        "` + _t("fountain") + `"
    ],
    "name": "` + _t("fountain") + `",
    "shortcodes": [
        ":fountain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛺",
    "emoticons": [],
    "keywords": [
        "` + _t("camping") + `",
        "` + _t("tent") + `"
    ],
    "name": "` + _t("tent") + `",
    "shortcodes": [
        ":tent:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌁",
    "emoticons": [],
    "keywords": [
        "` + _t("fog") + `",
        "` + _t("foggy") + `"
    ],
    "name": "` + _t("foggy") + `",
    "shortcodes": [
        ":foggy:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌃",
    "emoticons": [],
    "keywords": [
        "` + _t("night") + `",
        "` + _t("night with stars") + `",
        "` + _t("star") + `"
    ],
    "name": "` + _t("night with stars") + `",
    "shortcodes": [
        ":night_with_stars:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏙️",
    "emoticons": [],
    "keywords": [
        "` + _t("city") + `",
        "` + _t("cityscape") + `"
    ],
    "name": "` + _t("cityscape") + `",
    "shortcodes": [
        ":cityscape:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌄",
    "emoticons": [],
    "keywords": [
        "` + _t("morning") + `",
        "` + _t("mountain") + `",
        "` + _t("sun") + `",
        "` + _t("sunrise") + `",
        "` + _t("sunrise over mountains") + `"
    ],
    "name": "` + _t("sunrise over mountains") + `",
    "shortcodes": [
        ":sunrise_over_mountains:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌅",
    "emoticons": [],
    "keywords": [
        "` + _t("morning") + `",
        "` + _t("sun") + `",
        "` + _t("sunrise") + `"
    ],
    "name": "` + _t("sunrise") + `",
    "shortcodes": [
        ":sunrise:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌆",
    "emoticons": [],
    "keywords": [
        "` + _t("city") + `",
        "` + _t("cityscape at dusk") + `",
        "` + _t("dusk") + `",
        "` + _t("evening") + `",
        "` + _t("landscape") + `",
        "` + _t("sunset") + `"
    ],
    "name": "` + _t("cityscape at dusk") + `",
    "shortcodes": [
        ":cityscape_at_dusk:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌇",
    "emoticons": [],
    "keywords": [
        "` + _t("dusk") + `",
        "` + _t("sun") + `",
        "` + _t("sunset") + `"
    ],
    "name": "` + _t("sunset") + `",
    "shortcodes": [
        ":sunset:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌉",
    "emoticons": [],
    "keywords": [
        "` + _t("bridge") + `",
        "` + _t("bridge at night") + `",
        "` + _t("night") + `"
    ],
    "name": "` + _t("bridge at night") + `",
    "shortcodes": [
        ":bridge_at_night:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "♨️",
    "emoticons": [],
    "keywords": [
        "` + _t("hot") + `",
        "` + _t("hotsprings") + `",
        "` + _t("springs") + `",
        "` + _t("steaming") + `"
    ],
    "name": "` + _t("hot springs") + `",
    "shortcodes": [
        ":hot_springs:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🎠",
    "emoticons": [],
    "keywords": [
        "` + _t("carousel") + `",
        "` + _t("horse") + `",
        "` + _t("merry-go-round") + `"
    ],
    "name": "` + _t("carousel horse") + `",
    "shortcodes": [
        ":carousel_horse:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🎡",
    "emoticons": [],
    "keywords": [
        "` + _t("amusement park") + `",
        "` + _t("ferris") + `",
        "` + _t("wheel") + `",
        "` + _t("Ferris") + `",
        "` + _t("theme park") + `"
    ],
    "name": "` + _t("ferris wheel") + `",
    "shortcodes": [
        ":ferris_wheel:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🎢",
    "emoticons": [],
    "keywords": [
        "` + _t("amusement park") + `",
        "` + _t("coaster") + `",
        "` + _t("roller") + `"
    ],
    "name": "` + _t("roller coaster") + `",
    "shortcodes": [
        ":roller_coaster:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "💈",
    "emoticons": [],
    "keywords": [
        "` + _t("barber") + `",
        "` + _t("haircut") + `",
        "` + _t("pole") + `"
    ],
    "name": "` + _t("barber pole") + `",
    "shortcodes": [
        ":barber_pole:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🎪",
    "emoticons": [],
    "keywords": [
        "` + _t("big top") + `",
        "` + _t("circus") + `",
        "` + _t("tent") + `"
    ],
    "name": "` + _t("circus tent") + `",
    "shortcodes": [
        ":circus_tent:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚂",
    "emoticons": [],
    "keywords": [
        "` + _t("engine") + `",
        "` + _t("locomotive") + `",
        "` + _t("railway") + `",
        "` + _t("steam") + `",
        "` + _t("train") + `"
    ],
    "name": "` + _t("locomotive") + `",
    "shortcodes": [
        ":locomotive:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚃",
    "emoticons": [],
    "keywords": [
        "` + _t("car") + `",
        "` + _t("electric") + `",
        "` + _t("railway") + `",
        "` + _t("train") + `",
        "` + _t("tram") + `",
        "` + _t("trolley bus") + `",
        "` + _t("trolleybus") + `",
        "` + _t("railway carriage") + `"
    ],
    "name": "` + _t("railway car") + `",
    "shortcodes": [
        ":railway_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚄",
    "emoticons": [],
    "keywords": [
        "` + _t("high-speed train") + `",
        "` + _t("railway") + `",
        "` + _t("shinkansen") + `",
        "` + _t("speed") + `",
        "` + _t("train") + `",
        "` + _t("Shinkansen") + `"
    ],
    "name": "` + _t("high-speed train") + `",
    "shortcodes": [
        ":high-speed_train:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚅",
    "emoticons": [],
    "keywords": [
        "` + _t("bullet") + `",
        "` + _t("railway") + `",
        "` + _t("shinkansen") + `",
        "` + _t("speed") + `",
        "` + _t("train") + `",
        "` + _t("Shinkansen") + `"
    ],
    "name": "` + _t("bullet train") + `",
    "shortcodes": [
        ":bullet_train:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚆",
    "emoticons": [],
    "keywords": [
        "` + _t("railway") + `",
        "` + _t("train") + `"
    ],
    "name": "` + _t("train") + `",
    "shortcodes": [
        ":train:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚇",
    "emoticons": [],
    "keywords": [
        "` + _t("metro") + `",
        "` + _t("subway") + `"
    ],
    "name": "` + _t("metro") + `",
    "shortcodes": [
        ":metro:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚈",
    "emoticons": [],
    "keywords": [
        "` + _t("light rail") + `",
        "` + _t("railway") + `"
    ],
    "name": "` + _t("light rail") + `",
    "shortcodes": [
        ":light_rail:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚉",
    "emoticons": [],
    "keywords": [
        "` + _t("railway") + `",
        "` + _t("station") + `",
        "` + _t("train") + `"
    ],
    "name": "` + _t("station") + `",
    "shortcodes": [
        ":station:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚊",
    "emoticons": [],
    "keywords": [
        "` + _t("light rail") + `",
        "` + _t("oncoming") + `",
        "` + _t("oncoming light rail") + `",
        "` + _t("tram") + `",
        "` + _t("trolleybus") + `",
        "` + _t("car") + `",
        "` + _t("streetcar") + `",
        "` + _t("tramcar") + `",
        "` + _t("trolley") + `",
        "` + _t("trolley bus") + `"
    ],
    "name": "` + _t("tram") + `",
    "shortcodes": [
        ":tram:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚝",
    "emoticons": [],
    "keywords": [
        "` + _t("monorail") + `",
        "` + _t("vehicle") + `"
    ],
    "name": "` + _t("monorail") + `",
    "shortcodes": [
        ":monorail:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚞",
    "emoticons": [],
    "keywords": [
        "` + _t("car") + `",
        "` + _t("mountain") + `",
        "` + _t("railway") + `"
    ],
    "name": "` + _t("mountain railway") + `",
    "shortcodes": [
        ":mountain_railway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚋",
    "emoticons": [],
    "keywords": [
        "` + _t("car") + `",
        "` + _t("tram") + `",
        "` + _t("trolley bus") + `",
        "` + _t("trolleybus") + `",
        "` + _t("streetcar") + `",
        "` + _t("tramcar") + `",
        "` + _t("trolley") + `"
    ],
    "name": "` + _t("tram car") + `",
    "shortcodes": [
        ":tram_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚌",
    "emoticons": [],
    "keywords": [
        "` + _t("bus") + `",
        "` + _t("vehicle") + `"
    ],
    "name": "` + _t("bus") + `",
    "shortcodes": [
        ":bus:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚍",
    "emoticons": [],
    "keywords": [
        "` + _t("bus") + `",
        "` + _t("oncoming") + `"
    ],
    "name": "` + _t("oncoming bus") + `",
    "shortcodes": [
        ":oncoming_bus:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚎",
    "emoticons": [],
    "keywords": [
        "` + _t("bus") + `",
        "` + _t("tram") + `",
        "` + _t("trolley") + `",
        "` + _t("trolleybus") + `",
        "` + _t("streetcar") + `"
    ],
    "name": "` + _t("trolleybus") + `",
    "shortcodes": [
        ":trolleybus:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚐",
    "emoticons": [],
    "keywords": [
        "` + _t("bus") + `",
        "` + _t("minibus") + `"
    ],
    "name": "` + _t("minibus") + `",
    "shortcodes": [
        ":minibus:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚑",
    "emoticons": [],
    "keywords": [
        "` + _t("ambulance") + `",
        "` + _t("vehicle") + `"
    ],
    "name": "` + _t("ambulance") + `",
    "shortcodes": [
        ":ambulance:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚒",
    "emoticons": [],
    "keywords": [
        "` + _t("engine") + `",
        "` + _t("fire") + `",
        "` + _t("truck") + `"
    ],
    "name": "` + _t("fire engine") + `",
    "shortcodes": [
        ":fire_engine:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚓",
    "emoticons": [],
    "keywords": [
        "` + _t("car") + `",
        "` + _t("patrol") + `",
        "` + _t("police") + `"
    ],
    "name": "` + _t("police car") + `",
    "shortcodes": [
        ":police_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚔",
    "emoticons": [],
    "keywords": [
        "` + _t("car") + `",
        "` + _t("oncoming") + `",
        "` + _t("police") + `"
    ],
    "name": "` + _t("oncoming police car") + `",
    "shortcodes": [
        ":oncoming_police_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚕",
    "emoticons": [],
    "keywords": [
        "` + _t("taxi") + `",
        "` + _t("vehicle") + `"
    ],
    "name": "` + _t("taxi") + `",
    "shortcodes": [
        ":taxi:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚖",
    "emoticons": [],
    "keywords": [
        "` + _t("oncoming") + `",
        "` + _t("taxi") + `"
    ],
    "name": "` + _t("oncoming taxi") + `",
    "shortcodes": [
        ":oncoming_taxi:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚗",
    "emoticons": [],
    "keywords": [
        "` + _t("automobile") + `",
        "` + _t("car") + `"
    ],
    "name": "` + _t("automobile") + `",
    "shortcodes": [
        ":automobile:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚘",
    "emoticons": [],
    "keywords": [
        "` + _t("automobile") + `",
        "` + _t("car") + `",
        "` + _t("oncoming") + `"
    ],
    "name": "` + _t("oncoming automobile") + `",
    "shortcodes": [
        ":oncoming_automobile:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚙",
    "emoticons": [],
    "keywords": [
        "` + _t("4WD") + `",
        "` + _t("four-wheel drive") + `",
        "` + _t("recreational") + `",
        "` + _t("sport utility") + `",
        "` + _t("sport utility vehicle") + `",
        "` + _t("4x4") + `",
        "` + _t("off-road vehicle") + `",
        "` + _t("SUV") + `"
    ],
    "name": "` + _t("sport utility vehicle") + `",
    "shortcodes": [
        ":sport_utility_vehicle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚚",
    "emoticons": [],
    "keywords": [
        "` + _t("delivery") + `",
        "` + _t("truck") + `"
    ],
    "name": "` + _t("delivery truck") + `",
    "shortcodes": [
        ":delivery_truck:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚛",
    "emoticons": [],
    "keywords": [
        "` + _t("articulated truck") + `",
        "` + _t("lorry") + `",
        "` + _t("semi") + `",
        "` + _t("truck") + `",
        "` + _t("articulated lorry") + `"
    ],
    "name": "` + _t("articulated lorry") + `",
    "shortcodes": [
        ":articulated_lorry:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚜",
    "emoticons": [],
    "keywords": [
        "` + _t("tractor") + `",
        "` + _t("vehicle") + `"
    ],
    "name": "` + _t("tractor") + `",
    "shortcodes": [
        ":tractor:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏎️",
    "emoticons": [],
    "keywords": [
        "` + _t("car") + `",
        "` + _t("racing") + `"
    ],
    "name": "` + _t("racing car") + `",
    "shortcodes": [
        ":racing_car:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🏍️",
    "emoticons": [],
    "keywords": [
        "` + _t("motorcycle") + `",
        "` + _t("racing") + `"
    ],
    "name": "` + _t("motorcycle") + `",
    "shortcodes": [
        ":motorcycle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛵",
    "emoticons": [],
    "keywords": [
        "` + _t("motor") + `",
        "` + _t("scooter") + `"
    ],
    "name": "` + _t("motor scooter") + `",
    "shortcodes": [
        ":motor_scooter:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🦽",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("manual wheelchair") + `"
    ],
    "name": "` + _t("manual wheelchair") + `",
    "shortcodes": [
        ":manual_wheelchair:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🦼",
    "emoticons": [],
    "keywords": [
        "` + _t("mobility scooter") + `",
        "` + _t("accessibility") + `",
        "` + _t("motorized wheelchair") + `",
        "` + _t("powered wheelchair") + `"
    ],
    "name": "` + _t("motorized wheelchair") + `",
    "shortcodes": [
        ":motorized_wheelchair:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛺",
    "emoticons": [],
    "keywords": [
        "` + _t("auto rickshaw") + `",
        "` + _t("tuk tuk") + `",
        "` + _t("tuk-tuk") + `",
        "` + _t("tuktuk") + `"
    ],
    "name": "` + _t("auto rickshaw") + `",
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
        "` + _t("bicycle") + `",
        "` + _t("bike") + `"
    ],
    "name": "` + _t("bicycle") + `",
    "shortcodes": [
        ":bicycle:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛴",
    "emoticons": [],
    "keywords": [
        "` + _t("kick") + `",
        "` + _t("scooter") + `"
    ],
    "name": "` + _t("kick scooter") + `",
    "shortcodes": [
        ":kick_scooter:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛹",
    "emoticons": [],
    "keywords": [
        "` + _t("board") + `",
        "` + _t("skateboard") + `"
    ],
    "name": "` + _t("skateboard") + `",
    "shortcodes": [
        ":skateboard:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚏",
    "emoticons": [],
    "keywords": [
        "` + _t("bus") + `",
        "` + _t("stop") + `",
        "` + _t("busstop") + `"
    ],
    "name": "` + _t("bus stop") + `",
    "shortcodes": [
        ":bus_stop:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛣️",
    "emoticons": [],
    "keywords": [
        "` + _t("freeway") + `",
        "` + _t("highway") + `",
        "` + _t("road") + `",
        "` + _t("motorway") + `"
    ],
    "name": "` + _t("motorway") + `",
    "shortcodes": [
        ":motorway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛤️",
    "emoticons": [],
    "keywords": [
        "` + _t("railway") + `",
        "` + _t("railway track") + `",
        "` + _t("train") + `"
    ],
    "name": "` + _t("railway track") + `",
    "shortcodes": [
        ":railway_track:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛢️",
    "emoticons": [],
    "keywords": [
        "` + _t("drum") + `",
        "` + _t("oil") + `"
    ],
    "name": "` + _t("oil drum") + `",
    "shortcodes": [
        ":oil_drum:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛽",
    "emoticons": [],
    "keywords": [
        "` + _t("diesel") + `",
        "` + _t("fuel") + `",
        "` + _t("gas") + `",
        "` + _t("petrol pump") + `",
        "` + _t("pump") + `",
        "` + _t("station") + `",
        "` + _t("fuelpump") + `"
    ],
    "name": "` + _t("fuel pump") + `",
    "shortcodes": [
        ":fuel_pump:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚨",
    "emoticons": [],
    "keywords": [
        "` + _t("beacon") + `",
        "` + _t("car") + `",
        "` + _t("light") + `",
        "` + _t("police") + `",
        "` + _t("revolving") + `"
    ],
    "name": "` + _t("police car light") + `",
    "shortcodes": [
        ":police_car_light:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚥",
    "emoticons": [],
    "keywords": [
        "` + _t("horizontal traffic lights") + `",
        "` + _t("lights") + `",
        "` + _t("signal") + `",
        "` + _t("traffic") + `",
        "` + _t("horizontal traffic light") + `",
        "` + _t("light") + `"
    ],
    "name": "` + _t("horizontal traffic light") + `",
    "shortcodes": [
        ":horizontal_traffic_light:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚦",
    "emoticons": [],
    "keywords": [
        "` + _t("lights") + `",
        "` + _t("signal") + `",
        "` + _t("traffic") + `",
        "` + _t("vertical traffic lights") + `",
        "` + _t("light") + `",
        "` + _t("vertical traffic light") + `"
    ],
    "name": "` + _t("vertical traffic light") + `",
    "shortcodes": [
        ":vertical_traffic_light:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛑",
    "emoticons": [],
    "keywords": [
        "` + _t("octagonal") + `",
        "` + _t("sign") + `",
        "` + _t("stop") + `"
    ],
    "name": "` + _t("stop sign") + `",
    "shortcodes": [
        ":stop_sign:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚧",
    "emoticons": [],
    "keywords": [
        "` + _t("barrier") + `",
        "` + _t("construction") + `"
    ],
    "name": "` + _t("construction") + `",
    "shortcodes": [
        ":construction:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⚓",
    "emoticons": [],
    "keywords": [
        "` + _t("anchor") + `",
        "` + _t("ship") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("anchor") + `",
    "shortcodes": [
        ":anchor:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛵",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("resort") + `",
        "` + _t("sailboat") + `",
        "` + _t("sea") + `",
        "` + _t("yacht") + `"
    ],
    "name": "` + _t("sailboat") + `",
    "shortcodes": [
        ":sailboat:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛶",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("canoe") + `"
    ],
    "name": "` + _t("canoe") + `",
    "shortcodes": [
        ":canoe:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚤",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("speedboat") + `"
    ],
    "name": "` + _t("speedboat") + `",
    "shortcodes": [
        ":speedboat:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛳️",
    "emoticons": [],
    "keywords": [
        "` + _t("passenger") + `",
        "` + _t("ship") + `"
    ],
    "name": "` + _t("passenger ship") + `",
    "shortcodes": [
        ":passenger_ship:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛴️",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("ferry") + `",
        "` + _t("passenger") + `"
    ],
    "name": "` + _t("ferry") + `",
    "shortcodes": [
        ":ferry:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛥️",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("motor boat") + `",
        "` + _t("motorboat") + `"
    ],
    "name": "` + _t("motor boat") + `",
    "shortcodes": [
        ":motor_boat:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚢",
    "emoticons": [],
    "keywords": [
        "` + _t("boat") + `",
        "` + _t("passenger") + `",
        "` + _t("ship") + `"
    ],
    "name": "` + _t("ship") + `",
    "shortcodes": [
        ":ship:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "✈️",
    "emoticons": [],
    "keywords": [
        "` + _t("aeroplane") + `",
        "` + _t("airplane") + `"
    ],
    "name": "` + _t("airplane") + `",
    "shortcodes": [
        ":airplane:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛩️",
    "emoticons": [],
    "keywords": [
        "` + _t("aeroplane") + `",
        "` + _t("airplane") + `",
        "` + _t("small airplane") + `"
    ],
    "name": "` + _t("small airplane") + `",
    "shortcodes": [
        ":small_airplane:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛫",
    "emoticons": [],
    "keywords": [
        "` + _t("aeroplane") + `",
        "` + _t("airplane") + `",
        "` + _t("check-in") + `",
        "` + _t("departure") + `",
        "` + _t("departures") + `",
        "` + _t("take-off") + `"
    ],
    "name": "` + _t("airplane departure") + `",
    "shortcodes": [
        ":airplane_departure:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛬",
    "emoticons": [],
    "keywords": [
        "` + _t("aeroplane") + `",
        "` + _t("airplane") + `",
        "` + _t("airplane arrival") + `",
        "` + _t("arrivals") + `",
        "` + _t("arriving") + `",
        "` + _t("landing") + `"
    ],
    "name": "` + _t("airplane arrival") + `",
    "shortcodes": [
        ":airplane_arrival:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🪂",
    "emoticons": [],
    "keywords": [
        "` + _t("hang-glide") + `",
        "` + _t("parachute") + `",
        "` + _t("parasail") + `",
        "` + _t("skydive") + `",
        "` + _t("parascend") + `"
    ],
    "name": "` + _t("parachute") + `",
    "shortcodes": [
        ":parachute:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "💺",
    "emoticons": [],
    "keywords": [
        "` + _t("chair") + `",
        "` + _t("seat") + `"
    ],
    "name": "` + _t("seat") + `",
    "shortcodes": [
        ":seat:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚁",
    "emoticons": [],
    "keywords": [
        "` + _t("helicopter") + `",
        "` + _t("vehicle") + `"
    ],
    "name": "` + _t("helicopter") + `",
    "shortcodes": [
        ":helicopter:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚟",
    "emoticons": [],
    "keywords": [
        "` + _t("cable") + `",
        "` + _t("railway") + `",
        "` + _t("suspension") + `"
    ],
    "name": "` + _t("suspension railway") + `",
    "shortcodes": [
        ":suspension_railway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚠",
    "emoticons": [],
    "keywords": [
        "` + _t("cable") + `",
        "` + _t("cableway") + `",
        "` + _t("gondola") + `",
        "` + _t("mountain") + `",
        "` + _t("mountain cableway") + `"
    ],
    "name": "` + _t("mountain cableway") + `",
    "shortcodes": [
        ":mountain_cableway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚡",
    "emoticons": [],
    "keywords": [
        "` + _t("aerial") + `",
        "` + _t("cable") + `",
        "` + _t("car") + `",
        "` + _t("gondola") + `",
        "` + _t("tramway") + `"
    ],
    "name": "` + _t("aerial tramway") + `",
    "shortcodes": [
        ":aerial_tramway:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛰️",
    "emoticons": [],
    "keywords": [
        "` + _t("satellite") + `",
        "` + _t("space") + `"
    ],
    "name": "` + _t("satellite") + `",
    "shortcodes": [
        ":satellite:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🚀",
    "emoticons": [],
    "keywords": [
        "` + _t("rocket") + `",
        "` + _t("space") + `"
    ],
    "name": "` + _t("rocket") + `",
    "shortcodes": [
        ":rocket:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛸",
    "emoticons": [],
    "keywords": [
        "` + _t("flying saucer") + `",
        "` + _t("UFO") + `"
    ],
    "name": "` + _t("flying saucer") + `",
    "shortcodes": [
        ":flying_saucer:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🛎️",
    "emoticons": [],
    "keywords": [
        "` + _t("bell") + `",
        "` + _t("hotel") + `",
        "` + _t("porter") + `",
        "` + _t("bellhop") + `"
    ],
    "name": "` + _t("bellhop bell") + `",
    "shortcodes": [
        ":bellhop_bell:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🧳",
    "emoticons": [],
    "keywords": [
        "` + _t("luggage") + `",
        "` + _t("packing") + `",
        "` + _t("travel") + `"
    ],
    "name": "` + _t("luggage") + `",
    "shortcodes": [
        ":luggage:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⌛",
    "emoticons": [],
    "keywords": [
        "` + _t("hourglass") + `",
        "` + _t("hourglass done") + `",
        "` + _t("sand") + `",
        "` + _t("timer") + `"
    ],
    "name": "` + _t("hourglass done") + `",
    "shortcodes": [
        ":hourglass_done:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⏳",
    "emoticons": [],
    "keywords": [
        "` + _t("hourglass") + `",
        "` + _t("hourglass not done") + `",
        "` + _t("sand") + `",
        "` + _t("timer") + `"
    ],
    "name": "` + _t("hourglass not done") + `",
    "shortcodes": [
        ":hourglass_not_done:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⌚",
    "emoticons": [],
    "keywords": [
        "` + _t("clock") + `",
        "` + _t("watch") + `"
    ],
    "name": "` + _t("watch") + `",
    "shortcodes": [
        ":watch:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⏰",
    "emoticons": [],
    "keywords": [
        "` + _t("alarm") + `",
        "` + _t("clock") + `"
    ],
    "name": "` + _t("alarm clock") + `",
    "shortcodes": [
        ":alarm_clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⏱️",
    "emoticons": [],
    "keywords": [
        "` + _t("clock") + `",
        "` + _t("stopwatch") + `"
    ],
    "name": "` + _t("stopwatch") + `",
    "shortcodes": [
        ":stopwatch:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⏲️",
    "emoticons": [],
    "keywords": [
        "` + _t("clock") + `",
        "` + _t("timer") + `"
    ],
    "name": "` + _t("timer clock") + `",
    "shortcodes": [
        ":timer_clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕰️",
    "emoticons": [],
    "keywords": [
        "` + _t("clock") + `",
        "` + _t("mantelpiece clock") + `"
    ],
    "name": "` + _t("mantelpiece clock") + `",
    "shortcodes": [
        ":mantelpiece_clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕛",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("12") + `",
        "` + _t("12:00") + `",
        "` + _t("clock") + `",
        "` + _t("o’clock") + `",
        "` + _t("twelve") + `"
    ],
    "name": "` + _t("twelve o’clock") + `",
    "shortcodes": [
        ":twelve_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕧",
    "emoticons": [],
    "keywords": [
        "` + _t("12") + `",
        "` + _t("12:30") + `",
        "` + _t("clock") + `",
        "` + _t("thirty") + `",
        "` + _t("twelve") + `",
        "` + _t("twelve-thirty") + `",
        "` + _t("half past twelve") + `",
        "` + _t("12.30") + `"
    ],
    "name": "` + _t("twelve-thirty") + `",
    "shortcodes": [
        ":twelve-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕐",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("1") + `",
        "` + _t("1:00") + `",
        "` + _t("clock") + `",
        "` + _t("o’clock") + `",
        "` + _t("one") + `"
    ],
    "name": "` + _t("one o’clock") + `",
    "shortcodes": [
        ":one_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕜",
    "emoticons": [],
    "keywords": [
        "` + _t("1") + `",
        "` + _t("1:30") + `",
        "` + _t("clock") + `",
        "` + _t("one") + `",
        "` + _t("one-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past one") + `",
        "` + _t("1.30") + `"
    ],
    "name": "` + _t("one-thirty") + `",
    "shortcodes": [
        ":one-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕑",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("2") + `",
        "` + _t("2:00") + `",
        "` + _t("clock") + `",
        "` + _t("o’clock") + `",
        "` + _t("two") + `"
    ],
    "name": "` + _t("two o’clock") + `",
    "shortcodes": [
        ":two_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕝",
    "emoticons": [],
    "keywords": [
        "` + _t("2") + `",
        "` + _t("2:30") + `",
        "` + _t("clock") + `",
        "` + _t("thirty") + `",
        "` + _t("two") + `",
        "` + _t("two-thirty") + `",
        "` + _t("half past two") + `",
        "` + _t("2.30") + `"
    ],
    "name": "` + _t("two-thirty") + `",
    "shortcodes": [
        ":two-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕒",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("3") + `",
        "` + _t("3:00") + `",
        "` + _t("clock") + `",
        "` + _t("o’clock") + `",
        "` + _t("three") + `"
    ],
    "name": "` + _t("three o’clock") + `",
    "shortcodes": [
        ":three_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕞",
    "emoticons": [],
    "keywords": [
        "` + _t("3") + `",
        "` + _t("3:30") + `",
        "` + _t("clock") + `",
        "` + _t("thirty") + `",
        "` + _t("three") + `",
        "` + _t("three-thirty") + `",
        "` + _t("half past three") + `",
        "` + _t("3.30") + `"
    ],
    "name": "` + _t("three-thirty") + `",
    "shortcodes": [
        ":three-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕓",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("4") + `",
        "` + _t("4:00") + `",
        "` + _t("clock") + `",
        "` + _t("four") + `",
        "` + _t("o’clock") + `"
    ],
    "name": "` + _t("four o’clock") + `",
    "shortcodes": [
        ":four_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕟",
    "emoticons": [],
    "keywords": [
        "` + _t("4") + `",
        "` + _t("4:30") + `",
        "` + _t("clock") + `",
        "` + _t("four") + `",
        "` + _t("four-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past four") + `",
        "` + _t("4.30") + `"
    ],
    "name": "` + _t("four-thirty") + `",
    "shortcodes": [
        ":four-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕔",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("5") + `",
        "` + _t("5:00") + `",
        "` + _t("clock") + `",
        "` + _t("five") + `",
        "` + _t("o’clock") + `"
    ],
    "name": "` + _t("five o’clock") + `",
    "shortcodes": [
        ":five_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕠",
    "emoticons": [],
    "keywords": [
        "` + _t("5") + `",
        "` + _t("5:30") + `",
        "` + _t("clock") + `",
        "` + _t("five") + `",
        "` + _t("five-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past five") + `",
        "` + _t("5.30") + `"
    ],
    "name": "` + _t("five-thirty") + `",
    "shortcodes": [
        ":five-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕕",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("6") + `",
        "` + _t("6:00") + `",
        "` + _t("clock") + `",
        "` + _t("o’clock") + `",
        "` + _t("six") + `"
    ],
    "name": "` + _t("six o’clock") + `",
    "shortcodes": [
        ":six_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕡",
    "emoticons": [],
    "keywords": [
        "` + _t("6") + `",
        "` + _t("6:30") + `",
        "` + _t("clock") + `",
        "` + _t("six") + `",
        "` + _t("six-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past six") + `",
        "` + _t("6.30") + `"
    ],
    "name": "` + _t("six-thirty") + `",
    "shortcodes": [
        ":six-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕖",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("7") + `",
        "` + _t("7:00") + `",
        "` + _t("clock") + `",
        "` + _t("o’clock") + `",
        "` + _t("seven") + `"
    ],
    "name": "` + _t("seven o’clock") + `",
    "shortcodes": [
        ":seven_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕢",
    "emoticons": [],
    "keywords": [
        "` + _t("7") + `",
        "` + _t("7:30") + `",
        "` + _t("clock") + `",
        "` + _t("seven") + `",
        "` + _t("seven-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past seven") + `",
        "` + _t("7.30") + `"
    ],
    "name": "` + _t("seven-thirty") + `",
    "shortcodes": [
        ":seven-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕗",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("8") + `",
        "` + _t("8:00") + `",
        "` + _t("clock") + `",
        "` + _t("eight") + `",
        "` + _t("o’clock") + `"
    ],
    "name": "` + _t("eight o’clock") + `",
    "shortcodes": [
        ":eight_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕣",
    "emoticons": [],
    "keywords": [
        "` + _t("8") + `",
        "` + _t("8:30") + `",
        "` + _t("clock") + `",
        "` + _t("eight") + `",
        "` + _t("eight-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past eight") + `",
        "` + _t("8.30") + `"
    ],
    "name": "` + _t("eight-thirty") + `",
    "shortcodes": [
        ":eight-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕘",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("9") + `",
        "` + _t("9:00") + `",
        "` + _t("clock") + `",
        "` + _t("nine") + `",
        "` + _t("o’clock") + `"
    ],
    "name": "` + _t("nine o’clock") + `",
    "shortcodes": [
        ":nine_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕤",
    "emoticons": [],
    "keywords": [
        "` + _t("9") + `",
        "` + _t("9:30") + `",
        "` + _t("clock") + `",
        "` + _t("nine") + `",
        "` + _t("nine-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past nine") + `",
        "` + _t("9.30") + `"
    ],
    "name": "` + _t("nine-thirty") + `",
    "shortcodes": [
        ":nine-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕙",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("10") + `",
        "` + _t("10:00") + `",
        "` + _t("clock") + `",
        "` + _t("o’clock") + `",
        "` + _t("ten") + `"
    ],
    "name": "` + _t("ten o’clock") + `",
    "shortcodes": [
        ":ten_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕥",
    "emoticons": [],
    "keywords": [
        "` + _t("10") + `",
        "` + _t("10:30") + `",
        "` + _t("clock") + `",
        "` + _t("ten") + `",
        "` + _t("ten-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past ten") + `",
        "` + _t("10.30") + `"
    ],
    "name": "` + _t("ten-thirty") + `",
    "shortcodes": [
        ":ten-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕚",
    "emoticons": [],
    "keywords": [
        "` + _t("00") + `",
        "` + _t("11") + `",
        "` + _t("11:00") + `",
        "` + _t("clock") + `",
        "` + _t("eleven") + `",
        "` + _t("o’clock") + `"
    ],
    "name": "` + _t("eleven o’clock") + `",
    "shortcodes": [
        ":eleven_o’clock:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🕦",
    "emoticons": [],
    "keywords": [
        "` + _t("11") + `",
        "` + _t("11:30") + `",
        "` + _t("clock") + `",
        "` + _t("eleven") + `",
        "` + _t("eleven-thirty") + `",
        "` + _t("thirty") + `",
        "` + _t("half past eleven") + `",
        "` + _t("11.30") + `"
    ],
    "name": "` + _t("eleven-thirty") + `",
    "shortcodes": [
        ":eleven-thirty:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌑",
    "emoticons": [],
    "keywords": [
        "` + _t("dark") + `",
        "` + _t("moon") + `",
        "` + _t("new moon") + `"
    ],
    "name": "` + _t("new moon") + `",
    "shortcodes": [
        ":new_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌒",
    "emoticons": [],
    "keywords": [
        "` + _t("crescent") + `",
        "` + _t("moon") + `",
        "` + _t("waxing") + `"
    ],
    "name": "` + _t("waxing crescent moon") + `",
    "shortcodes": [
        ":waxing_crescent_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌓",
    "emoticons": [],
    "keywords": [
        "` + _t("first quarter moon") + `",
        "` + _t("moon") + `",
        "` + _t("quarter") + `"
    ],
    "name": "` + _t("first quarter moon") + `",
    "shortcodes": [
        ":first_quarter_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌔",
    "emoticons": [],
    "keywords": [
        "` + _t("gibbous") + `",
        "` + _t("moon") + `",
        "` + _t("waxing") + `"
    ],
    "name": "` + _t("waxing gibbous moon") + `",
    "shortcodes": [
        ":waxing_gibbous_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌕",
    "emoticons": [],
    "keywords": [
        "` + _t("full") + `",
        "` + _t("moon") + `"
    ],
    "name": "` + _t("full moon") + `",
    "shortcodes": [
        ":full_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌖",
    "emoticons": [],
    "keywords": [
        "` + _t("gibbous") + `",
        "` + _t("moon") + `",
        "` + _t("waning") + `"
    ],
    "name": "` + _t("waning gibbous moon") + `",
    "shortcodes": [
        ":waning_gibbous_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌗",
    "emoticons": [],
    "keywords": [
        "` + _t("last quarter moon") + `",
        "` + _t("moon") + `",
        "` + _t("quarter") + `"
    ],
    "name": "` + _t("last quarter moon") + `",
    "shortcodes": [
        ":last_quarter_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌘",
    "emoticons": [],
    "keywords": [
        "` + _t("crescent") + `",
        "` + _t("moon") + `",
        "` + _t("waning") + `"
    ],
    "name": "` + _t("waning crescent moon") + `",
    "shortcodes": [
        ":waning_crescent_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌙",
    "emoticons": [],
    "keywords": [
        "` + _t("crescent") + `",
        "` + _t("moon") + `"
    ],
    "name": "` + _t("crescent moon") + `",
    "shortcodes": [
        ":crescent_moon:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌚",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("moon") + `",
        "` + _t("new moon face") + `"
    ],
    "name": "` + _t("new moon face") + `",
    "shortcodes": [
        ":new_moon_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌛",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("first quarter moon face") + `",
        "` + _t("moon") + `",
        "` + _t("quarter") + `"
    ],
    "name": "` + _t("first quarter moon face") + `",
    "shortcodes": [
        ":first_quarter_moon_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌜",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("last quarter moon face") + `",
        "` + _t("moon") + `",
        "` + _t("quarter") + `"
    ],
    "name": "` + _t("last quarter moon face") + `",
    "shortcodes": [
        ":last_quarter_moon_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌡️",
    "emoticons": [],
    "keywords": [
        "` + _t("thermometer") + `",
        "` + _t("weather") + `"
    ],
    "name": "` + _t("thermometer") + `",
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
        "` + _t("bright") + `",
        "` + _t("rays") + `",
        "` + _t("sun") + `",
        "` + _t("sunny") + `"
    ],
    "name": "` + _t("sun") + `",
    "shortcodes": [
        ":sun:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌝",
    "emoticons": [],
    "keywords": [
        "` + _t("bright") + `",
        "` + _t("face") + `",
        "` + _t("full") + `",
        "` + _t("moon") + `",
        "` + _t("full-moon face") + `"
    ],
    "name": "` + _t("full moon face") + `",
    "shortcodes": [
        ":full_moon_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌞",
    "emoticons": [],
    "keywords": [
        "` + _t("bright") + `",
        "` + _t("face") + `",
        "` + _t("sun") + `",
        "` + _t("sun with face") + `"
    ],
    "name": "` + _t("sun with face") + `",
    "shortcodes": [
        ":sun_with_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🪐",
    "emoticons": [],
    "keywords": [
        "` + _t("ringed planet") + `",
        "` + _t("saturn") + `",
        "` + _t("saturnine") + `"
    ],
    "name": "` + _t("ringed planet") + `",
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
        "` + _t("star") + `"
    ],
    "name": "` + _t("star") + `",
    "shortcodes": [
        ":star:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌟",
    "emoticons": [],
    "keywords": [
        "` + _t("glittery") + `",
        "` + _t("glow") + `",
        "` + _t("glowing star") + `",
        "` + _t("shining") + `",
        "` + _t("sparkle") + `",
        "` + _t("star") + `"
    ],
    "name": "` + _t("glowing star") + `",
    "shortcodes": [
        ":glowing_star:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌠",
    "emoticons": [],
    "keywords": [
        "` + _t("falling") + `",
        "` + _t("shooting") + `",
        "` + _t("star") + `"
    ],
    "name": "` + _t("shooting star") + `",
    "shortcodes": [
        ":shooting_star:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌌",
    "emoticons": [],
    "keywords": [
        "` + _t("Milky Way") + `",
        "` + _t("space") + `",
        "` + _t("milky way") + `",
        "` + _t("Milky") + `",
        "` + _t("Way") + `"
    ],
    "name": "` + _t("milky way") + `",
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
        "` + _t("cloud") + `",
        "` + _t("weather") + `"
    ],
    "name": "` + _t("cloud") + `",
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
        "` + _t("cloud") + `",
        "` + _t("sun") + `",
        "` + _t("sun behind cloud") + `"
    ],
    "name": "` + _t("sun behind cloud") + `",
    "shortcodes": [
        ":sun_behind_cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛈️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("cloud with lightning and rain") + `",
        "` + _t("rain") + `",
        "` + _t("thunder") + `"
    ],
    "name": "` + _t("cloud with lightning and rain") + `",
    "shortcodes": [
        ":cloud_with_lightning_and_rain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌤️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("sun") + `",
        "` + _t("sun behind small cloud") + `"
    ],
    "name": "` + _t("sun behind small cloud") + `",
    "shortcodes": [
        ":sun_behind_small_cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌥️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("sun") + `",
        "` + _t("sun behind large cloud") + `"
    ],
    "name": "` + _t("sun behind large cloud") + `",
    "shortcodes": [
        ":sun_behind_large_cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌦️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("rain") + `",
        "` + _t("sun") + `",
        "` + _t("sun behind rain cloud") + `"
    ],
    "name": "` + _t("sun behind rain cloud") + `",
    "shortcodes": [
        ":sun_behind_rain_cloud:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌧️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("cloud with rain") + `",
        "` + _t("rain") + `"
    ],
    "name": "` + _t("cloud with rain") + `",
    "shortcodes": [
        ":cloud_with_rain:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌨️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("cloud with snow") + `",
        "` + _t("cold") + `",
        "` + _t("snow") + `"
    ],
    "name": "` + _t("cloud with snow") + `",
    "shortcodes": [
        ":cloud_with_snow:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌩️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("cloud with lightning") + `",
        "` + _t("lightning") + `"
    ],
    "name": "` + _t("cloud with lightning") + `",
    "shortcodes": [
        ":cloud_with_lightning:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌪️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("tornado") + `",
        "` + _t("whirlwind") + `"
    ],
    "name": "` + _t("tornado") + `",
    "shortcodes": [
        ":tornado:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌫️",
    "emoticons": [],
    "keywords": [
        "` + _t("cloud") + `",
        "` + _t("fog") + `"
    ],
    "name": "` + _t("fog") + `",
    "shortcodes": [
        ":fog:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌬️",
    "emoticons": [],
    "keywords": [
        "` + _t("blow") + `",
        "` + _t("cloud") + `",
        "` + _t("face") + `",
        "` + _t("wind") + `"
    ],
    "name": "` + _t("wind face") + `",
    "shortcodes": [
        ":wind_face:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌀",
    "emoticons": [],
    "keywords": [
        "` + _t("cyclone") + `",
        "` + _t("dizzy") + `",
        "` + _t("hurricane") + `",
        "` + _t("twister") + `",
        "` + _t("typhoon") + `"
    ],
    "name": "` + _t("cyclone") + `",
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
        "` + _t("rain") + `",
        "` + _t("rainbow") + `"
    ],
    "name": "` + _t("rainbow") + `",
    "shortcodes": [
        ":rainbow:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌂",
    "emoticons": [],
    "keywords": [
        "` + _t("closed umbrella") + `",
        "` + _t("clothing") + `",
        "` + _t("rain") + `",
        "` + _t("umbrella") + `"
    ],
    "name": "` + _t("closed umbrella") + `",
    "shortcodes": [
        ":closed_umbrella:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☂️",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("rain") + `",
        "` + _t("umbrella") + `"
    ],
    "name": "` + _t("umbrella") + `",
    "shortcodes": [
        ":umbrella:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☔",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("drop") + `",
        "` + _t("rain") + `",
        "` + _t("umbrella") + `",
        "` + _t("umbrella with rain drops") + `"
    ],
    "name": "` + _t("umbrella with rain drops") + `",
    "shortcodes": [
        ":umbrella_with_rain_drops:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛱️",
    "emoticons": [],
    "keywords": [
        "` + _t("beach") + `",
        "` + _t("sand") + `",
        "` + _t("sun") + `",
        "` + _t("umbrella") + `",
        "` + _t("rain") + `",
        "` + _t("umbrella on ground") + `"
    ],
    "name": "` + _t("umbrella on ground") + `",
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
        "` + _t("danger") + `",
        "` + _t("electric") + `",
        "` + _t("high voltage") + `",
        "` + _t("lightning") + `",
        "` + _t("voltage") + `",
        "` + _t("zap") + `"
    ],
    "name": "` + _t("high voltage") + `",
    "shortcodes": [
        ":high_voltage:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "❄️",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("snow") + `",
        "` + _t("snowflake") + `"
    ],
    "name": "` + _t("snowflake") + `",
    "shortcodes": [
        ":snowflake:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☃️",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("snow") + `",
        "` + _t("snowman") + `"
    ],
    "name": "` + _t("snowman") + `",
    "shortcodes": [
        ":snowman:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "⛄",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("snow") + `",
        "` + _t("snowman") + `",
        "` + _t("snowman without snow") + `"
    ],
    "name": "` + _t("snowman without snow") + `",
    "shortcodes": [
        ":snowman_without_snow:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "☄️",
    "emoticons": [],
    "keywords": [
        "` + _t("comet") + `",
        "` + _t("space") + `"
    ],
    "name": "` + _t("comet") + `",
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
        "` + _t("fire") + `",
        "` + _t("flame") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("fire") + `",
    "shortcodes": [
        ":fire:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "💧",
    "emoticons": [],
    "keywords": [
        "` + _t("cold") + `",
        "` + _t("comic") + `",
        "` + _t("drop") + `",
        "` + _t("droplet") + `",
        "` + _t("sweat") + `"
    ],
    "name": "` + _t("droplet") + `",
    "shortcodes": [
        ":droplet:"
    ]
},
{
    "category": "Travel & Places",
    "codepoints": "🌊",
    "emoticons": [],
    "keywords": [
        "` + _t("ocean") + `",
        "` + _t("water") + `",
        "` + _t("wave") + `"
    ],
    "name": "` + _t("water wave") + `",
    "shortcodes": [
        ":water_wave:"
    ]
},`;

const _getEmojisData6 = () => `{
    "category": "Activities",
    "codepoints": "🎃",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("halloween") + `",
        "` + _t("jack") + `",
        "` + _t("jack-o-lantern") + `",
        "` + _t("lantern") + `",
        "` + _t("Halloween") + `",
        "` + _t("jack-o’-lantern") + `"
    ],
    "name": "` + _t("jack-o-lantern") + `",
    "shortcodes": [
        ":jack-o-lantern:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎄",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("Christmas") + `",
        "` + _t("tree") + `"
    ],
    "name": "` + _t("Christmas tree") + `",
    "shortcodes": [
        ":Christmas_tree:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎆",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("fireworks") + `"
    ],
    "name": "` + _t("fireworks") + `",
    "shortcodes": [
        ":fireworks:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎇",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("fireworks") + `",
        "` + _t("sparkle") + `",
        "` + _t("sparkler") + `"
    ],
    "name": "` + _t("sparkler") + `",
    "shortcodes": [
        ":sparkler:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧨",
    "emoticons": [],
    "keywords": [
        "` + _t("dynamite") + `",
        "` + _t("explosive") + `",
        "` + _t("firecracker") + `",
        "` + _t("fireworks") + `"
    ],
    "name": "` + _t("firecracker") + `",
    "shortcodes": [
        ":firecracker:"
    ]
},
{
    "category": "Activities",
    "codepoints": "✨",
    "emoticons": [],
    "keywords": [
        "` + _t("*") + `",
        "` + _t("sparkle") + `",
        "` + _t("sparkles") + `",
        "` + _t("star") + `"
    ],
    "name": "` + _t("sparkles") + `",
    "shortcodes": [
        ":sparkles:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎈",
    "emoticons": [],
    "keywords": [
        "` + _t("balloon") + `",
        "` + _t("celebration") + `"
    ],
    "name": "` + _t("balloon") + `",
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
        "` + _t("celebration") + `",
        "` + _t("party") + `",
        "` + _t("popper") + `",
        "` + _t("ta-da") + `",
        "` + _t("tada") + `"
    ],
    "name": "` + _t("party popper") + `",
    "shortcodes": [
        ":party_popper:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎊",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("celebration") + `",
        "` + _t("confetti") + `"
    ],
    "name": "` + _t("confetti ball") + `",
    "shortcodes": [
        ":confetti_ball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎋",
    "emoticons": [],
    "keywords": [
        "` + _t("banner") + `",
        "` + _t("celebration") + `",
        "` + _t("Japanese") + `",
        "` + _t("tanabata tree") + `",
        "` + _t("tree") + `",
        "` + _t("Tanabata tree") + `"
    ],
    "name": "` + _t("tanabata tree") + `",
    "shortcodes": [
        ":tanabata_tree:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎍",
    "emoticons": [],
    "keywords": [
        "` + _t("bamboo") + `",
        "` + _t("celebration") + `",
        "` + _t("decoration") + `",
        "` + _t("Japanese") + `",
        "` + _t("pine") + `",
        "` + _t("pine decoration") + `"
    ],
    "name": "` + _t("pine decoration") + `",
    "shortcodes": [
        ":pine_decoration:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎎",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("doll") + `",
        "` + _t("festival") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese dolls") + `"
    ],
    "name": "` + _t("Japanese dolls") + `",
    "shortcodes": [
        ":Japanese_dolls:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎏",
    "emoticons": [],
    "keywords": [
        "` + _t("carp") + `",
        "` + _t("celebration") + `",
        "` + _t("streamer") + `",
        "` + _t("carp wind sock") + `",
        "` + _t("Japanese wind socks") + `",
        "` + _t("koinobori") + `"
    ],
    "name": "` + _t("carp streamer") + `",
    "shortcodes": [
        ":carp_streamer:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎐",
    "emoticons": [],
    "keywords": [
        "` + _t("bell") + `",
        "` + _t("celebration") + `",
        "` + _t("chime") + `",
        "` + _t("wind") + `"
    ],
    "name": "` + _t("wind chime") + `",
    "shortcodes": [
        ":wind_chime:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎑",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("ceremony") + `",
        "` + _t("moon") + `",
        "` + _t("moon viewing ceremony") + `",
        "` + _t("moon-viewing ceremony") + `"
    ],
    "name": "` + _t("moon viewing ceremony") + `",
    "shortcodes": [
        ":moon_viewing_ceremony:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧧",
    "emoticons": [],
    "keywords": [
        "` + _t("gift") + `",
        "` + _t("good luck") + `",
        "` + _t("hóngbāo") + `",
        "` + _t("lai see") + `",
        "` + _t("money") + `",
        "` + _t("red envelope") + `"
    ],
    "name": "` + _t("red envelope") + `",
    "shortcodes": [
        ":red_envelope:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎀",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("ribbon") + `"
    ],
    "name": "` + _t("ribbon") + `",
    "shortcodes": [
        ":ribbon:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎁",
    "emoticons": [],
    "keywords": [
        "` + _t("box") + `",
        "` + _t("celebration") + `",
        "` + _t("gift") + `",
        "` + _t("present") + `",
        "` + _t("wrapped") + `"
    ],
    "name": "` + _t("wrapped gift") + `",
    "shortcodes": [
        ":wrapped_gift:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎗️",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("reminder") + `",
        "` + _t("ribbon") + `"
    ],
    "name": "` + _t("reminder ribbon") + `",
    "shortcodes": [
        ":reminder_ribbon:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎟️",
    "emoticons": [],
    "keywords": [
        "` + _t("admission") + `",
        "` + _t("admission tickets") + `",
        "` + _t("entry") + `",
        "` + _t("ticket") + `"
    ],
    "name": "` + _t("admission tickets") + `",
    "shortcodes": [
        ":admission_tickets:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎫",
    "emoticons": [],
    "keywords": [
        "` + _t("admission") + `",
        "` + _t("ticket") + `"
    ],
    "name": "` + _t("ticket") + `",
    "shortcodes": [
        ":ticket:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎖️",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("medal") + `",
        "` + _t("military") + `"
    ],
    "name": "` + _t("military medal") + `",
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
        "` + _t("celebration") + `",
        "` + _t("prize") + `",
        "` + _t("trophy") + `"
    ],
    "name": "` + _t("trophy") + `",
    "shortcodes": [
        ":trophy:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏅",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("medal") + `",
        "` + _t("sports") + `",
        "` + _t("sports medal") + `"
    ],
    "name": "` + _t("sports medal") + `",
    "shortcodes": [
        ":sports_medal:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥇",
    "emoticons": [],
    "keywords": [
        "` + _t("1st place medal") + `",
        "` + _t("first") + `",
        "` + _t("gold") + `",
        "` + _t("medal") + `"
    ],
    "name": "` + _t("1st place medal") + `",
    "shortcodes": [
        ":1st_place_medal:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥈",
    "emoticons": [],
    "keywords": [
        "` + _t("2nd place medal") + `",
        "` + _t("medal") + `",
        "` + _t("second") + `",
        "` + _t("silver") + `"
    ],
    "name": "` + _t("2nd place medal") + `",
    "shortcodes": [
        ":2nd_place_medal:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥉",
    "emoticons": [],
    "keywords": [
        "` + _t("3rd place medal") + `",
        "` + _t("bronze") + `",
        "` + _t("medal") + `",
        "` + _t("third") + `"
    ],
    "name": "` + _t("3rd place medal") + `",
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
        "` + _t("ball") + `",
        "` + _t("football") + `",
        "` + _t("soccer") + `"
    ],
    "name": "` + _t("soccer ball") + `",
    "shortcodes": [
        ":soccer_ball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "⚾",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("baseball") + `"
    ],
    "name": "` + _t("baseball") + `",
    "shortcodes": [
        ":baseball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥎",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("glove") + `",
        "` + _t("softball") + `",
        "` + _t("underarm") + `"
    ],
    "name": "` + _t("softball") + `",
    "shortcodes": [
        ":softball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏀",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("basketball") + `",
        "` + _t("hoop") + `"
    ],
    "name": "` + _t("basketball") + `",
    "shortcodes": [
        ":basketball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏐",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("game") + `",
        "` + _t("volleyball") + `"
    ],
    "name": "` + _t("volleyball") + `",
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
        "` + _t("american") + `",
        "` + _t("ball") + `",
        "` + _t("football") + `"
    ],
    "name": "` + _t("american football") + `",
    "shortcodes": [
        ":american_football:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏉",
    "emoticons": [],
    "keywords": [
        "` + _t("australian football") + `",
        "` + _t("rugby ball") + `",
        "` + _t("rugby league") + `",
        "` + _t("rugby union") + `",
        "` + _t("ball") + `",
        "` + _t("football") + `",
        "` + _t("rugby") + `"
    ],
    "name": "` + _t("rugby football") + `",
    "shortcodes": [
        ":rugby_football:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎾",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("racquet") + `",
        "` + _t("tennis") + `"
    ],
    "name": "` + _t("tennis") + `",
    "shortcodes": [
        ":tennis:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥏",
    "emoticons": [],
    "keywords": [
        "` + _t("flying disc") + `",
        "` + _t("frisbee") + `",
        "` + _t("ultimate") + `",
        "` + _t("Frisbee") + `"
    ],
    "name": "` + _t("flying disc") + `",
    "shortcodes": [
        ":flying_disc:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎳",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("game") + `",
        "` + _t("tenpin bowling") + `",
        "` + _t("bowling") + `"
    ],
    "name": "` + _t("bowling") + `",
    "shortcodes": [
        ":bowling:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏏",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("bat") + `",
        "` + _t("cricket game") + `",
        "` + _t("game") + `",
        "` + _t("cricket") + `",
        "` + _t("cricket match") + `"
    ],
    "name": "` + _t("cricket game") + `",
    "shortcodes": [
        ":cricket_game:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏑",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("field") + `",
        "` + _t("game") + `",
        "` + _t("hockey") + `",
        "` + _t("stick") + `"
    ],
    "name": "` + _t("field hockey") + `",
    "shortcodes": [
        ":field_hockey:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏒",
    "emoticons": [],
    "keywords": [
        "` + _t("game") + `",
        "` + _t("hockey") + `",
        "` + _t("ice") + `",
        "` + _t("puck") + `",
        "` + _t("stick") + `"
    ],
    "name": "` + _t("ice hockey") + `",
    "shortcodes": [
        ":ice_hockey:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥍",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("goal") + `",
        "` + _t("lacrosse") + `",
        "` + _t("stick") + `"
    ],
    "name": "` + _t("lacrosse") + `",
    "shortcodes": [
        ":lacrosse:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏓",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("bat") + `",
        "` + _t("game") + `",
        "` + _t("paddle") + `",
        "` + _t("ping pong") + `",
        "` + _t("table tennis") + `"
    ],
    "name": "` + _t("ping pong") + `",
    "shortcodes": [
        ":ping_pong:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🏸",
    "emoticons": [],
    "keywords": [
        "` + _t("badminton") + `",
        "` + _t("birdie") + `",
        "` + _t("game") + `",
        "` + _t("racquet") + `",
        "` + _t("shuttlecock") + `"
    ],
    "name": "` + _t("badminton") + `",
    "shortcodes": [
        ":badminton:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥊",
    "emoticons": [],
    "keywords": [
        "` + _t("boxing") + `",
        "` + _t("glove") + `"
    ],
    "name": "` + _t("boxing glove") + `",
    "shortcodes": [
        ":boxing_glove:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥋",
    "emoticons": [],
    "keywords": [
        "` + _t("judo") + `",
        "` + _t("karate") + `",
        "` + _t("martial arts") + `",
        "` + _t("martial arts uniform") + `",
        "` + _t("taekwondo") + `",
        "` + _t("uniform") + `"
    ],
    "name": "` + _t("martial arts uniform") + `",
    "shortcodes": [
        ":martial_arts_uniform:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥅",
    "emoticons": [],
    "keywords": [
        "` + _t("goal") + `",
        "` + _t("goal cage") + `",
        "` + _t("net") + `"
    ],
    "name": "` + _t("goal net") + `",
    "shortcodes": [
        ":goal_net:"
    ]
},
{
    "category": "Activities",
    "codepoints": "⛳",
    "emoticons": [],
    "keywords": [
        "` + _t("flag") + `",
        "` + _t("flag in hole") + `",
        "` + _t("golf") + `",
        "` + _t("hole") + `"
    ],
    "name": "` + _t("flag in hole") + `",
    "shortcodes": [
        ":flag_in_hole:"
    ]
},
{
    "category": "Activities",
    "codepoints": "⛸️",
    "emoticons": [],
    "keywords": [
        "` + _t("ice") + `",
        "` + _t("ice skating") + `",
        "` + _t("skate") + `"
    ],
    "name": "` + _t("ice skate") + `",
    "shortcodes": [
        ":ice_skate:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎣",
    "emoticons": [],
    "keywords": [
        "` + _t("fish") + `",
        "` + _t("fishing") + `",
        "` + _t("pole") + `",
        "` + _t("rod") + `",
        "` + _t("fishing pole") + `"
    ],
    "name": "` + _t("fishing pole") + `",
    "shortcodes": [
        ":fishing_pole:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🤿",
    "emoticons": [],
    "keywords": [
        "` + _t("diving") + `",
        "` + _t("diving mask") + `",
        "` + _t("scuba") + `",
        "` + _t("snorkeling") + `",
        "` + _t("snorkelling") + `"
    ],
    "name": "` + _t("diving mask") + `",
    "shortcodes": [
        ":diving_mask:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎽",
    "emoticons": [],
    "keywords": [
        "` + _t("athletics") + `",
        "` + _t("running") + `",
        "` + _t("sash") + `",
        "` + _t("shirt") + `"
    ],
    "name": "` + _t("running shirt") + `",
    "shortcodes": [
        ":running_shirt:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎿",
    "emoticons": [],
    "keywords": [
        "` + _t("ski") + `",
        "` + _t("skiing") + `",
        "` + _t("skis") + `",
        "` + _t("snow") + `"
    ],
    "name": "` + _t("skis") + `",
    "shortcodes": [
        ":skis:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🛷",
    "emoticons": [],
    "keywords": [
        "` + _t("sled") + `",
        "` + _t("sledge") + `",
        "` + _t("sleigh") + `"
    ],
    "name": "` + _t("sled") + `",
    "shortcodes": [
        ":sled:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🥌",
    "emoticons": [],
    "keywords": [
        "` + _t("curling") + `",
        "` + _t("game") + `",
        "` + _t("rock") + `",
        "` + _t("stone") + `",
        "` + _t("curling stone") + `",
        "` + _t("curling rock") + `"
    ],
    "name": "` + _t("curling stone") + `",
    "shortcodes": [
        ":curling_stone:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎯",
    "emoticons": [],
    "keywords": [
        "` + _t("bullseye") + `",
        "` + _t("dart") + `",
        "` + _t("direct hit") + `",
        "` + _t("game") + `",
        "` + _t("hit") + `",
        "` + _t("target") + `"
    ],
    "name": "` + _t("bullseye") + `",
    "shortcodes": [
        ":bullseye:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🪀",
    "emoticons": [],
    "keywords": [
        "` + _t("fluctuate") + `",
        "` + _t("toy") + `",
        "` + _t("yo-yo") + `"
    ],
    "name": "` + _t("yo-yo") + `",
    "shortcodes": [
        ":yo-yo:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🪁",
    "emoticons": [],
    "keywords": [
        "` + _t("fly") + `",
        "` + _t("kite") + `",
        "` + _t("soar") + `"
    ],
    "name": "` + _t("kite") + `",
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
        "` + _t("8") + `",
        "` + _t("ball") + `",
        "` + _t("billiard") + `",
        "` + _t("eight") + `",
        "` + _t("game") + `",
        "` + _t("pool 8 ball") + `"
    ],
    "name": "` + _t("pool 8 ball") + `",
    "shortcodes": [
        ":pool_8_ball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🔮",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("crystal") + `",
        "` + _t("fairy tale") + `",
        "` + _t("fantasy") + `",
        "` + _t("fortune") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("crystal ball") + `",
    "shortcodes": [
        ":crystal_ball:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧿",
    "emoticons": [],
    "keywords": [
        "` + _t("amulet") + `",
        "` + _t("charm") + `",
        "` + _t("evil-eye") + `",
        "` + _t("nazar") + `",
        "` + _t("talisman") + `",
        "` + _t("bead") + `",
        "` + _t("nazar amulet") + `",
        "` + _t("evil eye") + `"
    ],
    "name": "` + _t("nazar amulet") + `",
    "shortcodes": [
        ":nazar_amulet:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎮",
    "emoticons": [],
    "keywords": [
        "` + _t("controller") + `",
        "` + _t("game") + `",
        "` + _t("video game") + `"
    ],
    "name": "` + _t("video game") + `",
    "shortcodes": [
        ":video_game:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🕹️",
    "emoticons": [],
    "keywords": [
        "` + _t("game") + `",
        "` + _t("joystick") + `",
        "` + _t("video game") + `"
    ],
    "name": "` + _t("joystick") + `",
    "shortcodes": [
        ":joystick:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎰",
    "emoticons": [],
    "keywords": [
        "` + _t("game") + `",
        "` + _t("pokie") + `",
        "` + _t("pokies") + `",
        "` + _t("slot") + `",
        "` + _t("slot machine") + `"
    ],
    "name": "` + _t("slot machine") + `",
    "shortcodes": [
        ":slot_machine:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎲",
    "emoticons": [],
    "keywords": [
        "` + _t("dice") + `",
        "` + _t("die") + `",
        "` + _t("game") + `"
    ],
    "name": "` + _t("game die") + `",
    "shortcodes": [
        ":game_die:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧩",
    "emoticons": [],
    "keywords": [
        "` + _t("clue") + `",
        "` + _t("interlocking") + `",
        "` + _t("jigsaw") + `",
        "` + _t("piece") + `",
        "` + _t("puzzle") + `"
    ],
    "name": "` + _t("puzzle piece") + `",
    "shortcodes": [
        ":puzzle_piece:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧸",
    "emoticons": [],
    "keywords": [
        "` + _t("plaything") + `",
        "` + _t("plush") + `",
        "` + _t("stuffed") + `",
        "` + _t("teddy bear") + `",
        "` + _t("toy") + `"
    ],
    "name": "` + _t("teddy bear") + `",
    "shortcodes": [
        ":teddy_bear:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♠️",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("game") + `",
        "` + _t("spade suit") + `"
    ],
    "name": "` + _t("spade suit") + `",
    "shortcodes": [
        ":spade_suit:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♥️",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("game") + `",
        "` + _t("heart suit") + `"
    ],
    "name": "` + _t("heart suit") + `",
    "shortcodes": [
        ":heart_suit:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♦️",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("diamond suit") + `",
        "` + _t("diamonds") + `",
        "` + _t("game") + `"
    ],
    "name": "` + _t("diamond suit") + `",
    "shortcodes": [
        ":diamond_suit:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♣️",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("club suit") + `",
        "` + _t("clubs") + `",
        "` + _t("game") + `"
    ],
    "name": "` + _t("club suit") + `",
    "shortcodes": [
        ":club_suit:"
    ]
},
{
    "category": "Activities",
    "codepoints": "♟️",
    "emoticons": [],
    "keywords": [
        "` + _t("chess") + `",
        "` + _t("chess pawn") + `",
        "` + _t("dupe") + `",
        "` + _t("expendable") + `"
    ],
    "name": "` + _t("chess pawn") + `",
    "shortcodes": [
        ":chess_pawn:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🃏",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("game") + `",
        "` + _t("joker") + `",
        "` + _t("wildcard") + `"
    ],
    "name": "` + _t("joker") + `",
    "shortcodes": [
        ":joker:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🀄",
    "emoticons": [],
    "keywords": [
        "` + _t("game") + `",
        "` + _t("mahjong") + `",
        "` + _t("mahjong red dragon") + `",
        "` + _t("red") + `",
        "` + _t("Mahjong") + `",
        "` + _t("Mahjong red dragon") + `"
    ],
    "name": "` + _t("mahjong red dragon") + `",
    "shortcodes": [
        ":mahjong_red_dragon:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎴",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("flower") + `",
        "` + _t("flower playing cards") + `",
        "` + _t("game") + `",
        "` + _t("Japanese") + `",
        "` + _t("playing") + `"
    ],
    "name": "` + _t("flower playing cards") + `",
    "shortcodes": [
        ":flower_playing_cards:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎭",
    "emoticons": [],
    "keywords": [
        "` + _t("art") + `",
        "` + _t("mask") + `",
        "` + _t("performing") + `",
        "` + _t("performing arts") + `",
        "` + _t("theater") + `",
        "` + _t("theatre") + `"
    ],
    "name": "` + _t("performing arts") + `",
    "shortcodes": [
        ":performing_arts:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🖼️",
    "emoticons": [],
    "keywords": [
        "` + _t("art") + `",
        "` + _t("frame") + `",
        "` + _t("framed picture") + `",
        "` + _t("museum") + `",
        "` + _t("painting") + `",
        "` + _t("picture") + `"
    ],
    "name": "` + _t("framed picture") + `",
    "shortcodes": [
        ":framed_picture:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🎨",
    "emoticons": [],
    "keywords": [
        "` + _t("art") + `",
        "` + _t("artist palette") + `",
        "` + _t("museum") + `",
        "` + _t("painting") + `",
        "` + _t("palette") + `"
    ],
    "name": "` + _t("artist palette") + `",
    "shortcodes": [
        ":artist_palette:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧵",
    "emoticons": [],
    "keywords": [
        "` + _t("needle") + `",
        "` + _t("sewing") + `",
        "` + _t("spool") + `",
        "` + _t("string") + `",
        "` + _t("thread") + `"
    ],
    "name": "` + _t("thread") + `",
    "shortcodes": [
        ":thread:"
    ]
},
{
    "category": "Activities",
    "codepoints": "🧶",
    "emoticons": [],
    "keywords": [
        "` + _t("ball") + `",
        "` + _t("crochet") + `",
        "` + _t("knit") + `",
        "` + _t("yarn") + `"
    ],
    "name": "` + _t("yarn") + `",
    "shortcodes": [
        ":yarn:"
    ]
},`;

const _getEmojisData7 = () => `{
    "category": "Objects",
    "codepoints": "👓",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("eye") + `",
        "` + _t("eyeglasses") + `",
        "` + _t("eyewear") + `",
        "` + _t("glasses") + `"
    ],
    "name": "` + _t("glasses") + `",
    "shortcodes": [
        ":glasses:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🕶️",
    "emoticons": [],
    "keywords": [
        "` + _t("dark") + `",
        "` + _t("eye") + `",
        "` + _t("eyewear") + `",
        "` + _t("glasses") + `",
        "` + _t("sunglasses") + `",
        "` + _t("sunnies") + `"
    ],
    "name": "` + _t("sunglasses") + `",
    "shortcodes": [
        ":sunglasses:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥽",
    "emoticons": [],
    "keywords": [
        "` + _t("eye protection") + `",
        "` + _t("goggles") + `",
        "` + _t("swimming") + `",
        "` + _t("welding") + `"
    ],
    "name": "` + _t("goggles") + `",
    "shortcodes": [
        ":goggles:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥼",
    "emoticons": [],
    "keywords": [
        "` + _t("doctor") + `",
        "` + _t("experiment") + `",
        "` + _t("lab coat") + `",
        "` + _t("scientist") + `"
    ],
    "name": "` + _t("lab coat") + `",
    "shortcodes": [
        ":lab_coat:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🦺",
    "emoticons": [],
    "keywords": [
        "` + _t("emergency") + `",
        "` + _t("safety") + `",
        "` + _t("vest") + `",
        "` + _t("hi-vis") + `",
        "` + _t("high-vis") + `",
        "` + _t("jacket") + `",
        "` + _t("life jacket") + `"
    ],
    "name": "` + _t("safety vest") + `",
    "shortcodes": [
        ":safety_vest:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👔",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("necktie") + `",
        "` + _t("tie") + `"
    ],
    "name": "` + _t("necktie") + `",
    "shortcodes": [
        ":necktie:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👕",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("shirt") + `",
        "` + _t("t-shirt") + `",
        "` + _t("T-shirt") + `",
        "` + _t("tee") + `",
        "` + _t("tshirt") + `",
        "` + _t("tee-shirt") + `"
    ],
    "name": "` + _t("t-shirt") + `",
    "shortcodes": [
        ":t-shirt:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👖",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("jeans") + `",
        "` + _t("pants") + `",
        "` + _t("trousers") + `"
    ],
    "name": "` + _t("jeans") + `",
    "shortcodes": [
        ":jeans:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧣",
    "emoticons": [],
    "keywords": [
        "` + _t("neck") + `",
        "` + _t("scarf") + `"
    ],
    "name": "` + _t("scarf") + `",
    "shortcodes": [
        ":scarf:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧤",
    "emoticons": [],
    "keywords": [
        "` + _t("gloves") + `",
        "` + _t("hand") + `"
    ],
    "name": "` + _t("gloves") + `",
    "shortcodes": [
        ":gloves:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧥",
    "emoticons": [],
    "keywords": [
        "` + _t("coat") + `",
        "` + _t("jacket") + `"
    ],
    "name": "` + _t("coat") + `",
    "shortcodes": [
        ":coat:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧦",
    "emoticons": [],
    "keywords": [
        "` + _t("socks") + `",
        "` + _t("stocking") + `"
    ],
    "name": "` + _t("socks") + `",
    "shortcodes": [
        ":socks:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👗",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("dress") + `",
        "` + _t("woman’s clothes") + `"
    ],
    "name": "` + _t("dress") + `",
    "shortcodes": [
        ":dress:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👘",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("kimono") + `"
    ],
    "name": "` + _t("kimono") + `",
    "shortcodes": [
        ":kimono:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥻",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("dress") + `",
        "` + _t("sari") + `"
    ],
    "name": "` + _t("sari") + `",
    "shortcodes": [
        ":sari:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩱",
    "emoticons": [],
    "keywords": [
        "` + _t("bathing suit") + `",
        "` + _t("one-piece swimsuit") + `",
        "` + _t("swimming costume") + `"
    ],
    "name": "` + _t("one-piece swimsuit") + `",
    "shortcodes": [
        ":one-piece_swimsuit:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩲",
    "emoticons": [],
    "keywords": [
        "` + _t("bathers") + `",
        "` + _t("briefs") + `",
        "` + _t("speedos") + `",
        "` + _t("underwear") + `",
        "` + _t("bathing suit") + `",
        "` + _t("one-piece") + `",
        "` + _t("swimsuit") + `",
        "` + _t("pants") + `"
    ],
    "name": "` + _t("briefs") + `",
    "shortcodes": [
        ":briefs:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩳",
    "emoticons": [],
    "keywords": [
        "` + _t("bathing suit") + `",
        "` + _t("boardies") + `",
        "` + _t("boardshorts") + `",
        "` + _t("shorts") + `",
        "` + _t("swim shorts") + `",
        "` + _t("underwear") + `",
        "` + _t("pants") + `"
    ],
    "name": "` + _t("shorts") + `",
    "shortcodes": [
        ":shorts:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👙",
    "emoticons": [],
    "keywords": [
        "` + _t("bikini") + `",
        "` + _t("clothing") + `",
        "` + _t("swim suit") + `",
        "` + _t("two-piece") + `",
        "` + _t("swim") + `"
    ],
    "name": "` + _t("bikini") + `",
    "shortcodes": [
        ":bikini:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👚",
    "emoticons": [],
    "keywords": [
        "` + _t("blouse") + `",
        "` + _t("clothing") + `",
        "` + _t("top") + `",
        "` + _t("woman") + `",
        "` + _t("woman’s clothes") + `"
    ],
    "name": "` + _t("woman’s clothes") + `",
    "shortcodes": [
        ":woman’s_clothes:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👛",
    "emoticons": [],
    "keywords": [
        "` + _t("accessories") + `",
        "` + _t("coin") + `",
        "` + _t("purse") + `",
        "` + _t("clothing") + `"
    ],
    "name": "` + _t("purse") + `",
    "shortcodes": [
        ":purse:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👜",
    "emoticons": [],
    "keywords": [
        "` + _t("accessories") + `",
        "` + _t("bag") + `",
        "` + _t("handbag") + `",
        "` + _t("tote") + `",
        "` + _t("clothing") + `",
        "` + _t("purse") + `"
    ],
    "name": "` + _t("handbag") + `",
    "shortcodes": [
        ":handbag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👝",
    "emoticons": [],
    "keywords": [
        "` + _t("accessories") + `",
        "` + _t("bag") + `",
        "` + _t("clutch bag") + `",
        "` + _t("pouch") + `",
        "` + _t("clothing") + `"
    ],
    "name": "` + _t("clutch bag") + `",
    "shortcodes": [
        ":clutch_bag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛍️",
    "emoticons": [],
    "keywords": [
        "` + _t("bag") + `",
        "` + _t("hotel") + `",
        "` + _t("shopping") + `",
        "` + _t("shopping bags") + `"
    ],
    "name": "` + _t("shopping bags") + `",
    "shortcodes": [
        ":shopping_bags:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎒",
    "emoticons": [],
    "keywords": [
        "` + _t("backpack") + `",
        "` + _t("bag") + `",
        "` + _t("rucksack") + `",
        "` + _t("satchel") + `",
        "` + _t("school") + `"
    ],
    "name": "` + _t("backpack") + `",
    "shortcodes": [
        ":backpack:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👞",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("man") + `",
        "` + _t("man’s shoe") + `",
        "` + _t("shoe") + `"
    ],
    "name": "` + _t("man’s shoe") + `",
    "shortcodes": [
        ":man’s_shoe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👟",
    "emoticons": [],
    "keywords": [
        "` + _t("athletic") + `",
        "` + _t("clothing") + `",
        "` + _t("runners") + `",
        "` + _t("running shoe") + `",
        "` + _t("shoe") + `",
        "` + _t("sneaker") + `",
        "` + _t("trainer") + `"
    ],
    "name": "` + _t("running shoe") + `",
    "shortcodes": [
        ":running_shoe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥾",
    "emoticons": [],
    "keywords": [
        "` + _t("backpacking") + `",
        "` + _t("boot") + `",
        "` + _t("camping") + `",
        "` + _t("hiking") + `"
    ],
    "name": "` + _t("hiking boot") + `",
    "shortcodes": [
        ":hiking_boot:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥿",
    "emoticons": [],
    "keywords": [
        "` + _t("ballet flat") + `",
        "` + _t("flat shoe") + `",
        "` + _t("slip-on") + `",
        "` + _t("slipper") + `",
        "` + _t("pump") + `"
    ],
    "name": "` + _t("flat shoe") + `",
    "shortcodes": [
        ":flat_shoe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👠",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("heel") + `",
        "` + _t("high-heeled shoe") + `",
        "` + _t("shoe") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("high-heeled shoe") + `",
    "shortcodes": [
        ":high-heeled_shoe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👡",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("sandal") + `",
        "` + _t("shoe") + `",
        "` + _t("woman") + `",
        "` + _t("woman’s sandal") + `"
    ],
    "name": "` + _t("woman’s sandal") + `",
    "shortcodes": [
        ":woman’s_sandal:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩰",
    "emoticons": [],
    "keywords": [
        "` + _t("ballet") + `",
        "` + _t("ballet shoes") + `",
        "` + _t("dance") + `"
    ],
    "name": "` + _t("ballet shoes") + `",
    "shortcodes": [
        ":ballet_shoes:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👢",
    "emoticons": [],
    "keywords": [
        "` + _t("boot") + `",
        "` + _t("clothing") + `",
        "` + _t("shoe") + `",
        "` + _t("woman") + `",
        "` + _t("woman’s boot") + `"
    ],
    "name": "` + _t("woman’s boot") + `",
    "shortcodes": [
        ":woman’s_boot:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👑",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("crown") + `",
        "` + _t("king") + `",
        "` + _t("queen") + `"
    ],
    "name": "` + _t("crown") + `",
    "shortcodes": [
        ":crown:"
    ]
},
{
    "category": "Objects",
    "codepoints": "👒",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("hat") + `",
        "` + _t("woman") + `",
        "` + _t("woman’s hat") + `"
    ],
    "name": "` + _t("woman’s hat") + `",
    "shortcodes": [
        ":woman’s_hat:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎩",
    "emoticons": [],
    "keywords": [
        "` + _t("clothing") + `",
        "` + _t("hat") + `",
        "` + _t("top") + `",
        "` + _t("tophat") + `"
    ],
    "name": "` + _t("top hat") + `",
    "shortcodes": [
        ":top_hat:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎓",
    "emoticons": [],
    "keywords": [
        "` + _t("cap") + `",
        "` + _t("celebration") + `",
        "` + _t("clothing") + `",
        "` + _t("graduation") + `",
        "` + _t("hat") + `"
    ],
    "name": "` + _t("graduation cap") + `",
    "shortcodes": [
        ":graduation_cap:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧢",
    "emoticons": [],
    "keywords": [
        "` + _t("baseball cap") + `",
        "` + _t("billed cap") + `"
    ],
    "name": "` + _t("billed cap") + `",
    "shortcodes": [
        ":billed_cap:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⛑️",
    "emoticons": [],
    "keywords": [
        "` + _t("aid") + `",
        "` + _t("cross") + `",
        "` + _t("face") + `",
        "` + _t("hat") + `",
        "` + _t("helmet") + `",
        "` + _t("rescue worker’s helmet") + `"
    ],
    "name": "` + _t("rescue worker’s helmet") + `",
    "shortcodes": [
        ":rescue_worker’s_helmet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📿",
    "emoticons": [],
    "keywords": [
        "` + _t("beads") + `",
        "` + _t("clothing") + `",
        "` + _t("necklace") + `",
        "` + _t("prayer") + `",
        "` + _t("religion") + `"
    ],
    "name": "` + _t("prayer beads") + `",
    "shortcodes": [
        ":prayer_beads:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💄",
    "emoticons": [],
    "keywords": [
        "` + _t("cosmetics") + `",
        "` + _t("lipstick") + `",
        "` + _t("make-up") + `",
        "` + _t("makeup") + `"
    ],
    "name": "` + _t("lipstick") + `",
    "shortcodes": [
        ":lipstick:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💍",
    "emoticons": [],
    "keywords": [
        "` + _t("diamond") + `",
        "` + _t("ring") + `"
    ],
    "name": "` + _t("ring") + `",
    "shortcodes": [
        ":ring:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💎",
    "emoticons": [],
    "keywords": [
        "` + _t("diamond") + `",
        "` + _t("gem") + `",
        "` + _t("gem stone") + `",
        "` + _t("jewel") + `",
        "` + _t("gemstone") + `"
    ],
    "name": "` + _t("gem stone") + `",
    "shortcodes": [
        ":gem_stone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔇",
    "emoticons": [],
    "keywords": [
        "` + _t("mute") + `",
        "` + _t("muted speaker") + `",
        "` + _t("quiet") + `",
        "` + _t("silent") + `",
        "` + _t("speaker") + `"
    ],
    "name": "` + _t("muted speaker") + `",
    "shortcodes": [
        ":muted_speaker:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔈",
    "emoticons": [],
    "keywords": [
        "` + _t("low") + `",
        "` + _t("quiet") + `",
        "` + _t("soft") + `",
        "` + _t("speaker") + `",
        "` + _t("volume") + `",
        "` + _t("speaker low volume") + `"
    ],
    "name": "` + _t("speaker low volume") + `",
    "shortcodes": [
        ":speaker_low_volume:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔉",
    "emoticons": [],
    "keywords": [
        "` + _t("medium") + `",
        "` + _t("speaker medium volume") + `"
    ],
    "name": "` + _t("speaker medium volume") + `",
    "shortcodes": [
        ":speaker_medium_volume:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔊",
    "emoticons": [],
    "keywords": [
        "` + _t("loud") + `",
        "` + _t("speaker high volume") + `"
    ],
    "name": "` + _t("speaker high volume") + `",
    "shortcodes": [
        ":speaker_high_volume:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📢",
    "emoticons": [],
    "keywords": [
        "` + _t("loud") + `",
        "` + _t("loudspeaker") + `",
        "` + _t("public address") + `"
    ],
    "name": "` + _t("loudspeaker") + `",
    "shortcodes": [
        ":loudspeaker:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📣",
    "emoticons": [],
    "keywords": [
        "` + _t("cheering") + `",
        "` + _t("megaphone") + `"
    ],
    "name": "` + _t("megaphone") + `",
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
        "` + _t("horn") + `",
        "` + _t("post") + `",
        "` + _t("postal") + `"
    ],
    "name": "` + _t("postal horn") + `",
    "shortcodes": [
        ":postal_horn:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔔",
    "emoticons": [],
    "keywords": [
        "` + _t("bell") + `"
    ],
    "name": "` + _t("bell") + `",
    "shortcodes": [
        ":bell:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔕",
    "emoticons": [],
    "keywords": [
        "` + _t("bell") + `",
        "` + _t("bell with slash") + `",
        "` + _t("forbidden") + `",
        "` + _t("mute") + `",
        "` + _t("quiet") + `",
        "` + _t("silent") + `"
    ],
    "name": "` + _t("bell with slash") + `",
    "shortcodes": [
        ":bell_with_slash:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎼",
    "emoticons": [],
    "keywords": [
        "` + _t("music") + `",
        "` + _t("musical score") + `",
        "` + _t("score") + `"
    ],
    "name": "` + _t("musical score") + `",
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
        "` + _t("music") + `",
        "` + _t("musical note") + `",
        "` + _t("note") + `"
    ],
    "name": "` + _t("musical note") + `",
    "shortcodes": [
        ":musical_note:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎶",
    "emoticons": [],
    "keywords": [
        "` + _t("music") + `",
        "` + _t("musical notes") + `",
        "` + _t("note") + `",
        "` + _t("notes") + `"
    ],
    "name": "` + _t("musical notes") + `",
    "shortcodes": [
        ":musical_notes:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎙️",
    "emoticons": [],
    "keywords": [
        "` + _t("mic") + `",
        "` + _t("microphone") + `",
        "` + _t("music") + `",
        "` + _t("studio") + `"
    ],
    "name": "` + _t("studio microphone") + `",
    "shortcodes": [
        ":studio_microphone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎚️",
    "emoticons": [],
    "keywords": [
        "` + _t("level") + `",
        "` + _t("music") + `",
        "` + _t("slider") + `"
    ],
    "name": "` + _t("level slider") + `",
    "shortcodes": [
        ":level_slider:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎛️",
    "emoticons": [],
    "keywords": [
        "` + _t("control") + `",
        "` + _t("knobs") + `",
        "` + _t("music") + `"
    ],
    "name": "` + _t("control knobs") + `",
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
        "` + _t("karaoke") + `",
        "` + _t("mic") + `",
        "` + _t("microphone") + `"
    ],
    "name": "` + _t("microphone") + `",
    "shortcodes": [
        ":microphone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎧",
    "emoticons": [],
    "keywords": [
        "` + _t("earbud") + `",
        "` + _t("headphone") + `"
    ],
    "name": "` + _t("headphone") + `",
    "shortcodes": [
        ":headphone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📻",
    "emoticons": [],
    "keywords": [
        "` + _t("AM") + `",
        "` + _t("FM") + `",
        "` + _t("radio") + `",
        "` + _t("wireless") + `",
        "` + _t("video") + `"
    ],
    "name": "` + _t("radio") + `",
    "shortcodes": [
        ":radio:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎷",
    "emoticons": [],
    "keywords": [
        "` + _t("instrument") + `",
        "` + _t("music") + `",
        "` + _t("sax") + `",
        "` + _t("saxophone") + `"
    ],
    "name": "` + _t("saxophone") + `",
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
        "` + _t("guitar") + `",
        "` + _t("instrument") + `",
        "` + _t("music") + `"
    ],
    "name": "` + _t("guitar") + `",
    "shortcodes": [
        ":guitar:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎹",
    "emoticons": [],
    "keywords": [
        "` + _t("instrument") + `",
        "` + _t("keyboard") + `",
        "` + _t("music") + `",
        "` + _t("musical keyboard") + `",
        "` + _t("organ") + `",
        "` + _t("piano") + `"
    ],
    "name": "` + _t("musical keyboard") + `",
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
        "` + _t("instrument") + `",
        "` + _t("music") + `",
        "` + _t("trumpet") + `"
    ],
    "name": "` + _t("trumpet") + `",
    "shortcodes": [
        ":trumpet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎻",
    "emoticons": [],
    "keywords": [
        "` + _t("instrument") + `",
        "` + _t("music") + `",
        "` + _t("violin") + `"
    ],
    "name": "` + _t("violin") + `",
    "shortcodes": [
        ":violin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪕",
    "emoticons": [],
    "keywords": [
        "` + _t("banjo") + `",
        "` + _t("music") + `",
        "` + _t("stringed") + `"
    ],
    "name": "` + _t("banjo") + `",
    "shortcodes": [
        ":banjo:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🥁",
    "emoticons": [],
    "keywords": [
        "` + _t("drum") + `",
        "` + _t("drumsticks") + `",
        "` + _t("music") + `",
        "` + _t("percussions") + `"
    ],
    "name": "` + _t("drum") + `",
    "shortcodes": [
        ":drum:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📱",
    "emoticons": [],
    "keywords": [
        "` + _t("cell") + `",
        "` + _t("mobile") + `",
        "` + _t("phone") + `",
        "` + _t("telephone") + `"
    ],
    "name": "` + _t("mobile phone") + `",
    "shortcodes": [
        ":mobile_phone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📲",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("cell") + `",
        "` + _t("mobile") + `",
        "` + _t("mobile phone with arrow") + `",
        "` + _t("phone") + `",
        "` + _t("receive") + `"
    ],
    "name": "` + _t("mobile phone with arrow") + `",
    "shortcodes": [
        ":mobile_phone_with_arrow:"
    ]
},
{
    "category": "Objects",
    "codepoints": "☎️",
    "emoticons": [],
    "keywords": [
        "` + _t("landline") + `",
        "` + _t("phone") + `",
        "` + _t("telephone") + `"
    ],
    "name": "` + _t("telephone") + `",
    "shortcodes": [
        ":telephone:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📞",
    "emoticons": [],
    "keywords": [
        "` + _t("phone") + `",
        "` + _t("receiver") + `",
        "` + _t("telephone") + `"
    ],
    "name": "` + _t("telephone receiver") + `",
    "shortcodes": [
        ":telephone_receiver:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📟",
    "emoticons": [],
    "keywords": [
        "` + _t("pager") + `"
    ],
    "name": "` + _t("pager") + `",
    "shortcodes": [
        ":pager:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📠",
    "emoticons": [],
    "keywords": [
        "` + _t("fax") + `",
        "` + _t("fax machine") + `"
    ],
    "name": "` + _t("fax machine") + `",
    "shortcodes": [
        ":fax_machine:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔋",
    "emoticons": [],
    "keywords": [
        "` + _t("battery") + `"
    ],
    "name": "` + _t("battery") + `",
    "shortcodes": [
        ":battery:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔌",
    "emoticons": [],
    "keywords": [
        "` + _t("electric") + `",
        "` + _t("electricity") + `",
        "` + _t("plug") + `"
    ],
    "name": "` + _t("electric plug") + `",
    "shortcodes": [
        ":electric_plug:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💻",
    "emoticons": [],
    "keywords": [
        "` + _t("computer") + `",
        "` + _t("laptop") + `",
        "` + _t("PC") + `",
        "` + _t("personal") + `",
        "` + _t("pc") + `"
    ],
    "name": "` + _t("laptop") + `",
    "shortcodes": [
        ":laptop:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖥️",
    "emoticons": [],
    "keywords": [
        "` + _t("computer") + `",
        "` + _t("desktop") + `"
    ],
    "name": "` + _t("desktop computer") + `",
    "shortcodes": [
        ":desktop_computer:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖨️",
    "emoticons": [],
    "keywords": [
        "` + _t("computer") + `",
        "` + _t("printer") + `"
    ],
    "name": "` + _t("printer") + `",
    "shortcodes": [
        ":printer:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⌨️",
    "emoticons": [],
    "keywords": [
        "` + _t("computer") + `",
        "` + _t("keyboard") + `"
    ],
    "name": "` + _t("keyboard") + `",
    "shortcodes": [
        ":keyboard:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖱️",
    "emoticons": [],
    "keywords": [
        "` + _t("computer") + `",
        "` + _t("computer mouse") + `"
    ],
    "name": "` + _t("computer mouse") + `",
    "shortcodes": [
        ":computer_mouse:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖲️",
    "emoticons": [],
    "keywords": [
        "` + _t("computer") + `",
        "` + _t("trackball") + `"
    ],
    "name": "` + _t("trackball") + `",
    "shortcodes": [
        ":trackball:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💽",
    "emoticons": [],
    "keywords": [
        "` + _t("computer") + `",
        "` + _t("disk") + `",
        "` + _t("minidisk") + `",
        "` + _t("optical") + `"
    ],
    "name": "` + _t("computer disk") + `",
    "shortcodes": [
        ":computer_disk:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💾",
    "emoticons": [],
    "keywords": [
        "` + _t("computer") + `",
        "` + _t("disk") + `",
        "` + _t("diskette") + `",
        "` + _t("floppy") + `"
    ],
    "name": "` + _t("floppy disk") + `",
    "shortcodes": [
        ":floppy_disk:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💿",
    "emoticons": [],
    "keywords": [
        "` + _t("CD") + `",
        "` + _t("computer") + `",
        "` + _t("disk") + `",
        "` + _t("optical") + `"
    ],
    "name": "` + _t("optical disk") + `",
    "shortcodes": [
        ":optical_disk:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📀",
    "emoticons": [],
    "keywords": [
        "` + _t("blu-ray") + `",
        "` + _t("computer") + `",
        "` + _t("disk") + `",
        "` + _t("dvd") + `",
        "` + _t("DVD") + `",
        "` + _t("optical") + `",
        "` + _t("Blu-ray") + `"
    ],
    "name": "` + _t("dvd") + `",
    "shortcodes": [
        ":dvd:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧮",
    "emoticons": [],
    "keywords": [
        "` + _t("abacus") + `",
        "` + _t("calculation") + `"
    ],
    "name": "` + _t("abacus") + `",
    "shortcodes": [
        ":abacus:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎥",
    "emoticons": [],
    "keywords": [
        "` + _t("camera") + `",
        "` + _t("cinema") + `",
        "` + _t("movie") + `"
    ],
    "name": "` + _t("movie camera") + `",
    "shortcodes": [
        ":movie_camera:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🎞️",
    "emoticons": [],
    "keywords": [
        "` + _t("cinema") + `",
        "` + _t("film") + `",
        "` + _t("frames") + `",
        "` + _t("movie") + `"
    ],
    "name": "` + _t("film frames") + `",
    "shortcodes": [
        ":film_frames:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📽️",
    "emoticons": [],
    "keywords": [
        "` + _t("cinema") + `",
        "` + _t("film") + `",
        "` + _t("movie") + `",
        "` + _t("projector") + `",
        "` + _t("video") + `"
    ],
    "name": "` + _t("film projector") + `",
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
        "` + _t("clapper") + `",
        "` + _t("clapper board") + `",
        "` + _t("clapperboard") + `",
        "` + _t("film") + `",
        "` + _t("movie") + `"
    ],
    "name": "` + _t("clapper board") + `",
    "shortcodes": [
        ":clapper_board:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📺",
    "emoticons": [],
    "keywords": [
        "` + _t("television") + `",
        "` + _t("TV") + `",
        "` + _t("video") + `",
        "` + _t("tv") + `"
    ],
    "name": "` + _t("television") + `",
    "shortcodes": [
        ":television:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📷",
    "emoticons": [],
    "keywords": [
        "` + _t("camera") + `",
        "` + _t("video") + `"
    ],
    "name": "` + _t("camera") + `",
    "shortcodes": [
        ":camera:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📸",
    "emoticons": [],
    "keywords": [
        "` + _t("camera") + `",
        "` + _t("camera with flash") + `",
        "` + _t("flash") + `",
        "` + _t("video") + `"
    ],
    "name": "` + _t("camera with flash") + `",
    "shortcodes": [
        ":camera_with_flash:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📹",
    "emoticons": [],
    "keywords": [
        "` + _t("camera") + `",
        "` + _t("video") + `"
    ],
    "name": "` + _t("video camera") + `",
    "shortcodes": [
        ":video_camera:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📼",
    "emoticons": [],
    "keywords": [
        "` + _t("tape") + `",
        "` + _t("VHS") + `",
        "` + _t("video") + `",
        "` + _t("videocassette") + `",
        "` + _t("vhs") + `"
    ],
    "name": "` + _t("videocassette") + `",
    "shortcodes": [
        ":videocassette:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔍",
    "emoticons": [],
    "keywords": [
        "` + _t("glass") + `",
        "` + _t("magnifying") + `",
        "` + _t("magnifying glass tilted left") + `",
        "` + _t("search") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("magnifying glass tilted left") + `",
    "shortcodes": [
        ":magnifying_glass_tilted_left:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔎",
    "emoticons": [],
    "keywords": [
        "` + _t("glass") + `",
        "` + _t("magnifying") + `",
        "` + _t("magnifying glass tilted right") + `",
        "` + _t("search") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("magnifying glass tilted right") + `",
    "shortcodes": [
        ":magnifying_glass_tilted_right:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🕯️",
    "emoticons": [],
    "keywords": [
        "` + _t("candle") + `",
        "` + _t("light") + `"
    ],
    "name": "` + _t("candle") + `",
    "shortcodes": [
        ":candle:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💡",
    "emoticons": [],
    "keywords": [
        "` + _t("bulb") + `",
        "` + _t("comic") + `",
        "` + _t("electric") + `",
        "` + _t("globe") + `",
        "` + _t("idea") + `",
        "` + _t("light") + `"
    ],
    "name": "` + _t("light bulb") + `",
    "shortcodes": [
        ":light_bulb:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔦",
    "emoticons": [],
    "keywords": [
        "` + _t("electric") + `",
        "` + _t("flashlight") + `",
        "` + _t("light") + `",
        "` + _t("tool") + `",
        "` + _t("torch") + `"
    ],
    "name": "` + _t("flashlight") + `",
    "shortcodes": [
        ":flashlight:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🏮",
    "emoticons": [],
    "keywords": [
        "` + _t("bar") + `",
        "` + _t("lantern") + `",
        "` + _t("light") + `",
        "` + _t("red") + `",
        "` + _t("red paper lantern") + `"
    ],
    "name": "` + _t("red paper lantern") + `",
    "shortcodes": [
        ":red_paper_lantern:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪔",
    "emoticons": [],
    "keywords": [
        "` + _t("diya") + `",
        "` + _t("lamp") + `",
        "` + _t("oil") + `"
    ],
    "name": "` + _t("diya lamp") + `",
    "shortcodes": [
        ":diya_lamp:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📔",
    "emoticons": [],
    "keywords": [
        "` + _t("book") + `",
        "` + _t("cover") + `",
        "` + _t("decorated") + `",
        "` + _t("notebook") + `",
        "` + _t("notebook with decorative cover") + `"
    ],
    "name": "` + _t("notebook with decorative cover") + `",
    "shortcodes": [
        ":notebook_with_decorative_cover:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📕",
    "emoticons": [],
    "keywords": [
        "` + _t("book") + `",
        "` + _t("closed") + `"
    ],
    "name": "` + _t("closed book") + `",
    "shortcodes": [
        ":closed_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📖",
    "emoticons": [],
    "keywords": [
        "` + _t("book") + `",
        "` + _t("open") + `"
    ],
    "name": "` + _t("open book") + `",
    "shortcodes": [
        ":open_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📗",
    "emoticons": [],
    "keywords": [
        "` + _t("book") + `",
        "` + _t("green") + `"
    ],
    "name": "` + _t("green book") + `",
    "shortcodes": [
        ":green_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📘",
    "emoticons": [],
    "keywords": [
        "` + _t("blue") + `",
        "` + _t("book") + `"
    ],
    "name": "` + _t("blue book") + `",
    "shortcodes": [
        ":blue_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📙",
    "emoticons": [],
    "keywords": [
        "` + _t("book") + `",
        "` + _t("orange") + `"
    ],
    "name": "` + _t("orange book") + `",
    "shortcodes": [
        ":orange_book:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📚",
    "emoticons": [],
    "keywords": [
        "` + _t("book") + `",
        "` + _t("books") + `"
    ],
    "name": "` + _t("books") + `",
    "shortcodes": [
        ":books:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📓",
    "emoticons": [],
    "keywords": [
        "` + _t("notebook") + `"
    ],
    "name": "` + _t("notebook") + `",
    "shortcodes": [
        ":notebook:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📒",
    "emoticons": [],
    "keywords": [
        "` + _t("ledger") + `",
        "` + _t("notebook") + `"
    ],
    "name": "` + _t("ledger") + `",
    "shortcodes": [
        ":ledger:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📃",
    "emoticons": [],
    "keywords": [
        "` + _t("curl") + `",
        "` + _t("document") + `",
        "` + _t("page") + `",
        "` + _t("page with curl") + `"
    ],
    "name": "` + _t("page with curl") + `",
    "shortcodes": [
        ":page_with_curl:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📜",
    "emoticons": [],
    "keywords": [
        "` + _t("paper") + `",
        "` + _t("scroll") + `"
    ],
    "name": "` + _t("scroll") + `",
    "shortcodes": [
        ":scroll:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📄",
    "emoticons": [],
    "keywords": [
        "` + _t("document") + `",
        "` + _t("page") + `",
        "` + _t("page facing up") + `"
    ],
    "name": "` + _t("page facing up") + `",
    "shortcodes": [
        ":page_facing_up:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📰",
    "emoticons": [],
    "keywords": [
        "` + _t("news") + `",
        "` + _t("newspaper") + `",
        "` + _t("paper") + `"
    ],
    "name": "` + _t("newspaper") + `",
    "shortcodes": [
        ":newspaper:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗞️",
    "emoticons": [],
    "keywords": [
        "` + _t("news") + `",
        "` + _t("newspaper") + `",
        "` + _t("paper") + `",
        "` + _t("rolled") + `",
        "` + _t("rolled-up newspaper") + `"
    ],
    "name": "` + _t("rolled-up newspaper") + `",
    "shortcodes": [
        ":rolled-up_newspaper:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📑",
    "emoticons": [],
    "keywords": [
        "` + _t("bookmark") + `",
        "` + _t("mark") + `",
        "` + _t("marker") + `",
        "` + _t("tabs") + `"
    ],
    "name": "` + _t("bookmark tabs") + `",
    "shortcodes": [
        ":bookmark_tabs:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔖",
    "emoticons": [],
    "keywords": [
        "` + _t("bookmark") + `",
        "` + _t("mark") + `"
    ],
    "name": "` + _t("bookmark") + `",
    "shortcodes": [
        ":bookmark:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🏷️",
    "emoticons": [],
    "keywords": [
        "` + _t("label") + `"
    ],
    "name": "` + _t("label") + `",
    "shortcodes": [
        ":label:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💰",
    "emoticons": [],
    "keywords": [
        "` + _t("bag") + `",
        "` + _t("dollar") + `",
        "` + _t("money") + `",
        "` + _t("moneybag") + `"
    ],
    "name": "` + _t("money bag") + `",
    "shortcodes": [
        ":money_bag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💴",
    "emoticons": [],
    "keywords": [
        "` + _t("banknote") + `",
        "` + _t("bill") + `",
        "` + _t("currency") + `",
        "` + _t("money") + `",
        "` + _t("note") + `",
        "` + _t("yen") + `"
    ],
    "name": "` + _t("yen banknote") + `",
    "shortcodes": [
        ":yen_banknote:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💵",
    "emoticons": [],
    "keywords": [
        "` + _t("banknote") + `",
        "` + _t("bill") + `",
        "` + _t("currency") + `",
        "` + _t("dollar") + `",
        "` + _t("money") + `",
        "` + _t("note") + `"
    ],
    "name": "` + _t("dollar banknote") + `",
    "shortcodes": [
        ":dollar_banknote:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💶",
    "emoticons": [],
    "keywords": [
        "` + _t("banknote") + `",
        "` + _t("bill") + `",
        "` + _t("currency") + `",
        "` + _t("euro") + `",
        "` + _t("money") + `",
        "` + _t("note") + `"
    ],
    "name": "` + _t("euro banknote") + `",
    "shortcodes": [
        ":euro_banknote:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💷",
    "emoticons": [],
    "keywords": [
        "` + _t("banknote") + `",
        "` + _t("bill") + `",
        "` + _t("currency") + `",
        "` + _t("money") + `",
        "` + _t("note") + `",
        "` + _t("pound") + `",
        "` + _t("sterling") + `"
    ],
    "name": "` + _t("pound banknote") + `",
    "shortcodes": [
        ":pound_banknote:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💸",
    "emoticons": [],
    "keywords": [
        "` + _t("banknote") + `",
        "` + _t("bill") + `",
        "` + _t("fly") + `",
        "` + _t("money") + `",
        "` + _t("money with wings") + `",
        "` + _t("wings") + `"
    ],
    "name": "` + _t("money with wings") + `",
    "shortcodes": [
        ":money_with_wings:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💳",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("credit") + `",
        "` + _t("money") + `"
    ],
    "name": "` + _t("credit card") + `",
    "shortcodes": [
        ":credit_card:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧾",
    "emoticons": [],
    "keywords": [
        "` + _t("accounting") + `",
        "` + _t("bookkeeping") + `",
        "` + _t("evidence") + `",
        "` + _t("proof") + `",
        "` + _t("receipt") + `"
    ],
    "name": "` + _t("receipt") + `",
    "shortcodes": [
        ":receipt:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💹",
    "emoticons": [],
    "keywords": [
        "` + _t("chart") + `",
        "` + _t("chart increasing with yen") + `",
        "` + _t("graph") + `",
        "` + _t("graph increasing with yen") + `",
        "` + _t("growth") + `",
        "` + _t("money") + `",
        "` + _t("yen") + `"
    ],
    "name": "` + _t("chart increasing with yen") + `",
    "shortcodes": [
        ":chart_increasing_with_yen:"
    ]
},
{
    "category": "Objects",
    "codepoints": "✉️",
    "emoticons": [],
    "keywords": [
        "` + _t("email") + `",
        "` + _t("envelope") + `",
        "` + _t("letter") + `",
        "` + _t("e-mail") + `"
    ],
    "name": "` + _t("envelope") + `",
    "shortcodes": [
        ":envelope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📧",
    "emoticons": [],
    "keywords": [
        "` + _t("e-mail") + `",
        "` + _t("email") + `",
        "` + _t("letter") + `",
        "` + _t("mail") + `"
    ],
    "name": "` + _t("e-mail") + `",
    "shortcodes": [
        ":e-mail:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📨",
    "emoticons": [],
    "keywords": [
        "` + _t("e-mail") + `",
        "` + _t("email") + `",
        "` + _t("envelope") + `",
        "` + _t("incoming") + `",
        "` + _t("letter") + `",
        "` + _t("receive") + `"
    ],
    "name": "` + _t("incoming envelope") + `",
    "shortcodes": [
        ":incoming_envelope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📩",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("e-mail") + `",
        "` + _t("email") + `",
        "` + _t("envelope") + `",
        "` + _t("envelope with arrow") + `",
        "` + _t("outgoing") + `"
    ],
    "name": "` + _t("envelope with arrow") + `",
    "shortcodes": [
        ":envelope_with_arrow:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📤",
    "emoticons": [],
    "keywords": [
        "` + _t("box") + `",
        "` + _t("letter") + `",
        "` + _t("mail") + `",
        "` + _t("out tray") + `",
        "` + _t("outbox") + `",
        "` + _t("sent") + `",
        "` + _t("tray") + `"
    ],
    "name": "` + _t("outbox tray") + `",
    "shortcodes": [
        ":outbox_tray:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📥",
    "emoticons": [],
    "keywords": [
        "` + _t("box") + `",
        "` + _t("in tray") + `",
        "` + _t("inbox") + `",
        "` + _t("letter") + `",
        "` + _t("mail") + `",
        "` + _t("receive") + `",
        "` + _t("tray") + `"
    ],
    "name": "` + _t("inbox tray") + `",
    "shortcodes": [
        ":inbox_tray:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📦",
    "emoticons": [],
    "keywords": [
        "` + _t("box") + `",
        "` + _t("package") + `",
        "` + _t("parcel") + `"
    ],
    "name": "` + _t("package") + `",
    "shortcodes": [
        ":package:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📫",
    "emoticons": [],
    "keywords": [
        "` + _t("closed") + `",
        "` + _t("closed letterbox with raised flag") + `",
        "` + _t("mail") + `",
        "` + _t("mailbox") + `",
        "` + _t("postbox") + `",
        "` + _t("closed mailbox with raised flag") + `",
        "` + _t("closed postbox with raised flag") + `",
        "` + _t("letterbox") + `",
        "` + _t("post") + `",
        "` + _t("post box") + `"
    ],
    "name": "` + _t("closed mailbox with raised flag") + `",
    "shortcodes": [
        ":closed_mailbox_with_raised_flag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📪",
    "emoticons": [],
    "keywords": [
        "` + _t("closed") + `",
        "` + _t("closed letterbox with lowered flag") + `",
        "` + _t("lowered") + `",
        "` + _t("mail") + `",
        "` + _t("mailbox") + `",
        "` + _t("postbox") + `",
        "` + _t("closed mailbox with lowered flag") + `",
        "` + _t("closed postbox with lowered flag") + `",
        "` + _t("letterbox") + `",
        "` + _t("post box") + `",
        "` + _t("post") + `"
    ],
    "name": "` + _t("closed mailbox with lowered flag") + `",
    "shortcodes": [
        ":closed_mailbox_with_lowered_flag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📬",
    "emoticons": [],
    "keywords": [
        "` + _t("mail") + `",
        "` + _t("mailbox") + `",
        "` + _t("open") + `",
        "` + _t("open letterbox with raised flag") + `",
        "` + _t("postbox") + `",
        "` + _t("open mailbox with raised flag") + `",
        "` + _t("open postbox with raised flag") + `",
        "` + _t("post") + `",
        "` + _t("post box") + `"
    ],
    "name": "` + _t("open mailbox with raised flag") + `",
    "shortcodes": [
        ":open_mailbox_with_raised_flag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📭",
    "emoticons": [],
    "keywords": [
        "` + _t("lowered") + `",
        "` + _t("mail") + `",
        "` + _t("mailbox") + `",
        "` + _t("open") + `",
        "` + _t("open letterbox with lowered flag") + `",
        "` + _t("postbox") + `",
        "` + _t("open mailbox with lowered flag") + `",
        "` + _t("open postbox with lowered flag") + `",
        "` + _t("post") + `",
        "` + _t("post box") + `"
    ],
    "name": "` + _t("open mailbox with lowered flag") + `",
    "shortcodes": [
        ":open_mailbox_with_lowered_flag:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📮",
    "emoticons": [],
    "keywords": [
        "` + _t("mail") + `",
        "` + _t("mailbox") + `",
        "` + _t("postbox") + `",
        "` + _t("post") + `",
        "` + _t("post box") + `"
    ],
    "name": "` + _t("postbox") + `",
    "shortcodes": [
        ":postbox:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗳️",
    "emoticons": [],
    "keywords": [
        "` + _t("ballot") + `",
        "` + _t("ballot box with ballot") + `",
        "` + _t("box") + `"
    ],
    "name": "` + _t("ballot box with ballot") + `",
    "shortcodes": [
        ":ballot_box_with_ballot:"
    ]
},
{
    "category": "Objects",
    "codepoints": "✏️",
    "emoticons": [],
    "keywords": [
        "` + _t("pencil") + `"
    ],
    "name": "` + _t("pencil") + `",
    "shortcodes": [
        ":pencil:"
    ]
},
{
    "category": "Objects",
    "codepoints": "✒️",
    "emoticons": [],
    "keywords": [
        "` + _t("black nib") + `",
        "` + _t("nib") + `",
        "` + _t("pen") + `"
    ],
    "name": "` + _t("black nib") + `",
    "shortcodes": [
        ":black_nib:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖋️",
    "emoticons": [],
    "keywords": [
        "` + _t("fountain") + `",
        "` + _t("pen") + `"
    ],
    "name": "` + _t("fountain pen") + `",
    "shortcodes": [
        ":fountain_pen:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖊️",
    "emoticons": [],
    "keywords": [
        "` + _t("ballpoint") + `",
        "` + _t("pen") + `"
    ],
    "name": "` + _t("pen") + `",
    "shortcodes": [
        ":pen:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖌️",
    "emoticons": [],
    "keywords": [
        "` + _t("paintbrush") + `",
        "` + _t("painting") + `"
    ],
    "name": "` + _t("paintbrush") + `",
    "shortcodes": [
        ":paintbrush:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖍️",
    "emoticons": [],
    "keywords": [
        "` + _t("crayon") + `"
    ],
    "name": "` + _t("crayon") + `",
    "shortcodes": [
        ":crayon:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📝",
    "emoticons": [],
    "keywords": [
        "` + _t("memo") + `",
        "` + _t("pencil") + `"
    ],
    "name": "` + _t("memo") + `",
    "shortcodes": [
        ":memo:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💼",
    "emoticons": [],
    "keywords": [
        "` + _t("briefcase") + `"
    ],
    "name": "` + _t("briefcase") + `",
    "shortcodes": [
        ":briefcase:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📁",
    "emoticons": [],
    "keywords": [
        "` + _t("file") + `",
        "` + _t("folder") + `"
    ],
    "name": "` + _t("file folder") + `",
    "shortcodes": [
        ":file_folder:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📂",
    "emoticons": [],
    "keywords": [
        "` + _t("file") + `",
        "` + _t("folder") + `",
        "` + _t("open") + `"
    ],
    "name": "` + _t("open file folder") + `",
    "shortcodes": [
        ":open_file_folder:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗂️",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("dividers") + `",
        "` + _t("index") + `"
    ],
    "name": "` + _t("card index dividers") + `",
    "shortcodes": [
        ":card_index_dividers:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📅",
    "emoticons": [],
    "keywords": [
        "` + _t("calendar") + `",
        "` + _t("date") + `"
    ],
    "name": "` + _t("calendar") + `",
    "shortcodes": [
        ":calendar:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📆",
    "emoticons": [],
    "keywords": [
        "` + _t("calendar") + `",
        "` + _t("tear-off calendar") + `"
    ],
    "name": "` + _t("tear-off calendar") + `",
    "shortcodes": [
        ":tear-off_calendar:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗒️",
    "emoticons": [],
    "keywords": [
        "` + _t("note") + `",
        "` + _t("pad") + `",
        "` + _t("spiral") + `",
        "` + _t("spiral notepad") + `"
    ],
    "name": "` + _t("spiral notepad") + `",
    "shortcodes": [
        ":spiral_notepad:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗓️",
    "emoticons": [],
    "keywords": [
        "` + _t("calendar") + `",
        "` + _t("pad") + `",
        "` + _t("spiral") + `"
    ],
    "name": "` + _t("spiral calendar") + `",
    "shortcodes": [
        ":spiral_calendar:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📇",
    "emoticons": [],
    "keywords": [
        "` + _t("card") + `",
        "` + _t("index") + `",
        "` + _t("rolodex") + `"
    ],
    "name": "` + _t("card index") + `",
    "shortcodes": [
        ":card_index:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📈",
    "emoticons": [],
    "keywords": [
        "` + _t("chart") + `",
        "` + _t("chart increasing") + `",
        "` + _t("graph") + `",
        "` + _t("graph increasing") + `",
        "` + _t("growth") + `",
        "` + _t("trend") + `",
        "` + _t("upward") + `"
    ],
    "name": "` + _t("chart increasing") + `",
    "shortcodes": [
        ":chart_increasing:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📉",
    "emoticons": [],
    "keywords": [
        "` + _t("chart") + `",
        "` + _t("chart decreasing") + `",
        "` + _t("down") + `",
        "` + _t("graph") + `",
        "` + _t("graph decreasing") + `",
        "` + _t("trend") + `"
    ],
    "name": "` + _t("chart decreasing") + `",
    "shortcodes": [
        ":chart_decreasing:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📊",
    "emoticons": [],
    "keywords": [
        "` + _t("bar") + `",
        "` + _t("chart") + `",
        "` + _t("graph") + `"
    ],
    "name": "` + _t("bar chart") + `",
    "shortcodes": [
        ":bar_chart:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📋",
    "emoticons": [],
    "keywords": [
        "` + _t("clipboard") + `"
    ],
    "name": "` + _t("clipboard") + `",
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
        "` + _t("drawing-pin") + `",
        "` + _t("pin") + `",
        "` + _t("pushpin") + `"
    ],
    "name": "` + _t("pushpin") + `",
    "shortcodes": [
        ":pushpin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📍",
    "emoticons": [],
    "keywords": [
        "` + _t("pin") + `",
        "` + _t("pushpin") + `",
        "` + _t("round drawing-pin") + `",
        "` + _t("round pushpin") + `"
    ],
    "name": "` + _t("round pushpin") + `",
    "shortcodes": [
        ":round_pushpin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📎",
    "emoticons": [],
    "keywords": [
        "` + _t("paperclip") + `"
    ],
    "name": "` + _t("paperclip") + `",
    "shortcodes": [
        ":paperclip:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🖇️",
    "emoticons": [],
    "keywords": [
        "` + _t("link") + `",
        "` + _t("linked paperclips") + `",
        "` + _t("paperclip") + `"
    ],
    "name": "` + _t("linked paperclips") + `",
    "shortcodes": [
        ":linked_paperclips:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📏",
    "emoticons": [],
    "keywords": [
        "` + _t("ruler") + `",
        "` + _t("straight edge") + `",
        "` + _t("straight ruler") + `"
    ],
    "name": "` + _t("straight ruler") + `",
    "shortcodes": [
        ":straight_ruler:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📐",
    "emoticons": [],
    "keywords": [
        "` + _t("ruler") + `",
        "` + _t("set") + `",
        "` + _t("triangle") + `",
        "` + _t("triangular ruler") + `",
        "` + _t("set square") + `"
    ],
    "name": "` + _t("triangular ruler") + `",
    "shortcodes": [
        ":triangular_ruler:"
    ]
},
{
    "category": "Objects",
    "codepoints": "✂️",
    "emoticons": [],
    "keywords": [
        "` + _t("cutting") + `",
        "` + _t("scissors") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("scissors") + `",
    "shortcodes": [
        ":scissors:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗃️",
    "emoticons": [],
    "keywords": [
        "` + _t("box") + `",
        "` + _t("card") + `",
        "` + _t("file") + `"
    ],
    "name": "` + _t("card file box") + `",
    "shortcodes": [
        ":card_file_box:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗄️",
    "emoticons": [],
    "keywords": [
        "` + _t("cabinet") + `",
        "` + _t("file") + `",
        "` + _t("filing") + `"
    ],
    "name": "` + _t("file cabinet") + `",
    "shortcodes": [
        ":file_cabinet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗑️",
    "emoticons": [],
    "keywords": [
        "` + _t("wastebasket") + `"
    ],
    "name": "` + _t("wastebasket") + `",
    "shortcodes": [
        ":wastebasket:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔒",
    "emoticons": [],
    "keywords": [
        "` + _t("closed") + `",
        "` + _t("locked") + `",
        "` + _t("padlock") + `"
    ],
    "name": "` + _t("locked") + `",
    "shortcodes": [
        ":locked:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔓",
    "emoticons": [],
    "keywords": [
        "` + _t("lock") + `",
        "` + _t("open") + `",
        "` + _t("unlock") + `",
        "` + _t("unlocked") + `",
        "` + _t("padlock") + `"
    ],
    "name": "` + _t("unlocked") + `",
    "shortcodes": [
        ":unlocked:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔏",
    "emoticons": [],
    "keywords": [
        "` + _t("ink") + `",
        "` + _t("lock") + `",
        "` + _t("locked with pen") + `",
        "` + _t("nib") + `",
        "` + _t("pen") + `",
        "` + _t("privacy") + `"
    ],
    "name": "` + _t("locked with pen") + `",
    "shortcodes": [
        ":locked_with_pen:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔐",
    "emoticons": [],
    "keywords": [
        "` + _t("closed") + `",
        "` + _t("key") + `",
        "` + _t("lock") + `",
        "` + _t("locked with key") + `",
        "` + _t("secure") + `"
    ],
    "name": "` + _t("locked with key") + `",
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
        "` + _t("key") + `",
        "` + _t("lock") + `",
        "` + _t("password") + `"
    ],
    "name": "` + _t("key") + `",
    "shortcodes": [
        ":key:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗝️",
    "emoticons": [],
    "keywords": [
        "` + _t("clue") + `",
        "` + _t("key") + `",
        "` + _t("lock") + `",
        "` + _t("old") + `"
    ],
    "name": "` + _t("old key") + `",
    "shortcodes": [
        ":old_key:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔨",
    "emoticons": [],
    "keywords": [
        "` + _t("hammer") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("hammer") + `",
    "shortcodes": [
        ":hammer:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪓",
    "emoticons": [],
    "keywords": [
        "` + _t("axe") + `",
        "` + _t("chop") + `",
        "` + _t("hatchet") + `",
        "` + _t("split") + `",
        "` + _t("wood") + `"
    ],
    "name": "` + _t("axe") + `",
    "shortcodes": [
        ":axe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⛏️",
    "emoticons": [],
    "keywords": [
        "` + _t("mining") + `",
        "` + _t("pick") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("pick") + `",
    "shortcodes": [
        ":pick:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚒️",
    "emoticons": [],
    "keywords": [
        "` + _t("hammer") + `",
        "` + _t("hammer and pick") + `",
        "` + _t("pick") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("hammer and pick") + `",
    "shortcodes": [
        ":hammer_and_pick:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛠️",
    "emoticons": [],
    "keywords": [
        "` + _t("hammer") + `",
        "` + _t("hammer and spanner") + `",
        "` + _t("hammer and wrench") + `",
        "` + _t("spanner") + `",
        "` + _t("tool") + `",
        "` + _t("wrench") + `"
    ],
    "name": "` + _t("hammer and wrench") + `",
    "shortcodes": [
        ":hammer_and_wrench:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗡️",
    "emoticons": [],
    "keywords": [
        "` + _t("dagger") + `",
        "` + _t("knife") + `",
        "` + _t("weapon") + `"
    ],
    "name": "` + _t("dagger") + `",
    "shortcodes": [
        ":dagger:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚔️",
    "emoticons": [],
    "keywords": [
        "` + _t("crossed") + `",
        "` + _t("swords") + `",
        "` + _t("weapon") + `"
    ],
    "name": "` + _t("crossed swords") + `",
    "shortcodes": [
        ":crossed_swords:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔫",
    "emoticons": [],
    "keywords": [
        "` + _t("toy") + `",
        "` + _t("water pistol") + `",
        "` + _t("gun") + `",
        "` + _t("handgun") + `",
        "` + _t("pistol") + `",
        "` + _t("revolver") + `",
        "` + _t("tool") + `",
        "` + _t("water") + `",
        "` + _t("weapon") + `"
    ],
    "name": "` + _t("water pistol") + `",
    "shortcodes": [
        ":water_pistol:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🏹",
    "emoticons": [],
    "keywords": [
        "` + _t("archer") + `",
        "` + _t("arrow") + `",
        "` + _t("bow") + `",
        "` + _t("bow and arrow") + `",
        "` + _t("Sagittarius") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("bow and arrow") + `",
    "shortcodes": [
        ":bow_and_arrow:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛡️",
    "emoticons": [],
    "keywords": [
        "` + _t("shield") + `",
        "` + _t("weapon") + `"
    ],
    "name": "` + _t("shield") + `",
    "shortcodes": [
        ":shield:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔧",
    "emoticons": [],
    "keywords": [
        "` + _t("spanner") + `",
        "` + _t("tool") + `",
        "` + _t("wrench") + `"
    ],
    "name": "` + _t("wrench") + `",
    "shortcodes": [
        ":wrench:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔩",
    "emoticons": [],
    "keywords": [
        "` + _t("bolt") + `",
        "` + _t("nut") + `",
        "` + _t("nut and bolt") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("nut and bolt") + `",
    "shortcodes": [
        ":nut_and_bolt:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚙️",
    "emoticons": [],
    "keywords": [
        "` + _t("cog") + `",
        "` + _t("cogwheel") + `",
        "` + _t("gear") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("gear") + `",
    "shortcodes": [
        ":gear:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗜️",
    "emoticons": [],
    "keywords": [
        "` + _t("clamp") + `",
        "` + _t("compress") + `",
        "` + _t("tool") + `",
        "` + _t("vice") + `"
    ],
    "name": "` + _t("clamp") + `",
    "shortcodes": [
        ":clamp:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚖️",
    "emoticons": [],
    "keywords": [
        "` + _t("balance") + `",
        "` + _t("justice") + `",
        "` + _t("Libra") + `",
        "` + _t("scale") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("balance scale") + `",
    "shortcodes": [
        ":balance_scale:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🦯",
    "emoticons": [],
    "keywords": [
        "` + _t("accessibility") + `",
        "` + _t("long mobility cane") + `",
        "` + _t("white cane") + `",
        "` + _t("blind") + `",
        "` + _t("guide cane") + `"
    ],
    "name": "` + _t("white cane") + `",
    "shortcodes": [
        ":white_cane:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔗",
    "emoticons": [],
    "keywords": [
        "` + _t("link") + `"
    ],
    "name": "` + _t("link") + `",
    "shortcodes": [
        ":link:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⛓️",
    "emoticons": [],
    "keywords": [
        "` + _t("chain") + `",
        "` + _t("chains") + `"
    ],
    "name": "` + _t("chains") + `",
    "shortcodes": [
        ":chains:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧰",
    "emoticons": [],
    "keywords": [
        "` + _t("chest") + `",
        "` + _t("mechanic") + `",
        "` + _t("tool") + `",
        "` + _t("toolbox") + `"
    ],
    "name": "` + _t("toolbox") + `",
    "shortcodes": [
        ":toolbox:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧲",
    "emoticons": [],
    "keywords": [
        "` + _t("attraction") + `",
        "` + _t("horseshoe") + `",
        "` + _t("magnet") + `",
        "` + _t("magnetic") + `"
    ],
    "name": "` + _t("magnet") + `",
    "shortcodes": [
        ":magnet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚗️",
    "emoticons": [],
    "keywords": [
        "` + _t("alembic") + `",
        "` + _t("chemistry") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("alembic") + `",
    "shortcodes": [
        ":alembic:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧪",
    "emoticons": [],
    "keywords": [
        "` + _t("chemist") + `",
        "` + _t("chemistry") + `",
        "` + _t("experiment") + `",
        "` + _t("lab") + `",
        "` + _t("science") + `",
        "` + _t("test tube") + `"
    ],
    "name": "` + _t("test tube") + `",
    "shortcodes": [
        ":test_tube:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧫",
    "emoticons": [],
    "keywords": [
        "` + _t("bacteria") + `",
        "` + _t("biologist") + `",
        "` + _t("biology") + `",
        "` + _t("culture") + `",
        "` + _t("lab") + `",
        "` + _t("petri dish") + `"
    ],
    "name": "` + _t("petri dish") + `",
    "shortcodes": [
        ":petri_dish:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧬",
    "emoticons": [],
    "keywords": [
        "` + _t("biologist") + `",
        "` + _t("dna") + `",
        "` + _t("DNA") + `",
        "` + _t("evolution") + `",
        "` + _t("gene") + `",
        "` + _t("genetics") + `",
        "` + _t("life") + `"
    ],
    "name": "` + _t("dna") + `",
    "shortcodes": [
        ":dna:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔬",
    "emoticons": [],
    "keywords": [
        "` + _t("microscope") + `",
        "` + _t("science") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("microscope") + `",
    "shortcodes": [
        ":microscope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🔭",
    "emoticons": [],
    "keywords": [
        "` + _t("science") + `",
        "` + _t("telescope") + `",
        "` + _t("tool") + `"
    ],
    "name": "` + _t("telescope") + `",
    "shortcodes": [
        ":telescope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "📡",
    "emoticons": [],
    "keywords": [
        "` + _t("antenna") + `",
        "` + _t("dish") + `",
        "` + _t("satellite") + `"
    ],
    "name": "` + _t("satellite antenna") + `",
    "shortcodes": [
        ":satellite_antenna:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💉",
    "emoticons": [],
    "keywords": [
        "` + _t("medicine") + `",
        "` + _t("needle") + `",
        "` + _t("shot") + `",
        "` + _t("sick") + `",
        "` + _t("syringe") + `",
        "` + _t("ill") + `",
        "` + _t("injection") + `"
    ],
    "name": "` + _t("syringe") + `",
    "shortcodes": [
        ":syringe:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩸",
    "emoticons": [],
    "keywords": [
        "` + _t("bleed") + `",
        "` + _t("blood donation") + `",
        "` + _t("drop of blood") + `",
        "` + _t("injury") + `",
        "` + _t("medicine") + `",
        "` + _t("menstruation") + `"
    ],
    "name": "` + _t("drop of blood") + `",
    "shortcodes": [
        ":drop_of_blood:"
    ]
},
{
    "category": "Objects",
    "codepoints": "💊",
    "emoticons": [],
    "keywords": [
        "` + _t("doctor") + `",
        "` + _t("medicine") + `",
        "` + _t("pill") + `",
        "` + _t("sick") + `"
    ],
    "name": "` + _t("pill") + `",
    "shortcodes": [
        ":pill:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩹",
    "emoticons": [],
    "keywords": [
        "` + _t("adhesive bandage") + `",
        "` + _t("bandage") + `",
        "` + _t("bandaid") + `",
        "` + _t("dressing") + `",
        "` + _t("injury") + `",
        "` + _t("plaster") + `",
        "` + _t("sticking plaster") + `"
    ],
    "name": "` + _t("adhesive bandage") + `",
    "shortcodes": [
        ":adhesive_bandage:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🩺",
    "emoticons": [],
    "keywords": [
        "` + _t("doctor") + `",
        "` + _t("heart") + `",
        "` + _t("medicine") + `",
        "` + _t("stethoscope") + `"
    ],
    "name": "` + _t("stethoscope") + `",
    "shortcodes": [
        ":stethoscope:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🚪",
    "emoticons": [],
    "keywords": [
        "` + _t("door") + `"
    ],
    "name": "` + _t("door") + `",
    "shortcodes": [
        ":door:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛏️",
    "emoticons": [],
    "keywords": [
        "` + _t("bed") + `",
        "` + _t("hotel") + `",
        "` + _t("sleep") + `"
    ],
    "name": "` + _t("bed") + `",
    "shortcodes": [
        ":bed:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛋️",
    "emoticons": [],
    "keywords": [
        "` + _t("couch") + `",
        "` + _t("couch and lamp") + `",
        "` + _t("hotel") + `",
        "` + _t("lamp") + `",
        "` + _t("sofa") + `",
        "` + _t("sofa and lamp") + `"
    ],
    "name": "` + _t("couch and lamp") + `",
    "shortcodes": [
        ":couch_and_lamp:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪑",
    "emoticons": [],
    "keywords": [
        "` + _t("chair") + `",
        "` + _t("seat") + `",
        "` + _t("sit") + `"
    ],
    "name": "` + _t("chair") + `",
    "shortcodes": [
        ":chair:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🚽",
    "emoticons": [],
    "keywords": [
        "` + _t("facilities") + `",
        "` + _t("loo") + `",
        "` + _t("toilet") + `",
        "` + _t("WC") + `",
        "` + _t("lavatory") + `"
    ],
    "name": "` + _t("toilet") + `",
    "shortcodes": [
        ":toilet:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🚿",
    "emoticons": [],
    "keywords": [
        "` + _t("shower") + `",
        "` + _t("water") + `"
    ],
    "name": "` + _t("shower") + `",
    "shortcodes": [
        ":shower:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛁",
    "emoticons": [],
    "keywords": [
        "` + _t("bath") + `",
        "` + _t("bathtub") + `"
    ],
    "name": "` + _t("bathtub") + `",
    "shortcodes": [
        ":bathtub:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🪒",
    "emoticons": [],
    "keywords": [
        "` + _t("razor") + `",
        "` + _t("sharp") + `",
        "` + _t("shave") + `",
        "` + _t("cut-throat") + `"
    ],
    "name": "` + _t("razor") + `",
    "shortcodes": [
        ":razor:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧴",
    "emoticons": [],
    "keywords": [
        "` + _t("lotion") + `",
        "` + _t("lotion bottle") + `",
        "` + _t("moisturizer") + `",
        "` + _t("shampoo") + `",
        "` + _t("sunscreen") + `",
        "` + _t("moisturiser") + `"
    ],
    "name": "` + _t("lotion bottle") + `",
    "shortcodes": [
        ":lotion_bottle:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧷",
    "emoticons": [],
    "keywords": [
        "` + _t("nappy") + `",
        "` + _t("punk rock") + `",
        "` + _t("safety pin") + `",
        "` + _t("diaper") + `"
    ],
    "name": "` + _t("safety pin") + `",
    "shortcodes": [
        ":safety_pin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧹",
    "emoticons": [],
    "keywords": [
        "` + _t("broom") + `",
        "` + _t("cleaning") + `",
        "` + _t("sweeping") + `",
        "` + _t("witch") + `"
    ],
    "name": "` + _t("broom") + `",
    "shortcodes": [
        ":broom:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧺",
    "emoticons": [],
    "keywords": [
        "` + _t("basket") + `",
        "` + _t("farming") + `",
        "` + _t("laundry") + `",
        "` + _t("picnic") + `"
    ],
    "name": "` + _t("basket") + `",
    "shortcodes": [
        ":basket:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧻",
    "emoticons": [],
    "keywords": [
        "` + _t("paper towels") + `",
        "` + _t("roll of paper") + `",
        "` + _t("toilet paper") + `",
        "` + _t("toilet roll") + `"
    ],
    "name": "` + _t("roll of paper") + `",
    "shortcodes": [
        ":roll_of_paper:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧼",
    "emoticons": [],
    "keywords": [
        "` + _t("bar") + `",
        "` + _t("bathing") + `",
        "` + _t("cleaning") + `",
        "` + _t("lather") + `",
        "` + _t("soap") + `",
        "` + _t("soapdish") + `"
    ],
    "name": "` + _t("soap") + `",
    "shortcodes": [
        ":soap:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧽",
    "emoticons": [],
    "keywords": [
        "` + _t("absorbing") + `",
        "` + _t("cleaning") + `",
        "` + _t("porous") + `",
        "` + _t("sponge") + `"
    ],
    "name": "` + _t("sponge") + `",
    "shortcodes": [
        ":sponge:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🧯",
    "emoticons": [],
    "keywords": [
        "` + _t("extinguish") + `",
        "` + _t("fire") + `",
        "` + _t("fire extinguisher") + `",
        "` + _t("quench") + `"
    ],
    "name": "` + _t("fire extinguisher") + `",
    "shortcodes": [
        ":fire_extinguisher:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🛒",
    "emoticons": [],
    "keywords": [
        "` + _t("cart") + `",
        "` + _t("shopping") + `",
        "` + _t("trolley") + `",
        "` + _t("basket") + `"
    ],
    "name": "` + _t("shopping cart") + `",
    "shortcodes": [
        ":shopping_cart:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🚬",
    "emoticons": [],
    "keywords": [
        "` + _t("cigarette") + `",
        "` + _t("smoking") + `"
    ],
    "name": "` + _t("cigarette") + `",
    "shortcodes": [
        ":cigarette:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚰️",
    "emoticons": [],
    "keywords": [
        "` + _t("coffin") + `",
        "` + _t("death") + `"
    ],
    "name": "` + _t("coffin") + `",
    "shortcodes": [
        ":coffin:"
    ]
},
{
    "category": "Objects",
    "codepoints": "⚱️",
    "emoticons": [],
    "keywords": [
        "` + _t("ashes") + `",
        "` + _t("death") + `",
        "` + _t("funeral") + `",
        "` + _t("urn") + `"
    ],
    "name": "` + _t("funeral urn") + `",
    "shortcodes": [
        ":funeral_urn:"
    ]
},
{
    "category": "Objects",
    "codepoints": "🗿",
    "emoticons": [],
    "keywords": [
        "` + _t("face") + `",
        "` + _t("moai") + `",
        "` + _t("moyai") + `",
        "` + _t("statue") + `"
    ],
    "name": "` + _t("moai") + `",
    "shortcodes": [
        ":moai:"
    ]
},`;

const _getEmojisData8 = () => `{
    "category": "Symbols",
    "codepoints": "🏧",
    "emoticons": [],
    "keywords": [
        "` + _t("ATM") + `",
        "` + _t("ATM sign") + `",
        "` + _t("automated") + `",
        "` + _t("bank") + `",
        "` + _t("teller") + `"
    ],
    "name": "` + _t("ATM sign") + `",
    "shortcodes": [
        ":ATM_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚮",
    "emoticons": [],
    "keywords": [
        "` + _t("litter") + `",
        "` + _t("litter bin") + `",
        "` + _t("litter in bin sign") + `",
        "` + _t("garbage") + `",
        "` + _t("trash") + `"
    ],
    "name": "` + _t("litter in bin sign") + `",
    "shortcodes": [
        ":litter_in_bin_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚰",
    "emoticons": [],
    "keywords": [
        "` + _t("drinking") + `",
        "` + _t("potable") + `",
        "` + _t("water") + `"
    ],
    "name": "` + _t("potable water") + `",
    "shortcodes": [
        ":potable_water:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♿",
    "emoticons": [],
    "keywords": [
        "` + _t("access") + `",
        "` + _t("disabled access") + `",
        "` + _t("wheelchair symbol") + `"
    ],
    "name": "` + _t("wheelchair symbol") + `",
    "shortcodes": [
        ":wheelchair_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚹",
    "emoticons": [],
    "keywords": [
        "` + _t("bathroom") + `",
        "` + _t("lavatory") + `",
        "` + _t("man") + `",
        "` + _t("men’s room") + `",
        "` + _t("restroom") + `",
        "` + _t("toilet") + `",
        "` + _t("WC") + `",
        "` + _t("men’s") + `",
        "` + _t("washroom") + `",
        "` + _t("wc") + `"
    ],
    "name": "` + _t("men’s room") + `",
    "shortcodes": [
        ":men’s_room:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚺",
    "emoticons": [],
    "keywords": [
        "` + _t("ladies room") + `",
        "` + _t("lavatory") + `",
        "` + _t("restroom") + `",
        "` + _t("wc") + `",
        "` + _t("woman") + `",
        "` + _t("women’s room") + `",
        "` + _t("women’s toilet") + `",
        "` + _t("bathroom") + `",
        "` + _t("toilet") + `",
        "` + _t("WC") + `",
        "` + _t("ladies’ room") + `",
        "` + _t("washroom") + `",
        "` + _t("women’s") + `"
    ],
    "name": "` + _t("women’s room") + `",
    "shortcodes": [
        ":women’s_room:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚻",
    "emoticons": [],
    "keywords": [
        "` + _t("bathroom") + `",
        "` + _t("lavatory") + `",
        "` + _t("restroom") + `",
        "` + _t("toilet") + `",
        "` + _t("WC") + `",
        "` + _t("washroom") + `"
    ],
    "name": "` + _t("restroom") + `",
    "shortcodes": [
        ":restroom:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚼",
    "emoticons": [],
    "keywords": [
        "` + _t("baby") + `",
        "` + _t("baby symbol") + `",
        "` + _t("change room") + `",
        "` + _t("changing") + `"
    ],
    "name": "` + _t("baby symbol") + `",
    "shortcodes": [
        ":baby_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚾",
    "emoticons": [],
    "keywords": [
        "` + _t("amenities") + `",
        "` + _t("bathroom") + `",
        "` + _t("restroom") + `",
        "` + _t("toilet") + `",
        "` + _t("water closet") + `",
        "` + _t("wc") + `",
        "` + _t("WC") + `",
        "` + _t("closet") + `",
        "` + _t("lavatory") + `",
        "` + _t("water") + `"
    ],
    "name": "` + _t("water closet") + `",
    "shortcodes": [
        ":water_closet:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛂",
    "emoticons": [],
    "keywords": [
        "` + _t("border") + `",
        "` + _t("control") + `",
        "` + _t("passport") + `",
        "` + _t("security") + `"
    ],
    "name": "` + _t("passport control") + `",
    "shortcodes": [
        ":passport_control:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛃",
    "emoticons": [],
    "keywords": [
        "` + _t("customs") + `"
    ],
    "name": "` + _t("customs") + `",
    "shortcodes": [
        ":customs:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛄",
    "emoticons": [],
    "keywords": [
        "` + _t("baggage") + `",
        "` + _t("claim") + `"
    ],
    "name": "` + _t("baggage claim") + `",
    "shortcodes": [
        ":baggage_claim:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛅",
    "emoticons": [],
    "keywords": [
        "` + _t("baggage") + `",
        "` + _t("left luggage") + `",
        "` + _t("locker") + `",
        "` + _t("luggage") + `"
    ],
    "name": "` + _t("left luggage") + `",
    "shortcodes": [
        ":left_luggage:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚠️",
    "emoticons": [],
    "keywords": [
        "` + _t("warning") + `"
    ],
    "name": "` + _t("warning") + `",
    "shortcodes": [
        ":warning:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚸",
    "emoticons": [],
    "keywords": [
        "` + _t("child") + `",
        "` + _t("children crossing") + `",
        "` + _t("crossing") + `",
        "` + _t("pedestrian") + `",
        "` + _t("traffic") + `"
    ],
    "name": "` + _t("children crossing") + `",
    "shortcodes": [
        ":children_crossing:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⛔",
    "emoticons": [],
    "keywords": [
        "` + _t("denied") + `",
        "` + _t("entry") + `",
        "` + _t("forbidden") + `",
        "` + _t("no") + `",
        "` + _t("prohibited") + `",
        "` + _t("traffic") + `",
        "` + _t("not") + `"
    ],
    "name": "` + _t("no entry") + `",
    "shortcodes": [
        ":no_entry:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚫",
    "emoticons": [],
    "keywords": [
        "` + _t("denied") + `",
        "` + _t("entry") + `",
        "` + _t("forbidden") + `",
        "` + _t("no") + `",
        "` + _t("prohibited") + `",
        "` + _t("not") + `"
    ],
    "name": "` + _t("prohibited") + `",
    "shortcodes": [
        ":prohibited:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚳",
    "emoticons": [],
    "keywords": [
        "` + _t("bicycle") + `",
        "` + _t("bike") + `",
        "` + _t("forbidden") + `",
        "` + _t("no") + `",
        "` + _t("no bicycles") + `",
        "` + _t("prohibited") + `"
    ],
    "name": "` + _t("no bicycles") + `",
    "shortcodes": [
        ":no_bicycles:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚭",
    "emoticons": [],
    "keywords": [
        "` + _t("denied") + `",
        "` + _t("forbidden") + `",
        "` + _t("no") + `",
        "` + _t("prohibited") + `",
        "` + _t("smoking") + `",
        "` + _t("not") + `"
    ],
    "name": "` + _t("no smoking") + `",
    "shortcodes": [
        ":no_smoking:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚯",
    "emoticons": [],
    "keywords": [
        "` + _t("denied") + `",
        "` + _t("forbidden") + `",
        "` + _t("litter") + `",
        "` + _t("no") + `",
        "` + _t("no littering") + `",
        "` + _t("prohibited") + `",
        "` + _t("not") + `"
    ],
    "name": "` + _t("no littering") + `",
    "shortcodes": [
        ":no_littering:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚱",
    "emoticons": [],
    "keywords": [
        "` + _t("non-drinkable water") + `",
        "` + _t("non-drinking") + `",
        "` + _t("non-potable") + `",
        "` + _t("water") + `"
    ],
    "name": "` + _t("non-potable water") + `",
    "shortcodes": [
        ":non-potable_water:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚷",
    "emoticons": [],
    "keywords": [
        "` + _t("denied") + `",
        "` + _t("forbidden") + `",
        "` + _t("no") + `",
        "` + _t("no pedestrians") + `",
        "` + _t("pedestrian") + `",
        "` + _t("prohibited") + `",
        "` + _t("not") + `"
    ],
    "name": "` + _t("no pedestrians") + `",
    "shortcodes": [
        ":no_pedestrians:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📵",
    "emoticons": [],
    "keywords": [
        "` + _t("cell") + `",
        "` + _t("forbidden") + `",
        "` + _t("mobile") + `",
        "` + _t("no") + `",
        "` + _t("no mobile phones") + `",
        "` + _t("phone") + `"
    ],
    "name": "` + _t("no mobile phones") + `",
    "shortcodes": [
        ":no_mobile_phones:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔞",
    "emoticons": [],
    "keywords": [
        "` + _t("18") + `",
        "` + _t("age restriction") + `",
        "` + _t("eighteen") + `",
        "` + _t("no one under eighteen") + `",
        "` + _t("prohibited") + `",
        "` + _t("underage") + `"
    ],
    "name": "` + _t("no one under eighteen") + `",
    "shortcodes": [
        ":no_one_under_eighteen:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☢️",
    "emoticons": [],
    "keywords": [
        "` + _t("radioactive") + `",
        "` + _t("sign") + `"
    ],
    "name": "` + _t("radioactive") + `",
    "shortcodes": [
        ":radioactive:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☣️",
    "emoticons": [],
    "keywords": [
        "` + _t("biohazard") + `",
        "` + _t("sign") + `"
    ],
    "name": "` + _t("biohazard") + `",
    "shortcodes": [
        ":biohazard:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬆️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("cardinal") + `",
        "` + _t("direction") + `",
        "` + _t("north") + `",
        "` + _t("up") + `",
        "` + _t("up arrow") + `"
    ],
    "name": "` + _t("up arrow") + `",
    "shortcodes": [
        ":up_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↗️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("direction") + `",
        "` + _t("intercardinal") + `",
        "` + _t("northeast") + `",
        "` + _t("up-right arrow") + `"
    ],
    "name": "` + _t("up-right arrow") + `",
    "shortcodes": [
        ":up-right_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➡️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("cardinal") + `",
        "` + _t("direction") + `",
        "` + _t("east") + `",
        "` + _t("right arrow") + `"
    ],
    "name": "` + _t("right arrow") + `",
    "shortcodes": [
        ":right_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↘️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("direction") + `",
        "` + _t("down-right arrow") + `",
        "` + _t("intercardinal") + `",
        "` + _t("southeast") + `"
    ],
    "name": "` + _t("down-right arrow") + `",
    "shortcodes": [
        ":down-right_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬇️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("cardinal") + `",
        "` + _t("direction") + `",
        "` + _t("down") + `",
        "` + _t("south") + `"
    ],
    "name": "` + _t("down arrow") + `",
    "shortcodes": [
        ":down_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↙️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("direction") + `",
        "` + _t("down-left arrow") + `",
        "` + _t("intercardinal") + `",
        "` + _t("southwest") + `"
    ],
    "name": "` + _t("down-left arrow") + `",
    "shortcodes": [
        ":down-left_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬅️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("cardinal") + `",
        "` + _t("direction") + `",
        "` + _t("left arrow") + `",
        "` + _t("west") + `"
    ],
    "name": "` + _t("left arrow") + `",
    "shortcodes": [
        ":left_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↖️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("direction") + `",
        "` + _t("intercardinal") + `",
        "` + _t("northwest") + `",
        "` + _t("up-left arrow") + `"
    ],
    "name": "` + _t("up-left arrow") + `",
    "shortcodes": [
        ":up-left_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↕️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("up-down arrow") + `"
    ],
    "name": "` + _t("up-down arrow") + `",
    "shortcodes": [
        ":up-down_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↔️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("left-right arrow") + `"
    ],
    "name": "` + _t("left-right arrow") + `",
    "shortcodes": [
        ":left-right_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↩️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("right arrow curving left") + `"
    ],
    "name": "` + _t("right arrow curving left") + `",
    "shortcodes": [
        ":right_arrow_curving_left:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "↪️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("left arrow curving right") + `"
    ],
    "name": "` + _t("left arrow curving right") + `",
    "shortcodes": [
        ":left_arrow_curving_right:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⤴️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("right arrow curving up") + `"
    ],
    "name": "` + _t("right arrow curving up") + `",
    "shortcodes": [
        ":right_arrow_curving_up:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⤵️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("down") + `",
        "` + _t("right arrow curving down") + `"
    ],
    "name": "` + _t("right arrow curving down") + `",
    "shortcodes": [
        ":right_arrow_curving_down:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔃",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("clockwise") + `",
        "` + _t("clockwise vertical arrows") + `",
        "` + _t("reload") + `"
    ],
    "name": "` + _t("clockwise vertical arrows") + `",
    "shortcodes": [
        ":clockwise_vertical_arrows:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔄",
    "emoticons": [],
    "keywords": [
        "` + _t("anticlockwise") + `",
        "` + _t("arrow") + `",
        "` + _t("counterclockwise") + `",
        "` + _t("counterclockwise arrows button") + `",
        "` + _t("withershins") + `",
        "` + _t("anticlockwise arrows button") + `"
    ],
    "name": "` + _t("counterclockwise arrows button") + `",
    "shortcodes": [
        ":counterclockwise_arrows_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔙",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("BACK") + `"
    ],
    "name": "` + _t("BACK arrow") + `",
    "shortcodes": [
        ":BACK_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔚",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("END") + `"
    ],
    "name": "` + _t("END arrow") + `",
    "shortcodes": [
        ":END_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔛",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("mark") + `",
        "` + _t("ON") + `",
        "` + _t("ON!") + `"
    ],
    "name": "` + _t("ON! arrow") + `",
    "shortcodes": [
        ":ON!_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔜",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("SOON") + `"
    ],
    "name": "` + _t("SOON arrow") + `",
    "shortcodes": [
        ":SOON_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔝",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("TOP") + `",
        "` + _t("up") + `"
    ],
    "name": "` + _t("TOP arrow") + `",
    "shortcodes": [
        ":TOP_arrow:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🛐",
    "emoticons": [],
    "keywords": [
        "` + _t("place of worship") + `",
        "` + _t("religion") + `",
        "` + _t("worship") + `"
    ],
    "name": "` + _t("place of worship") + `",
    "shortcodes": [
        ":place_of_worship:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚛️",
    "emoticons": [],
    "keywords": [
        "` + _t("atheist") + `",
        "` + _t("atom") + `",
        "` + _t("atom symbol") + `"
    ],
    "name": "` + _t("atom symbol") + `",
    "shortcodes": [
        ":atom_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🕉️",
    "emoticons": [],
    "keywords": [
        "` + _t("Hindu") + `",
        "` + _t("om") + `",
        "` + _t("religion") + `"
    ],
    "name": "` + _t("om") + `",
    "shortcodes": [
        ":om:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✡️",
    "emoticons": [],
    "keywords": [
        "` + _t("David") + `",
        "` + _t("Jew") + `",
        "` + _t("Jewish") + `",
        "` + _t("religion") + `",
        "` + _t("star") + `",
        "` + _t("star of David") + `",
        "` + _t("Judaism") + `",
        "` + _t("Star of David") + `"
    ],
    "name": "` + _t("star of David") + `",
    "shortcodes": [
        ":star_of_David:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☸️",
    "emoticons": [],
    "keywords": [
        "` + _t("Buddhist") + `",
        "` + _t("dharma") + `",
        "` + _t("religion") + `",
        "` + _t("wheel") + `",
        "` + _t("wheel of dharma") + `"
    ],
    "name": "` + _t("wheel of dharma") + `",
    "shortcodes": [
        ":wheel_of_dharma:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☯️",
    "emoticons": [],
    "keywords": [
        "` + _t("religion") + `",
        "` + _t("tao") + `",
        "` + _t("taoist") + `",
        "` + _t("yang") + `",
        "` + _t("yin") + `",
        "` + _t("Tao") + `",
        "` + _t("Taoist") + `"
    ],
    "name": "` + _t("yin yang") + `",
    "shortcodes": [
        ":yin_yang:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✝️",
    "emoticons": [],
    "keywords": [
        "` + _t("Christian") + `",
        "` + _t("cross") + `",
        "` + _t("religion") + `",
        "` + _t("latin cross") + `",
        "` + _t("Latin cross") + `"
    ],
    "name": "` + _t("latin cross") + `",
    "shortcodes": [
        ":latin_cross:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☦️",
    "emoticons": [],
    "keywords": [
        "` + _t("Christian") + `",
        "` + _t("cross") + `",
        "` + _t("orthodox cross") + `",
        "` + _t("religion") + `",
        "` + _t("Orthodox cross") + `"
    ],
    "name": "` + _t("orthodox cross") + `",
    "shortcodes": [
        ":orthodox_cross:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☪️",
    "emoticons": [],
    "keywords": [
        "` + _t("islam") + `",
        "` + _t("Muslim") + `",
        "` + _t("religion") + `",
        "` + _t("star and crescent") + `",
        "` + _t("Islam") + `"
    ],
    "name": "` + _t("star and crescent") + `",
    "shortcodes": [
        ":star_and_crescent:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☮️",
    "emoticons": [],
    "keywords": [
        "` + _t("peace") + `",
        "` + _t("peace symbol") + `"
    ],
    "name": "` + _t("peace symbol") + `",
    "shortcodes": [
        ":peace_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🕎",
    "emoticons": [],
    "keywords": [
        "` + _t("candelabrum") + `",
        "` + _t("candlestick") + `",
        "` + _t("menorah") + `",
        "` + _t("religion") + `"
    ],
    "name": "` + _t("menorah") + `",
    "shortcodes": [
        ":menorah:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔯",
    "emoticons": [],
    "keywords": [
        "` + _t("dotted six-pointed star") + `",
        "` + _t("fortune") + `",
        "` + _t("star") + `"
    ],
    "name": "` + _t("dotted six-pointed star") + `",
    "shortcodes": [
        ":dotted_six-pointed_star:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♈",
    "emoticons": [],
    "keywords": [
        "` + _t("Aries") + `",
        "` + _t("ram") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Aries") + `",
    "shortcodes": [
        ":Aries:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♉",
    "emoticons": [],
    "keywords": [
        "` + _t("bull") + `",
        "` + _t("ox") + `",
        "` + _t("Taurus") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Taurus") + `",
    "shortcodes": [
        ":Taurus:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♊",
    "emoticons": [],
    "keywords": [
        "` + _t("Gemini") + `",
        "` + _t("twins") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Gemini") + `",
    "shortcodes": [
        ":Gemini:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♋",
    "emoticons": [],
    "keywords": [
        "` + _t("Cancer") + `",
        "` + _t("crab") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Cancer") + `",
    "shortcodes": [
        ":Cancer:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♌",
    "emoticons": [],
    "keywords": [
        "` + _t("Leo") + `",
        "` + _t("lion") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Leo") + `",
    "shortcodes": [
        ":Leo:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♍",
    "emoticons": [],
    "keywords": [
        "` + _t("virgin") + `",
        "` + _t("Virgo") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Virgo") + `",
    "shortcodes": [
        ":Virgo:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♎",
    "emoticons": [],
    "keywords": [
        "` + _t("balance") + `",
        "` + _t("justice") + `",
        "` + _t("Libra") + `",
        "` + _t("scales") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Libra") + `",
    "shortcodes": [
        ":Libra:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♏",
    "emoticons": [],
    "keywords": [
        "` + _t("Scorpio") + `",
        "` + _t("scorpion") + `",
        "` + _t("scorpius") + `",
        "` + _t("zodiac") + `",
        "` + _t("Scorpius") + `"
    ],
    "name": "` + _t("Scorpio") + `",
    "shortcodes": [
        ":Scorpio:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♐",
    "emoticons": [],
    "keywords": [
        "` + _t("archer") + `",
        "` + _t("centaur") + `",
        "` + _t("Sagittarius") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Sagittarius") + `",
    "shortcodes": [
        ":Sagittarius:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♑",
    "emoticons": [],
    "keywords": [
        "` + _t("Capricorn") + `",
        "` + _t("goat") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Capricorn") + `",
    "shortcodes": [
        ":Capricorn:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♒",
    "emoticons": [],
    "keywords": [
        "` + _t("Aquarius") + `",
        "` + _t("water bearer") + `",
        "` + _t("zodiac") + `",
        "` + _t("bearer") + `",
        "` + _t("water") + `"
    ],
    "name": "` + _t("Aquarius") + `",
    "shortcodes": [
        ":Aquarius:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♓",
    "emoticons": [],
    "keywords": [
        "` + _t("fish") + `",
        "` + _t("Pisces") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Pisces") + `",
    "shortcodes": [
        ":Pisces:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⛎",
    "emoticons": [],
    "keywords": [
        "` + _t("bearer") + `",
        "` + _t("Ophiuchus") + `",
        "` + _t("serpent") + `",
        "` + _t("snake") + `",
        "` + _t("zodiac") + `"
    ],
    "name": "` + _t("Ophiuchus") + `",
    "shortcodes": [
        ":Ophiuchus:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔀",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("crossed") + `",
        "` + _t("shuffle tracks button") + `"
    ],
    "name": "` + _t("shuffle tracks button") + `",
    "shortcodes": [
        ":shuffle_tracks_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔁",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("clockwise") + `",
        "` + _t("repeat") + `",
        "` + _t("repeat button") + `"
    ],
    "name": "` + _t("repeat button") + `",
    "shortcodes": [
        ":repeat_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔂",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("clockwise") + `",
        "` + _t("once") + `",
        "` + _t("repeat single button") + `"
    ],
    "name": "` + _t("repeat single button") + `",
    "shortcodes": [
        ":repeat_single_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "▶️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("play") + `",
        "` + _t("play button") + `",
        "` + _t("right") + `",
        "` + _t("triangle") + `"
    ],
    "name": "` + _t("play button") + `",
    "shortcodes": [
        ":play_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏩",
    "emoticons": [],
    "keywords": [
        "` + _t("fast forward button") + `",
        "` + _t("arrow") + `",
        "` + _t("double") + `",
        "` + _t("fast") + `",
        "` + _t("fast-forward button") + `",
        "` + _t("forward") + `"
    ],
    "name": "` + _t("fast-forward button") + `",
    "shortcodes": [
        ":fast-forward_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏭️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("next scene") + `",
        "` + _t("next track") + `",
        "` + _t("next track button") + `",
        "` + _t("triangle") + `"
    ],
    "name": "` + _t("next track button") + `",
    "shortcodes": [
        ":next_track_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏯️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("pause") + `",
        "` + _t("play") + `",
        "` + _t("play or pause button") + `",
        "` + _t("right") + `",
        "` + _t("triangle") + `"
    ],
    "name": "` + _t("play or pause button") + `",
    "shortcodes": [
        ":play_or_pause_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◀️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("left") + `",
        "` + _t("reverse") + `",
        "` + _t("reverse button") + `",
        "` + _t("triangle") + `"
    ],
    "name": "` + _t("reverse button") + `",
    "shortcodes": [
        ":reverse_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏪",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("double") + `",
        "` + _t("fast reverse button") + `",
        "` + _t("rewind") + `"
    ],
    "name": "` + _t("fast reverse button") + `",
    "shortcodes": [
        ":fast_reverse_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏮️",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("last track button") + `",
        "` + _t("previous scene") + `",
        "` + _t("previous track") + `",
        "` + _t("triangle") + `"
    ],
    "name": "` + _t("last track button") + `",
    "shortcodes": [
        ":last_track_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔼",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("button") + `",
        "` + _t("red") + `",
        "` + _t("upwards button") + `",
        "` + _t("upward button") + `"
    ],
    "name": "` + _t("upwards button") + `",
    "shortcodes": [
        ":upwards_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏫",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("double") + `",
        "` + _t("fast up button") + `"
    ],
    "name": "` + _t("fast up button") + `",
    "shortcodes": [
        ":fast_up_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔽",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("button") + `",
        "` + _t("down") + `",
        "` + _t("downwards button") + `",
        "` + _t("red") + `",
        "` + _t("downward button") + `"
    ],
    "name": "` + _t("downwards button") + `",
    "shortcodes": [
        ":downwards_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏬",
    "emoticons": [],
    "keywords": [
        "` + _t("arrow") + `",
        "` + _t("double") + `",
        "` + _t("down") + `",
        "` + _t("fast down button") + `"
    ],
    "name": "` + _t("fast down button") + `",
    "shortcodes": [
        ":fast_down_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏸️",
    "emoticons": [],
    "keywords": [
        "` + _t("bar") + `",
        "` + _t("double") + `",
        "` + _t("pause") + `",
        "` + _t("pause button") + `",
        "` + _t("vertical") + `"
    ],
    "name": "` + _t("pause button") + `",
    "shortcodes": [
        ":pause_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏹️",
    "emoticons": [],
    "keywords": [
        "` + _t("square") + `",
        "` + _t("stop") + `",
        "` + _t("stop button") + `"
    ],
    "name": "` + _t("stop button") + `",
    "shortcodes": [
        ":stop_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏺️",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("record") + `",
        "` + _t("record button") + `"
    ],
    "name": "` + _t("record button") + `",
    "shortcodes": [
        ":record_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⏏️",
    "emoticons": [],
    "keywords": [
        "` + _t("eject") + `",
        "` + _t("eject button") + `"
    ],
    "name": "` + _t("eject button") + `",
    "shortcodes": [
        ":eject_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🎦",
    "emoticons": [],
    "keywords": [
        "` + _t("camera") + `",
        "` + _t("cinema") + `",
        "` + _t("film") + `",
        "` + _t("movie") + `"
    ],
    "name": "` + _t("cinema") + `",
    "shortcodes": [
        ":cinema:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔅",
    "emoticons": [],
    "keywords": [
        "` + _t("brightness") + `",
        "` + _t("dim") + `",
        "` + _t("dim button") + `",
        "` + _t("low") + `"
    ],
    "name": "` + _t("dim button") + `",
    "shortcodes": [
        ":dim_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔆",
    "emoticons": [],
    "keywords": [
        "` + _t("bright button") + `",
        "` + _t("brightness") + `",
        "` + _t("brightness button") + `",
        "` + _t("bright") + `"
    ],
    "name": "` + _t("bright button") + `",
    "shortcodes": [
        ":bright_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📶",
    "emoticons": [],
    "keywords": [
        "` + _t("antenna") + `",
        "` + _t("antenna bars") + `",
        "` + _t("bar") + `",
        "` + _t("cell") + `",
        "` + _t("mobile") + `",
        "` + _t("phone") + `"
    ],
    "name": "` + _t("antenna bars") + `",
    "shortcodes": [
        ":antenna_bars:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📳",
    "emoticons": [],
    "keywords": [
        "` + _t("cell") + `",
        "` + _t("mobile") + `",
        "` + _t("mode") + `",
        "` + _t("phone") + `",
        "` + _t("telephone") + `",
        "` + _t("vibration") + `",
        "` + _t("vibrate") + `"
    ],
    "name": "` + _t("vibration mode") + `",
    "shortcodes": [
        ":vibration_mode:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📴",
    "emoticons": [],
    "keywords": [
        "` + _t("cell") + `",
        "` + _t("mobile") + `",
        "` + _t("off") + `",
        "` + _t("phone") + `",
        "` + _t("telephone") + `"
    ],
    "name": "` + _t("mobile phone off") + `",
    "shortcodes": [
        ":mobile_phone_off:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♀️",
    "emoticons": [],
    "keywords": [
        "` + _t("female sign") + `",
        "` + _t("woman") + `"
    ],
    "name": "` + _t("female sign") + `",
    "shortcodes": [
        ":female_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♂️",
    "emoticons": [],
    "keywords": [
        "` + _t("male sign") + `",
        "` + _t("man") + `"
    ],
    "name": "` + _t("male sign") + `",
    "shortcodes": [
        ":male_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✖️",
    "emoticons": [],
    "keywords": [
        "` + _t("×") + `",
        "` + _t("cancel") + `",
        "` + _t("multiplication") + `",
        "` + _t("multiply") + `",
        "` + _t("sign") + `",
        "` + _t("x") + `",
        "` + _t("heavy multiplication sign") + `"
    ],
    "name": "` + _t("multiply") + `",
    "shortcodes": [
        ":multiply:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➕",
    "emoticons": [],
    "keywords": [
        "` + _t("+") + `",
        "` + _t("add") + `",
        "` + _t("addition") + `",
        "` + _t("math") + `",
        "` + _t("maths") + `",
        "` + _t("plus") + `",
        "` + _t("sign") + `"
    ],
    "name": "` + _t("plus") + `",
    "shortcodes": [
        ":plus:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➖",
    "emoticons": [],
    "keywords": [
        "` + _t("-") + `",
        "` + _t("–") + `",
        "` + _t("math") + `",
        "` + _t("maths") + `",
        "` + _t("minus") + `",
        "` + _t("sign") + `",
        "` + _t("subtraction") + `",
        "` + _t("−") + `",
        "` + _t("heavy minus sign") + `"
    ],
    "name": "` + _t("minus") + `",
    "shortcodes": [
        ":minus:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➗",
    "emoticons": [],
    "keywords": [
        "` + _t("÷") + `",
        "` + _t("divide") + `",
        "` + _t("division") + `",
        "` + _t("math") + `",
        "` + _t("sign") + `"
    ],
    "name": "` + _t("divide") + `",
    "shortcodes": [
        ":divide:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♾️",
    "emoticons": [],
    "keywords": [
        "` + _t("eternal") + `",
        "` + _t("forever") + `",
        "` + _t("infinity") + `",
        "` + _t("unbound") + `",
        "` + _t("universal") + `",
        "` + _t("unbounded") + `"
    ],
    "name": "` + _t("infinity") + `",
    "shortcodes": [
        ":infinity:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "‼️",
    "emoticons": [],
    "keywords": [
        "` + _t("double exclamation mark") + `",
        "` + _t("exclamation") + `",
        "` + _t("mark") + `",
        "` + _t("punctuation") + `",
        "` + _t("!") + `",
        "` + _t("!!") + `",
        "` + _t("bangbang") + `"
    ],
    "name": "` + _t("double exclamation mark") + `",
    "shortcodes": [
        ":double_exclamation_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⁉️",
    "emoticons": [],
    "keywords": [
        "` + _t("exclamation") + `",
        "` + _t("mark") + `",
        "` + _t("punctuation") + `",
        "` + _t("question") + `",
        "` + _t("!") + `",
        "` + _t("!?") + `",
        "` + _t("?") + `",
        "` + _t("interrobang") + `",
        "` + _t("exclamation question mark") + `"
    ],
    "name": "` + _t("exclamation question mark") + `",
    "shortcodes": [
        ":exclamation_question_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❓",
    "emoticons": [],
    "keywords": [
        "` + _t("?") + `",
        "` + _t("mark") + `",
        "` + _t("punctuation") + `",
        "` + _t("question") + `",
        "` + _t("red question mark") + `"
    ],
    "name": "` + _t("red question mark") + `",
    "shortcodes": [
        ":red_question_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❔",
    "emoticons": [],
    "keywords": [
        "` + _t("?") + `",
        "` + _t("mark") + `",
        "` + _t("outlined") + `",
        "` + _t("punctuation") + `",
        "` + _t("question") + `",
        "` + _t("white question mark") + `"
    ],
    "name": "` + _t("white question mark") + `",
    "shortcodes": [
        ":white_question_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❕",
    "emoticons": [],
    "keywords": [
        "` + _t("!") + `",
        "` + _t("exclamation") + `",
        "` + _t("mark") + `",
        "` + _t("outlined") + `",
        "` + _t("punctuation") + `",
        "` + _t("white exclamation mark") + `"
    ],
    "name": "` + _t("white exclamation mark") + `",
    "shortcodes": [
        ":white_exclamation_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❗",
    "emoticons": [],
    "keywords": [
        "` + _t("!") + `",
        "` + _t("exclamation") + `",
        "` + _t("mark") + `",
        "` + _t("punctuation") + `",
        "` + _t("red exclamation mark") + `"
    ],
    "name": "` + _t("red exclamation mark") + `",
    "shortcodes": [
        ":red_exclamation_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "〰️",
    "emoticons": [],
    "keywords": [
        "` + _t("dash") + `",
        "` + _t("punctuation") + `",
        "` + _t("wavy") + `"
    ],
    "name": "` + _t("wavy dash") + `",
    "shortcodes": [
        ":wavy_dash:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "💱",
    "emoticons": [],
    "keywords": [
        "` + _t("bank") + `",
        "` + _t("currency") + `",
        "` + _t("exchange") + `",
        "` + _t("money") + `"
    ],
    "name": "` + _t("currency exchange") + `",
    "shortcodes": [
        ":currency_exchange:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "💲",
    "emoticons": [],
    "keywords": [
        "` + _t("currency") + `",
        "` + _t("dollar") + `",
        "` + _t("heavy dollar sign") + `",
        "` + _t("money") + `"
    ],
    "name": "` + _t("heavy dollar sign") + `",
    "shortcodes": [
        ":heavy_dollar_sign:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚕️",
    "emoticons": [],
    "keywords": [
        "` + _t("aesculapius") + `",
        "` + _t("medical symbol") + `",
        "` + _t("medicine") + `",
        "` + _t("staff") + `"
    ],
    "name": "` + _t("medical symbol") + `",
    "shortcodes": [
        ":medical_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "♻️",
    "emoticons": [],
    "keywords": [
        "` + _t("recycle") + `",
        "` + _t("recycling symbol") + `"
    ],
    "name": "` + _t("recycling symbol") + `",
    "shortcodes": [
        ":recycling_symbol:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚜️",
    "emoticons": [],
    "keywords": [
        "` + _t("fleur-de-lis") + `"
    ],
    "name": "` + _t("fleur-de-lis") + `",
    "shortcodes": [
        ":fleur-de-lis:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔱",
    "emoticons": [],
    "keywords": [
        "` + _t("anchor") + `",
        "` + _t("emblem") + `",
        "` + _t("ship") + `",
        "` + _t("tool") + `",
        "` + _t("trident") + `"
    ],
    "name": "` + _t("trident emblem") + `",
    "shortcodes": [
        ":trident_emblem:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "📛",
    "emoticons": [],
    "keywords": [
        "` + _t("badge") + `",
        "` + _t("name") + `"
    ],
    "name": "` + _t("name badge") + `",
    "shortcodes": [
        ":name_badge:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔰",
    "emoticons": [],
    "keywords": [
        "` + _t("beginner") + `",
        "` + _t("chevron") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese symbol for beginner") + `",
        "` + _t("leaf") + `"
    ],
    "name": "` + _t("Japanese symbol for beginner") + `",
    "shortcodes": [
        ":Japanese_symbol_for_beginner:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⭕",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("hollow red circle") + `",
        "` + _t("large") + `",
        "` + _t("o") + `",
        "` + _t("red") + `"
    ],
    "name": "` + _t("hollow red circle") + `",
    "shortcodes": [
        ":hollow_red_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✅",
    "emoticons": [],
    "keywords": [
        "` + _t("✓") + `",
        "` + _t("button") + `",
        "` + _t("check") + `",
        "` + _t("mark") + `",
        "` + _t("tick") + `"
    ],
    "name": "` + _t("check mark button") + `",
    "shortcodes": [
        ":check_mark_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "☑️",
    "emoticons": [],
    "keywords": [
        "` + _t("ballot") + `",
        "` + _t("box") + `",
        "` + _t("check box with check") + `",
        "` + _t("tick") + `",
        "` + _t("tick box with tick") + `",
        "` + _t("✓") + `",
        "` + _t("check") + `"
    ],
    "name": "` + _t("check box with check") + `",
    "shortcodes": [
        ":check_box_with_check:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✔️",
    "emoticons": [],
    "keywords": [
        "` + _t("check mark") + `",
        "` + _t("heavy tick mark") + `",
        "` + _t("mark") + `",
        "` + _t("tick") + `",
        "` + _t("✓") + `",
        "` + _t("check") + `"
    ],
    "name": "` + _t("check mark") + `",
    "shortcodes": [
        ":check_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❌",
    "emoticons": [],
    "keywords": [
        "` + _t("×") + `",
        "` + _t("cancel") + `",
        "` + _t("cross") + `",
        "` + _t("mark") + `",
        "` + _t("multiplication") + `",
        "` + _t("multiply") + `",
        "` + _t("x") + `"
    ],
    "name": "` + _t("cross mark") + `",
    "shortcodes": [
        ":cross_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❎",
    "emoticons": [],
    "keywords": [
        "` + _t("×") + `",
        "` + _t("cross mark button") + `",
        "` + _t("mark") + `",
        "` + _t("square") + `",
        "` + _t("x") + `"
    ],
    "name": "` + _t("cross mark button") + `",
    "shortcodes": [
        ":cross_mark_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➰",
    "emoticons": [],
    "keywords": [
        "` + _t("curl") + `",
        "` + _t("curly loop") + `",
        "` + _t("loop") + `"
    ],
    "name": "` + _t("curly loop") + `",
    "shortcodes": [
        ":curly_loop:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "➿",
    "emoticons": [],
    "keywords": [
        "` + _t("curl") + `",
        "` + _t("double") + `",
        "` + _t("double curly loop") + `",
        "` + _t("loop") + `"
    ],
    "name": "` + _t("double curly loop") + `",
    "shortcodes": [
        ":double_curly_loop:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "〽️",
    "emoticons": [],
    "keywords": [
        "` + _t("mark") + `",
        "` + _t("part") + `",
        "` + _t("part alternation mark") + `"
    ],
    "name": "` + _t("part alternation mark") + `",
    "shortcodes": [
        ":part_alternation_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✳️",
    "emoticons": [],
    "keywords": [
        "` + _t("*") + `",
        "` + _t("asterisk") + `",
        "` + _t("eight-spoked asterisk") + `"
    ],
    "name": "` + _t("eight-spoked asterisk") + `",
    "shortcodes": [
        ":eight-spoked_asterisk:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "✴️",
    "emoticons": [],
    "keywords": [
        "` + _t("*") + `",
        "` + _t("eight-pointed star") + `",
        "` + _t("star") + `"
    ],
    "name": "` + _t("eight-pointed star") + `",
    "shortcodes": [
        ":eight-pointed_star:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "❇️",
    "emoticons": [],
    "keywords": [
        "` + _t("*") + `",
        "` + _t("sparkle") + `"
    ],
    "name": "` + _t("sparkle") + `",
    "shortcodes": [
        ":sparkle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "©️",
    "emoticons": [],
    "keywords": [
        "` + _t("C") + `",
        "` + _t("copyright") + `"
    ],
    "name": "` + _t("copyright") + `",
    "shortcodes": [
        ":copyright:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "®️",
    "emoticons": [],
    "keywords": [
        "` + _t("R") + `",
        "` + _t("registered") + `",
        "` + _t("r") + `",
        "` + _t("trademark") + `"
    ],
    "name": "` + _t("registered") + `",
    "shortcodes": [
        ":registered:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "™️",
    "emoticons": [],
    "keywords": [
        "` + _t("mark") + `",
        "` + _t("TM") + `",
        "` + _t("trade mark") + `",
        "` + _t("trademark") + `"
    ],
    "name": "` + _t("trade mark") + `",
    "shortcodes": [
        ":trade_mark:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "#️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: #") + `",
    "shortcodes": [
        ":keycap:_#:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "*️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: *") + `",
    "shortcodes": [
        ":keycap:_*:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "0️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 0") + `",
    "shortcodes": [
        ":keycap:_0:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "1️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 1") + `",
    "shortcodes": [
        ":keycap:_1:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "2️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 2") + `",
    "shortcodes": [
        ":keycap:_2:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "3️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 3") + `",
    "shortcodes": [
        ":keycap:_3:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "4️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 4") + `",
    "shortcodes": [
        ":keycap:_4:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "5️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 5") + `",
    "shortcodes": [
        ":keycap:_5:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "6️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 6") + `",
    "shortcodes": [
        ":keycap:_6:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "7️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 7") + `",
    "shortcodes": [
        ":keycap:_7:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "8️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 8") + `",
    "shortcodes": [
        ":keycap:_8:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "9️⃣",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 9") + `",
    "shortcodes": [
        ":keycap:_9:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔟",
    "emoticons": [],
    "keywords": [
        "` + _t("keycap") + `"
    ],
    "name": "` + _t("keycap: 10") + `",
    "shortcodes": [
        ":keycap:_10:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔠",
    "emoticons": [],
    "keywords": [
        "` + _t("input Latin uppercase") + `",
        "` + _t("ABCD") + `",
        "` + _t("input") + `",
        "` + _t("latin") + `",
        "` + _t("letters") + `",
        "` + _t("uppercase") + `",
        "` + _t("Latin") + `"
    ],
    "name": "` + _t("input latin uppercase") + `",
    "shortcodes": [
        ":input_latin_uppercase:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔡",
    "emoticons": [],
    "keywords": [
        "` + _t("input Latin lowercase") + `",
        "` + _t("abcd") + `",
        "` + _t("input") + `",
        "` + _t("latin") + `",
        "` + _t("letters") + `",
        "` + _t("lowercase") + `",
        "` + _t("Latin") + `"
    ],
    "name": "` + _t("input latin lowercase") + `",
    "shortcodes": [
        ":input_latin_lowercase:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔢",
    "emoticons": [],
    "keywords": [
        "` + _t("1234") + `",
        "` + _t("input") + `",
        "` + _t("numbers") + `"
    ],
    "name": "` + _t("input numbers") + `",
    "shortcodes": [
        ":input_numbers:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔣",
    "emoticons": [],
    "keywords": [
        "` + _t("〒♪&%") + `",
        "` + _t("input") + `",
        "` + _t("input symbols") + `"
    ],
    "name": "` + _t("input symbols") + `",
    "shortcodes": [
        ":input_symbols:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔤",
    "emoticons": [],
    "keywords": [
        "` + _t("input Latin letters") + `",
        "` + _t("abc") + `",
        "` + _t("alphabet") + `",
        "` + _t("input") + `",
        "` + _t("latin") + `",
        "` + _t("letters") + `",
        "` + _t("Latin") + `"
    ],
    "name": "` + _t("input latin letters") + `",
    "shortcodes": [
        ":input_latin_letters:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🅰️",
    "emoticons": [],
    "keywords": [
        "` + _t("A") + `",
        "` + _t("A button (blood type)") + `",
        "` + _t("blood type") + `"
    ],
    "name": "` + _t("A button (blood type)") + `",
    "shortcodes": [
        ":A_button_(blood_type):"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆎",
    "emoticons": [],
    "keywords": [
        "` + _t("AB") + `",
        "` + _t("AB button (blood type)") + `",
        "` + _t("blood type") + `"
    ],
    "name": "` + _t("AB button (blood type)") + `",
    "shortcodes": [
        ":AB_button_(blood_type):"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🅱️",
    "emoticons": [],
    "keywords": [
        "` + _t("B") + `",
        "` + _t("B button (blood type)") + `",
        "` + _t("blood type") + `"
    ],
    "name": "` + _t("B button (blood type)") + `",
    "shortcodes": [
        ":B_button_(blood_type):"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆑",
    "emoticons": [],
    "keywords": [
        "` + _t("CL") + `",
        "` + _t("CL button") + `"
    ],
    "name": "` + _t("CL button") + `",
    "shortcodes": [
        ":CL_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆒",
    "emoticons": [],
    "keywords": [
        "` + _t("COOL") + `",
        "` + _t("COOL button") + `"
    ],
    "name": "` + _t("COOL button") + `",
    "shortcodes": [
        ":COOL_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆓",
    "emoticons": [],
    "keywords": [
        "` + _t("FREE") + `",
        "` + _t("FREE button") + `"
    ],
    "name": "` + _t("FREE button") + `",
    "shortcodes": [
        ":FREE_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "ℹ️",
    "emoticons": [],
    "keywords": [
        "` + _t("i") + `",
        "` + _t("information") + `"
    ],
    "name": "` + _t("information") + `",
    "shortcodes": [
        ":information:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆔",
    "emoticons": [],
    "keywords": [
        "` + _t("ID") + `",
        "` + _t("ID button") + `",
        "` + _t("identity") + `"
    ],
    "name": "` + _t("ID button") + `",
    "shortcodes": [
        ":ID_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "Ⓜ️",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("circled M") + `",
        "` + _t("M") + `"
    ],
    "name": "` + _t("circled M") + `",
    "shortcodes": [
        ":circled_M:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆕",
    "emoticons": [],
    "keywords": [
        "` + _t("NEW") + `",
        "` + _t("NEW button") + `"
    ],
    "name": "` + _t("NEW button") + `",
    "shortcodes": [
        ":NEW_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆖",
    "emoticons": [],
    "keywords": [
        "` + _t("NG") + `",
        "` + _t("NG button") + `"
    ],
    "name": "` + _t("NG button") + `",
    "shortcodes": [
        ":NG_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🅾️",
    "emoticons": [],
    "keywords": [
        "` + _t("blood type") + `",
        "` + _t("O") + `",
        "` + _t("O button (blood type)") + `"
    ],
    "name": "` + _t("O button (blood type)") + `",
    "shortcodes": [
        ":O_button_(blood_type):"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆗",
    "emoticons": [],
    "keywords": [
        "` + _t("OK") + `",
        "` + _t("OK button") + `"
    ],
    "name": "` + _t("OK button") + `",
    "shortcodes": [
        ":OK_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🅿️",
    "emoticons": [],
    "keywords": [
        "` + _t("P") + `",
        "` + _t("P button") + `",
        "` + _t("parking") + `"
    ],
    "name": "` + _t("P button") + `",
    "shortcodes": [
        ":P_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆘",
    "emoticons": [],
    "keywords": [
        "` + _t("help") + `",
        "` + _t("SOS") + `",
        "` + _t("SOS button") + `"
    ],
    "name": "` + _t("SOS button") + `",
    "shortcodes": [
        ":SOS_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆙",
    "emoticons": [],
    "keywords": [
        "` + _t("mark") + `",
        "` + _t("UP") + `",
        "` + _t("UP!") + `",
        "` + _t("UP! button") + `"
    ],
    "name": "` + _t("UP! button") + `",
    "shortcodes": [
        ":UP!_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🆚",
    "emoticons": [],
    "keywords": [
        "` + _t("versus") + `",
        "` + _t("VS") + `",
        "` + _t("VS button") + `"
    ],
    "name": "` + _t("VS button") + `",
    "shortcodes": [
        ":VS_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈁",
    "emoticons": [],
    "keywords": [
        "` + _t("“here”") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “here” button") + `",
        "` + _t("katakana") + `",
        "` + _t("ココ") + `"
    ],
    "name": "` + _t("Japanese “here” button") + `",
    "shortcodes": [
        ":Japanese_“here”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈂️",
    "emoticons": [],
    "keywords": [
        "` + _t("“service charge”") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “service charge” button") + `",
        "` + _t("katakana") + `",
        "` + _t("サ") + `"
    ],
    "name": "` + _t("Japanese “service charge” button") + `",
    "shortcodes": [
        ":Japanese_“service_charge”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈷️",
    "emoticons": [],
    "keywords": [
        "` + _t("“monthly amount”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “monthly amount” button") + `",
        "` + _t("月") + `"
    ],
    "name": "` + _t("Japanese “monthly amount” button") + `",
    "shortcodes": [
        ":Japanese_“monthly_amount”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈶",
    "emoticons": [],
    "keywords": [
        "` + _t("“not free of charge”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “not free of charge” button") + `",
        "` + _t("有") + `"
    ],
    "name": "` + _t("Japanese “not free of charge” button") + `",
    "shortcodes": [
        ":Japanese_“not_free_of_charge”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈯",
    "emoticons": [],
    "keywords": [
        "` + _t("“reserved”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “reserved” button") + `",
        "` + _t("指") + `"
    ],
    "name": "` + _t("Japanese “reserved” button") + `",
    "shortcodes": [
        ":Japanese_“reserved”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🉐",
    "emoticons": [],
    "keywords": [
        "` + _t("“bargain”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “bargain” button") + `",
        "` + _t("得") + `"
    ],
    "name": "` + _t("Japanese “bargain” button") + `",
    "shortcodes": [
        ":Japanese_“bargain”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈹",
    "emoticons": [],
    "keywords": [
        "` + _t("“discount”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “discount” button") + `",
        "` + _t("割") + `"
    ],
    "name": "` + _t("Japanese “discount” button") + `",
    "shortcodes": [
        ":Japanese_“discount”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈚",
    "emoticons": [],
    "keywords": [
        "` + _t("“free of charge”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “free of charge” button") + `",
        "` + _t("無") + `"
    ],
    "name": "` + _t("Japanese “free of charge” button") + `",
    "shortcodes": [
        ":Japanese_“free_of_charge”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈲",
    "emoticons": [],
    "keywords": [
        "` + _t("“prohibited”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “prohibited” button") + `",
        "` + _t("禁") + `"
    ],
    "name": "` + _t("Japanese “prohibited” button") + `",
    "shortcodes": [
        ":Japanese_“prohibited”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🉑",
    "emoticons": [],
    "keywords": [
        "` + _t("“acceptable”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “acceptable” button") + `",
        "` + _t("可") + `"
    ],
    "name": "` + _t("Japanese “acceptable” button") + `",
    "shortcodes": [
        ":Japanese_“acceptable”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈸",
    "emoticons": [],
    "keywords": [
        "` + _t("“application”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “application” button") + `",
        "` + _t("申") + `"
    ],
    "name": "` + _t("Japanese “application” button") + `",
    "shortcodes": [
        ":Japanese_“application”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈴",
    "emoticons": [],
    "keywords": [
        "` + _t("“passing grade”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “passing grade” button") + `",
        "` + _t("合") + `"
    ],
    "name": "` + _t("Japanese “passing grade” button") + `",
    "shortcodes": [
        ":Japanese_“passing_grade”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈳",
    "emoticons": [],
    "keywords": [
        "` + _t("“vacancy”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “vacancy” button") + `",
        "` + _t("空") + `"
    ],
    "name": "` + _t("Japanese “vacancy” button") + `",
    "shortcodes": [
        ":Japanese_“vacancy”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "㊗️",
    "emoticons": [],
    "keywords": [
        "` + _t("“congratulations”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “congratulations” button") + `",
        "` + _t("祝") + `"
    ],
    "name": "` + _t("Japanese “congratulations” button") + `",
    "shortcodes": [
        ":Japanese_“congratulations”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "㊙️",
    "emoticons": [],
    "keywords": [
        "` + _t("“secret”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “secret” button") + `",
        "` + _t("秘") + `"
    ],
    "name": "` + _t("Japanese “secret” button") + `",
    "shortcodes": [
        ":Japanese_“secret”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈺",
    "emoticons": [],
    "keywords": [
        "` + _t("“open for business”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “open for business” button") + `",
        "` + _t("営") + `"
    ],
    "name": "` + _t("Japanese “open for business” button") + `",
    "shortcodes": [
        ":Japanese_“open_for_business”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🈵",
    "emoticons": [],
    "keywords": [
        "` + _t("“no vacancy”") + `",
        "` + _t("ideograph") + `",
        "` + _t("Japanese") + `",
        "` + _t("Japanese “no vacancy” button") + `",
        "` + _t("満") + `"
    ],
    "name": "` + _t("Japanese “no vacancy” button") + `",
    "shortcodes": [
        ":Japanese_“no_vacancy”_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔴",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("geometric") + `",
        "` + _t("red") + `"
    ],
    "name": "` + _t("red circle") + `",
    "shortcodes": [
        ":red_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟠",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("orange") + `"
    ],
    "name": "` + _t("orange circle") + `",
    "shortcodes": [
        ":orange_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟡",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("yellow") + `"
    ],
    "name": "` + _t("yellow circle") + `",
    "shortcodes": [
        ":yellow_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟢",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("green") + `"
    ],
    "name": "` + _t("green circle") + `",
    "shortcodes": [
        ":green_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔵",
    "emoticons": [],
    "keywords": [
        "` + _t("blue") + `",
        "` + _t("circle") + `",
        "` + _t("geometric") + `"
    ],
    "name": "` + _t("blue circle") + `",
    "shortcodes": [
        ":blue_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟣",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("purple") + `"
    ],
    "name": "` + _t("purple circle") + `",
    "shortcodes": [
        ":purple_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟤",
    "emoticons": [],
    "keywords": [
        "` + _t("brown") + `",
        "` + _t("circle") + `"
    ],
    "name": "` + _t("brown circle") + `",
    "shortcodes": [
        ":brown_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚫",
    "emoticons": [],
    "keywords": [
        "` + _t("black circle") + `",
        "` + _t("circle") + `",
        "` + _t("geometric") + `"
    ],
    "name": "` + _t("black circle") + `",
    "shortcodes": [
        ":black_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⚪",
    "emoticons": [],
    "keywords": [
        "` + _t("circle") + `",
        "` + _t("geometric") + `",
        "` + _t("white circle") + `"
    ],
    "name": "` + _t("white circle") + `",
    "shortcodes": [
        ":white_circle:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟥",
    "emoticons": [],
    "keywords": [
        "` + _t("red") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("red square") + `",
    "shortcodes": [
        ":red_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟧",
    "emoticons": [],
    "keywords": [
        "` + _t("orange") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("orange square") + `",
    "shortcodes": [
        ":orange_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟨",
    "emoticons": [],
    "keywords": [
        "` + _t("square") + `",
        "` + _t("yellow") + `"
    ],
    "name": "` + _t("yellow square") + `",
    "shortcodes": [
        ":yellow_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟩",
    "emoticons": [],
    "keywords": [
        "` + _t("green") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("green square") + `",
    "shortcodes": [
        ":green_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟦",
    "emoticons": [],
    "keywords": [
        "` + _t("blue") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("blue square") + `",
    "shortcodes": [
        ":blue_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟪",
    "emoticons": [],
    "keywords": [
        "` + _t("purple") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("purple square") + `",
    "shortcodes": [
        ":purple_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🟫",
    "emoticons": [],
    "keywords": [
        "` + _t("brown") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("brown square") + `",
    "shortcodes": [
        ":brown_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬛",
    "emoticons": [],
    "keywords": [
        "` + _t("black large square") + `",
        "` + _t("geometric") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("black large square") + `",
    "shortcodes": [
        ":black_large_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "⬜",
    "emoticons": [],
    "keywords": [
        "` + _t("geometric") + `",
        "` + _t("square") + `",
        "` + _t("white large square") + `"
    ],
    "name": "` + _t("white large square") + `",
    "shortcodes": [
        ":white_large_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◼️",
    "emoticons": [],
    "keywords": [
        "` + _t("black medium square") + `",
        "` + _t("geometric") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("black medium square") + `",
    "shortcodes": [
        ":black_medium_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◻️",
    "emoticons": [],
    "keywords": [
        "` + _t("geometric") + `",
        "` + _t("square") + `",
        "` + _t("white medium square") + `"
    ],
    "name": "` + _t("white medium square") + `",
    "shortcodes": [
        ":white_medium_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◾",
    "emoticons": [],
    "keywords": [
        "` + _t("black medium-small square") + `",
        "` + _t("geometric") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("black medium-small square") + `",
    "shortcodes": [
        ":black_medium-small_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "◽",
    "emoticons": [],
    "keywords": [
        "` + _t("geometric") + `",
        "` + _t("square") + `",
        "` + _t("white medium-small square") + `"
    ],
    "name": "` + _t("white medium-small square") + `",
    "shortcodes": [
        ":white_medium-small_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "▪️",
    "emoticons": [],
    "keywords": [
        "` + _t("black small square") + `",
        "` + _t("geometric") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("black small square") + `",
    "shortcodes": [
        ":black_small_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "▫️",
    "emoticons": [],
    "keywords": [
        "` + _t("geometric") + `",
        "` + _t("square") + `",
        "` + _t("white small square") + `"
    ],
    "name": "` + _t("white small square") + `",
    "shortcodes": [
        ":white_small_square:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔶",
    "emoticons": [],
    "keywords": [
        "` + _t("diamond") + `",
        "` + _t("geometric") + `",
        "` + _t("large orange diamond") + `",
        "` + _t("orange") + `"
    ],
    "name": "` + _t("large orange diamond") + `",
    "shortcodes": [
        ":large_orange_diamond:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔷",
    "emoticons": [],
    "keywords": [
        "` + _t("blue") + `",
        "` + _t("diamond") + `",
        "` + _t("geometric") + `",
        "` + _t("large blue diamond") + `"
    ],
    "name": "` + _t("large blue diamond") + `",
    "shortcodes": [
        ":large_blue_diamond:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔸",
    "emoticons": [],
    "keywords": [
        "` + _t("diamond") + `",
        "` + _t("geometric") + `",
        "` + _t("orange") + `",
        "` + _t("small orange diamond") + `"
    ],
    "name": "` + _t("small orange diamond") + `",
    "shortcodes": [
        ":small_orange_diamond:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔹",
    "emoticons": [],
    "keywords": [
        "` + _t("blue") + `",
        "` + _t("diamond") + `",
        "` + _t("geometric") + `",
        "` + _t("small blue diamond") + `"
    ],
    "name": "` + _t("small blue diamond") + `",
    "shortcodes": [
        ":small_blue_diamond:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔺",
    "emoticons": [],
    "keywords": [
        "` + _t("geometric") + `",
        "` + _t("red") + `",
        "` + _t("red triangle pointed up") + `"
    ],
    "name": "` + _t("red triangle pointed up") + `",
    "shortcodes": [
        ":red_triangle_pointed_up:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔻",
    "emoticons": [],
    "keywords": [
        "` + _t("down") + `",
        "` + _t("geometric") + `",
        "` + _t("red") + `",
        "` + _t("red triangle pointed down") + `"
    ],
    "name": "` + _t("red triangle pointed down") + `",
    "shortcodes": [
        ":red_triangle_pointed_down:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "💠",
    "emoticons": [],
    "keywords": [
        "` + _t("comic") + `",
        "` + _t("diamond") + `",
        "` + _t("diamond with a dot") + `",
        "` + _t("geometric") + `",
        "` + _t("inside") + `"
    ],
    "name": "` + _t("diamond with a dot") + `",
    "shortcodes": [
        ":diamond_with_a_dot:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔘",
    "emoticons": [],
    "keywords": [
        "` + _t("button") + `",
        "` + _t("geometric") + `",
        "` + _t("radio") + `"
    ],
    "name": "` + _t("radio button") + `",
    "shortcodes": [
        ":radio_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔳",
    "emoticons": [],
    "keywords": [
        "` + _t("button") + `",
        "` + _t("geometric") + `",
        "` + _t("outlined") + `",
        "` + _t("square") + `",
        "` + _t("white square button") + `"
    ],
    "name": "` + _t("white square button") + `",
    "shortcodes": [
        ":white_square_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🔲",
    "emoticons": [],
    "keywords": [
        "` + _t("black square button") + `",
        "` + _t("button") + `",
        "` + _t("geometric") + `",
        "` + _t("square") + `"
    ],
    "name": "` + _t("black square button") + `",
    "shortcodes": [
        ":black_square_button:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏁",
    "emoticons": [],
    "keywords": [
        "` + _t("checkered") + `",
        "` + _t("chequered") + `",
        "` + _t("chequered flag") + `",
        "` + _t("racing") + `",
        "` + _t("checkered flag") + `"
    ],
    "name": "` + _t("chequered flag") + `",
    "shortcodes": [
        ":chequered_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🚩",
    "emoticons": [],
    "keywords": [
        "` + _t("post") + `",
        "` + _t("triangular flag") + `",
        "` + _t("red flag") + `"
    ],
    "name": "` + _t("triangular flag") + `",
    "shortcodes": [
        ":triangular_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🎌",
    "emoticons": [],
    "keywords": [
        "` + _t("celebration") + `",
        "` + _t("cross") + `",
        "` + _t("crossed") + `",
        "` + _t("crossed flags") + `",
        "` + _t("Japanese") + `"
    ],
    "name": "` + _t("crossed flags") + `",
    "shortcodes": [
        ":crossed_flags:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴",
    "emoticons": [],
    "keywords": [
        "` + _t("black flag") + `",
        "` + _t("waving") + `"
    ],
    "name": "` + _t("black flag") + `",
    "shortcodes": [
        ":black_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏳️",
    "emoticons": [],
    "keywords": [
        "` + _t("waving") + `",
        "` + _t("white flag") + `",
        "` + _t("surrender") + `"
    ],
    "name": "` + _t("white flag") + `",
    "shortcodes": [
        ":white_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏳️‍🌈",
    "emoticons": [],
    "keywords": [
        "` + _t("pride") + `",
        "` + _t("rainbow") + `",
        "` + _t("rainbow flag") + `"
    ],
    "name": "` + _t("rainbow flag") + `",
    "shortcodes": [
        ":rainbow_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴‍☠️",
    "emoticons": [],
    "keywords": [
        "` + _t("Jolly Roger") + `",
        "` + _t("pirate") + `",
        "` + _t("pirate flag") + `",
        "` + _t("plunder") + `",
        "` + _t("treasure") + `"
    ],
    "name": "` + _t("pirate flag") + `",
    "shortcodes": [
        ":pirate_flag:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "emoticons": [],
    "keywords": [
        "` + _t("flag") + `"
    ],
    "name": "` + _t("flag: England") + `",
    "shortcodes": [
        ":england:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "emoticons": [],
    "keywords": [
        "` + _t("flag") + `"
    ],
    "name": "` + _t("flag: Scotland") + `",
    "shortcodes": [
        ":scotland:"
    ]
},
{
    "category": "Symbols",
    "codepoints": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "emoticons": [],
    "keywords": [
        "` + _t("flag") + `"
    ],
    "name": "` + _t("flag: Wales") + `",
    "shortcodes": [
        ":wales:"
    ]
}`;

/** @type {string} */
let parsedCategories;
/** @type {string} */
let parsedEmojis;

export function getEmojis() {
    if (!parsedEmojis) {
        parsedEmojis = JSON.parse(`[
            ${_getEmojisData1()}
            ${_getEmojisData2()}
            ${_getEmojisData3()}
            ${_getEmojisData4()}
            ${_getEmojisData5()}
            ${_getEmojisData6()}
            ${_getEmojisData7()}
            ${_getEmojisData8()}
        ]`);
    }
    return parsedEmojis;
}

export function getCategories() {
    if (!parsedCategories) {
        parsedCategories = JSON.parse(_getCategories());
    }
    return parsedCategories;
}
