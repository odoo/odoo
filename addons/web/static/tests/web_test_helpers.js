import { before } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { loadBundle } from "@web/core/assets";
import * as _fields from "./_framework/mock_server/mock_fields";
import * as _models from "./_framework/mock_server/mock_model";
import { IrAttachment } from "./_framework/mock_server/mock_models/ir_attachment";
import { IrModel } from "./_framework/mock_server/mock_models/ir_model";
import { IrModelAccess } from "./_framework/mock_server/mock_models/ir_model_access";
import { IrModelFields } from "./_framework/mock_server/mock_models/ir_model_fields";
import { IrRule } from "./_framework/mock_server/mock_models/ir_rule";
import { IrUiView } from "./_framework/mock_server/mock_models/ir_ui_view";
import { ResCompany } from "./_framework/mock_server/mock_models/res_company";
import { ResCountry } from "./_framework/mock_server/mock_models/res_country";
import { ResCurrency } from "./_framework/mock_server/mock_models/res_currency";
import { ResGroups } from "./_framework/mock_server/mock_models/res_groups";
import { ResPartner } from "./_framework/mock_server/mock_models/res_partner";
import { ResUsers } from "./_framework/mock_server/mock_models/res_users";
import { defineModels, onRpc } from "./_framework/mock_server/mock_server";
import { globalCachedFetch } from "./_framework/module_set.hoot";

/**
 * @typedef {import("./_framework/mock_server/mock_fields").FieldType} FieldType
 * @typedef {import("./_framework/mock_server/mock_model").ModelRecord} ModelRecord
 */

/**
 * @template T
 * @typedef {import("./_framework/mock_server/mock_server").KwArgs<T>} KwArgs
 */

/**
 * @template T
 * @typedef {import("./_framework/mock_server/mock_server").RouteCallback<T>} RouteCallback
 */

export { asyncStep, waitForSteps } from "./_framework/async_step";
export {
    findComponent,
    getDropdownMenu,
    mountWithCleanup,
} from "./_framework/component_test_helpers";
export { contains, defineStyle, editAce } from "./_framework/dom_test_helpers";
export {
    clearRegistry,
    getMockEnv,
    getService,
    makeDialogMockEnv,
    makeMockEnv,
    mockService,
    restoreRegistry,
} from "./_framework/env_test_helpers";
export {
    clickKanbanLoadMore,
    clickKanbanRecord,
    createKanbanRecord,
    discardKanbanRecord,
    editKanbanColumnName,
    editKanbanRecord,
    editKanbanRecordQuickCreateInput,
    getKanbanColumn,
    getKanbanColumnDropdownMenu,
    getKanbanColumnTooltips,
    getKanbanCounters,
    getKanbanProgressBars,
    getKanbanRecord,
    getKanbanRecordTexts,
    quickCreateKanbanColumn,
    quickCreateKanbanRecord,
    toggleKanbanColumnActions,
    toggleKanbanRecordDropdown,
    validateKanbanColumn,
    validateKanbanRecord,
} from "./_framework/kanban_test_helpers";
export { Command } from "./_framework/mock_server/mock_model";
export {
    authenticate,
    defineActions,
    defineEmbeddedActions,
    defineMenus,
    defineModels,
    defineParams,
    logout,
    makeMockServer,
    MockServer,
    onRpc,
    stepAllNetworkCalls,
    withUser,
} from "./_framework/mock_server/mock_server";
export {
    getKwArgs,
    makeKwArgs,
    makeServerError,
    MockServerError,
    unmakeKwArgs,
} from "./_framework/mock_server/mock_server_utils";
export { serverState } from "./_framework/mock_server_state.hoot";
export { patchWithCleanup } from "./_framework/patch_test_helpers";
export { preventResizeObserverError } from "./_framework/resize_observer_error_catcher";
export {
    editFavorite,
    editFavoriteName,
    editPager,
    editSearch,
    getButtons,
    getFacetTexts,
    getMenuItemTexts,
    getPagerLimit,
    getPagerValue,
    getVisibleButtons,
    isItemSelected,
    isOptionSelected,
    mountWithSearch,
    openAddCustomFilterDialog,
    pagerNext,
    pagerPrevious,
    removeFacet,
    saveFavorite,
    selectGroup,
    switchView,
    toggleActionMenu,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
    toggleSearchBarMenu,
    validateSearch,
} from "./_framework/search_test_helpers";
export { swipeLeft, swipeRight } from "./_framework/touch_helpers";
export { installLanguages, patchTranslations } from "./_framework/translation_test_helpers";
export {
    clickButton,
    clickCancel,
    clickFieldDropdown,
    clickFieldDropdownItem,
    clickModalButton,
    clickSave,
    clickViewButton,
    expectMarkup,
    fieldInput,
    hideTab,
    mountView,
    mountViewInDialog,
    parseViewProps,
    selectFieldDropdownItem,
} from "./_framework/view_test_helpers";
export { mountWebClient, useTestClientAction } from "./_framework/webclient_test_helpers";

export function defineWebModels() {
    return defineModels(webModels);
}

/**
 * @param {string} bundleName
 */
export function preloadBundle(bundleName) {
    before(async function preloadBundle() {
        mockFetch(globalCachedFetch);
        await loadBundle(bundleName);
        mockFetch(null);
    });
}

export const fields = _fields;
export const models = _models;

export const webModels = {
    IrAttachment,
    IrModel,
    IrModelAccess,
    IrModelFields,
    IrRule,
    IrUiView,
    ResCompany,
    ResCountry,
    ResCurrency,
    ResGroups,
    ResPartner,
    ResUsers,
};

export function mockEmojiLoading() {
    onRpc("/load_emoji_bundle", () => {
        return {
            path: "/web/static/src/core/emoji_picker/emoji_data/test.json",
        };
    });

    onRpc("/web/static/src/core/emoji_picker/emoji_data/test.json", () => {
        return {
            "😀": {
                "keywords": [
                    "cheerful",
                    "cheery",
                    "face",
                    "grin",
                    "grinning",
                    "happy",
                    "laugh",
                    "nice",
                    "smile",
                    "smiling",
                    "teeth"
                ],
                "name": "grinning face"
            },
            "😃": {
                "keywords": [
                    "awesome",
                    "big",
                    "eyes",
                    "face",
                    "grin",
                    "grinning",
                    "happy",
                    "mouth",
                    "open",
                    "smile",
                    "smiling",
                    "teeth",
                    "yay"
                ],
                "name": "grinning face with big eyes"
            },
            "😛": {
                "keywords": [
                    "awesome",
                    "cool",
                    "face",
                    "nice",
                    "party",
                    "stuck-out",
                    "sweet",
                    "tongue"
                ],
                "name": "face with tongue"
            },
            "😆": {
                "keywords": [
                    "closed",
                    "eyes",
                    "face",
                    "grinning",
                    "haha",
                    "hahaha",
                    "happy",
                    "laugh",
                    "lol",
                    "mouth",
                    "open",
                    "rofl",
                    "smile",
                    "smiling",
                    "squinting"
                ],
                "name": "grinning squinting face"
            },
            "😊": {
                "keywords": [
                    "blush",
                    "eye",
                    "eyes",
                    "face",
                    "glad",
                    "satisfied",
                    "smile",
                    "smiling"
                ],
                "name": "smiling face with smiling eyes"
            },
            "😂": {
                "keywords": [
                    "crying",
                    "face",
                    "feels",
                    "funny",
                    "haha",
                    "happy",
                    "hehe",
                    "hilarious",
                    "joy",
                    "laugh",
                    "lmao",
                    "lol",
                    "rofl",
                    "roflmao",
                    "tear"
                ],
                "name": "face with tears of joy"
            },
            "😈": {
                "keywords": [
                    "demon",
                    "devil",
                    "evil",
                    "face",
                    "fairy",
                    "fairytale",
                    "fantasy",
                    "horns",
                    "purple",
                    "shade",
                    "smile",
                    "smiling",
                    "tale"
                ],
                "name": "smiling face with horns"
            },
            "🤠": {
                "keywords": [
                    "cowboy",
                    "cowgirl",
                    "face",
                    "hat"
                ],
                "name": "cowboy hat face"
            },
            "👺": {
                "keywords": [
                    "angry",
                    "creature",
                    "face",
                    "fairy",
                    "fairytale",
                    "fantasy",
                    "goblin",
                    "mask",
                    "mean",
                    "monster",
                    "tale"
                ],
                "name": "goblin"
            },
            "😎": {
                "keywords": [
                    "awesome",
                    "beach",
                    "bright",
                    "bro",
                    "chilling",
                    "cool",
                    "face",
                    "rad",
                    "relaxed",
                    "shades",
                    "slay",
                    "smile",
                    "style",
                    "sunglasses",
                    "swag",
                    "win"
                ],
                "name": "smiling face with sunglasses"
            },
            "🤥": {
                "keywords": [
                    "face",
                    "liar",
                    "lie",
                    "lying",
                    "pinocchio"
                ],
                "name": "lying face"
            },
            "👽": {
                "keywords": [
                    "alien",
                    "creature",
                    "extraterrestrial",
                    "face",
                    "fairy",
                    "fairytale",
                    "fantasy",
                    "monster",
                    "space",
                    "tale",
                    "ufo"
                ],
                "name": "alien"
            },
            "😅": {
                "keywords": [
                    "cold",
                    "dejected",
                    "excited",
                    "face",
                    "grinning",
                    "mouth",
                    "nervous",
                    "open",
                    "smile",
                    "smiling",
                    "stress",
                    "stressed",
                    "sweat"
                ],
                "name": "grinning face with sweat"
            },
            "😏": {
                "keywords": [
                    "boss",
                    "dapper",
                    "face",
                    "flirt",
                    "homie",
                    "kidding",
                    "leer",
                    "shade",
                    "slick",
                    "sly",
                    "smirk",
                    "smug",
                    "snicker",
                    "suave",
                    "suspicious",
                    "swag"
                ],
                "name": "smirking face"
            },
            "🤢": {
                "keywords": [
                    "face",
                    "gross",
                    "nasty",
                    "nauseated",
                    "sick",
                    "vomit"
                ],
                "name": "nauseated face"
            },
            "🆎": {
                "keywords": [
                    "AB",
                    "blood",
                    "button",
                    "type"
                ],
                "name": "AB button (blood type)"
            },
            "🌮": {
                "keywords": [
                    "mexican",
                    "taco"
                ],
                "name": "taco"
            },
            "🆗": {
                "keywords": [
                    "button",
                    "OK",
                    "okay"
                ],
                "name": "OK button"
            },
            "🈁": {
                "keywords": [
                    "button",
                    "here",
                    "Japanese",
                    "katakana"
                ],
                "name": "Japanese “here” button"
            },
        };
    });

    onRpc("/web/static/src/core/emoji_picker/emoji_data/global.json", () => {
        return {
            "😀": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":grinning_face:"
                ],
                "emoticons": []
            },
            "😃": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":grinning_face_with_big_eyes:"
                ],
                "emoticons": [
                    ":D",
                    ":-D",
                    "=D"
                ]
            },
            "😛": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":face_with_tongue:"
                ],
                "emoticons": [
                    ":p",
                    ":P",
                    ":-p",
                    ":-P",
                    "=P"
                ]
            },
            "😆": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":grinning_squinting_face:"
                ],
                "emoticons": [
                    "xD",
                    "XD"
                ]
            },
            "😊": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":smiling_face_with_smiling_eyes:"
                ],
                "emoticons": [
                    ":)",
                    ":-)",
                    "=)",
                    ":]"
                ]
            },
            "😂": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":face_with_tears_of_joy:"
                ],
                "emoticons": [
                    "x'D"
                ]
            },
            "😈": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":smiling_face_with_horns:"
                ],
                "emoticons": [
                    "3:)",
                    ">:)"
                ]
            },
            "🤠": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":cowboy_hat_face:"
                ],
                "emoticons": []
            },
            "👺": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":goblin:"
                ],
                "emoticons": []
            },
            "😎": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":smiling_face_with_sunglasses:"
                ],
                "emoticons": [
                    "B)",
                    "8)",
                    "B-)",
                    "8-)"
                ]
            },
            "🤥": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":lying_face:"
                ],
                "emoticons": []
            },
            "👽": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":alien:"
                ],
                "emoticons": [
                    ":et",
                    ":alien"
                ]
            },
            "😅": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":grinning_face_with_sweat:"
                ],
                "emoticons": []
            },
            "😏": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":smirking_face:"
                ],
                "emoticons": []
            },
            "🤢": {
                "category": "Smileys & People",
                "shortcodes": [
                    ":nauseated_face:"
                ],
                "emoticons": []
            },
            "🆎": {
                "category": "Symbols",
                "shortcodes": [
                    ":ab_button_blood_type:"
                ],
                "emoticons": []
            },
            "🌮": {
                "category": "Food & Drink",
                "shortcodes": [
                    ":taco:"
                ],
                "emoticons": []
            },
            "🆗": {
                "category": "Symbols",
                "shortcodes": [
                    ":ok_button:"
                ],
                "emoticons": []
            },
            "🈁": {
                "category": "Symbols",
                "shortcodes": [
                    ":japanese_here_button:"
                ],
                "emoticons": []
            },
        };
    });

    onRpc("/web/static/src/core/emoji_picker/emoji_data/emojiCategories.json", () => {
        return [
            {
                "name": "Smileys & People",
                "displayName": "Smileys & People",
                "title": "🙂",
                "sortId": 1
            },
            {
                "name": "Symbols",
                "displayName": "Symbols",
                "title": "💯",
                "sortId": 2
            },
            {
                "name": "Animals & Nature",
                "displayName": "Animals & Nature",
                "title": "🐵",
                "sortId": 3
            },
            {
                "name": "Food & Drink",
                "displayName": "Food & Drink",
                "title": "🍄",
                "sortId": 4
            },
            {
                "name": "Travel & Places",
                "displayName": "Travel & Places",
                "title": "🌍",
                "sortId": 5
            },
            {
                "name": "Activities",
                "displayName": "Activities",
                "title": "🎃",
                "sortId": 6
            },
            {
                "name": "Objects",
                "displayName": "Objects",
                "title": "🔫",
                "sortId": 7
            }
        ];
    });
}
