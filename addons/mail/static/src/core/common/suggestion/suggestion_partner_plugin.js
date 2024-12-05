// import { Plugin } from "@html_editor/plugin";
// // import { isEmptyBlock } from "@html_editor/utils/dom_info";
// import { reactive } from "@odoo/owl";
// import { _t } from "@web/core/l10n/translation";
// import { rotate } from "@web/core/utils/arrays";
// import { SuggestionList } from "./suggestion_list";
// import { withSequence } from "@html_editor/utils/resource";
// import { select } from "addons/point_of_sale/static/tests/pos/tours/utils/combo_popup_util";
// // import { omit, pick } from "@web/core/utils/objects";

// /** @typedef { import("@html_editor/core/selection_plugin").EditorSelection } EditorSelection */
// /** @typedef { import("@html_editor/core/user_command_plugin").UserCommand } UserCommand */
// /** @typedef { ReturnType<_t> } TranslatedString */

// /**
//  * @typedef {Object} PowerboxCategory
//  * @property {string} id
//  * @property {String} name
//  *
//  *
//  * @typedef {Object} PowerboxItem
//  * @property {string} categoryId Id of a powerbox category
//  * @property {string} commandId Id of a user command to extend
//  * @property {Object} [commandParams] Passed to the command's `run` function - optional
//  * @property {TranslatedString} [title] Inheritable
//  * @property {TranslatedString} [description] Inheritable
//  * @property {string} [icon] fa-class - Inheritable
//  * @property {TranslatedString[]} [keywords]
//  * @property {(selection: EditorSelection) => boolean} [isAvailable] Optional and inheritable
//  */

// /**
//  * A powerbox item must derive from a user command ( @see UserCommand )
//  * specified by commandId. Properties defined in a powerbox item override those
//  * from a user command.
//  *
//  * Example:
//  *
//  * resources = {
//  *      suggestion_handlers: [
//             { id, search, fetch, select },
//         ],
//  * };
//  */

// /**
//  * The resulting powerbox command after deriving properties from a user command
//  * (type for internal use).
//  * @typedef {Object} PowerboxCommand
//  * @property {string} categoryId
//  * @property {string} categoryName
//  * @property {string} title
//  * @property {string} description
//  * @property {string} icon
//  * @property {Function} run
//  * @property {TranslatedString[]} [keywords]
//  * @property { (selection: EditorSelection) => boolean  } [isAvailable]
//  */

// /**
//  * @typedef { Object } PowerboxShared
//  * @property { PowerboxPlugin['close'] } close
//  * @property { PowerboxPlugin['open'] } open
//  * @property { PowerboxPlugin['update'] } update
//  */

// export class SuggestionPartnerPlugin extends Plugin {
//     static id = "suggestion.partner";
//     static dependencies = ["overlay", "selection", "history", "userCommand"];
//     static shared = [
//         "getSuggestionHandlers",
//         "close",
//         "open",
//         "update",
//     ];
//     // resources = {
//     //     supported_delimiters: ["@"],
//     //     suggestion_handlers: [{ id, search, fetch, select }],
//     // };
//     setup() {
//         /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
//         this.overlay = this.dependencies.overlay.createOverlay(SuggestionList);

//         this.state = reactive({});
//         this.overlayProps = {
//             document: this.document,
//             close: () => this.overlay.close(),
//             state: this.state,
//             activateSuggestion: (currentIndex) => {
//                 this.state.currentIndex = currentIndex;
//             },
//             applySuggestion: this.applySuggestion.bind(this),
//         };
//         this.addDomListener(this.editable.ownerDocument, "keydown", this.onKeyDown);
//     }

//     /**
//      * @param {Object} params
//      * @param {PowerboxCommand[]} params.suggestions
//      * @param {PowerboxCategory[]} [params.categories]
//      * @param {Function} [params.onApplySuggestion=() => {}]
//      * @param {Function} [params.onClose=() => {}]
//      */
//     open({
//         suggestions,
//         categories,
//         onApplySuggestion = () => {},
//         onClose = () => {},
//     } = {}) {
//         this.close();
//         this.onApplySuggestion = onApplySuggestion;
//         this.onClose = onClose;
//         this.update(suggestions, categories);
//     }

//     /**
//      * @param {PowerboxCommand[]} suggestions
//      * @param {PowerboxCategory[]} [categories]
//      */
//     update(suggestions, categories) {
//         if (categories) {
//             const orderCommands = [];
//             for (const category of categories) {
//                 orderCommands.push(
//                     ...suggestions.filter((suggestion) => suggestion.categoryId === category.id)
//                 );
//             }
//             suggestions = orderCommands;
//         }
//         Object.assign(this.state, {
//             showCategories: !!categories,
//             suggestions,
//             currentIndex: 0,
//         });
//         this.overlay.open({ props: this.overlayProps });
//     }

//     close() {
//         if (!this.overlay.isOpen) {
//             return;
//         }
//         this.onClose();
//         this.overlay.close();
//     }

//     onKeyDown(ev) {
//         if (!this.overlay.isOpen) {
//             return;
//         }
//         const key = ev.key;
//         switch (key) {
//             case "Escape":
//                 this.close();
//                 break;
//             case "Enter":
//             case "Tab":
//                 ev.preventDefault();
//                 ev.stopImmediatePropagation();
//                 this.applySuggestion(this.state.suggestions[this.state.currentIndex]);
//                 break;
//             case "ArrowUp": {
//                 ev.preventDefault();
//                 this.state.currentIndex = rotate(
//                     this.state.currentIndex,
//                     this.state.suggestions,
//                     -1
//                 );
//                 break;
//             }
//             case "ArrowDown": {
//                 ev.preventDefault();
//                 this.state.currentIndex = rotate(
//                     this.state.currentIndex,
//                     this.state.suggestions,
//                     1
//                 );
//                 break;
//             }
//             case "ArrowLeft":
//             case "ArrowRight": {
//                 this.close();
//                 break;
//             }
//         }
//     }

//     applySuggestion(suggestion) {
//         this.onApplySuggestion(suggestion);
//         this.close();
//     }

//     /**
//      * @returns {PowerboxCommand[]}
//      */
//     getSuggestionHandlers() {
//         const suggestionHandlers = this.getResource("suggestion_handlers");
//         const categoryDict = Object.fromEntries(
//             suggestionHandlers.map((handle) => [
//                 handle.id,
//                 handle.search,
//                 handle.fetch,
//                 handle.select,
//             ])
//         );
//         return categoryDict;
//     }

//     fetch() {

//     }

//     search() {

//     }

//     sort() {

//     }

// }
