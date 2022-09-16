/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/throttle';

patchRecordMethods('EmojiRegistry', {
    async _populateFromEmojiData() {
        const dataEmojiCategories = [
        {
            "name": "Smileys & Emotion",
            "title": "🤠",
            "sortId": 1
        },
        {
            "name": "People & Body",
            "title": "🤟",
            "sortId": 2
        }];
        const dataEmojis = [
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
        ];
        this._super(dataEmojiCategories, dataEmojis);
    },
});
