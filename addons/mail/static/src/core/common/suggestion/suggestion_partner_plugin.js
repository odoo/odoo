// import { Plugin } from "@html_editor/plugin";
// import { renderToElement } from "@web/core/utils/render";
// import { rightPos } from "@html_editor/utils/position";
// // import { useSequential } from "@mail/utils/common/hooks";
// import { cleanTerm } from "@mail/utils/common/format";

// export class SuggestionPlugin extends Plugin {
//     static id = "searchSuggestion";
//     static dependencies = ["suggestion", "selection", "dom", "history"];
//     resources = {
//         beforeinput_handlers: this.onBeforeInput.bind(this),
//         input_handlers: this.onInput.bind(this),
//         delete_handlers: this.update.bind(this),
//         post_undo_handlers: this.update.bind(this),
//         post_redo_handlers: this.update.bind(this),
//     };
//     setup() {
//         // const categoryIds = new Set();
//         // for (const category of this.getResource("powerbox_categories")) {
//         //     if (categoryIds.has(category.id)) {
//         //         throw new Error(`Duplicate category id: ${category.id}`);
//         //     }
//         //     categoryIds.add(category.id);
//         // }
//         this.supportedDelimiters = this.getResource("supported_delimiters");
//         // this.shouldUpdate = false;
//         // this.sequential = useSequential();
//         // this.search = {
//         //     delimiter: undefined,
//         //     term: "",
//         // };
//         // this.state = useState({
//         //     count: 0,
//         //     items: undefined,
//         //     isFetching: false,
//         // });
//         // this.lastFetchedSearch;
//         // useEffect(
//         //     (delimiter, term) => {
//         //         this.searchSuggestion();
//         //         if (this.search.position === undefined || !this.search.delimiter) {
//         //             return; // nothing else to fetch
//         //         }
//         //         this.sequential(async () => {
//         //             if (
//         //                 this.lastFetchedSearch?.count === 0 &&
//         //                 (!this.search.delimiter || this.isSearchMoreSpecificThanLastFetch)
//         //             ) {
//         //                 return; // no need to fetch since this is more specific than last and last had no result
//         //             }
//         //             this.state.isFetching = true;
//         //             try {
//         //                 await this.fetchSuggestions(this.search);
//         //             } catch {
//         //                 this.lastFetchedSearch = null;
//         //             } finally {
//         //                 this.state.isFetching = false;
//         //             }
//         //             this.searchSuggestion();
//         //             this.lastFetchedSearch = {
//         //                 ...this.search,
//         //                 count: this.state.items?.suggestions.length ?? 0,
//         //             };
//         //             if (
//         //                 this.search.delimiter === delimiter &&
//         //                 this.search.term === term &&
//         //                 !this.state.items?.suggestions.length
//         //             ) {
//         //                 this.clearSearch();
//         //             }
//         //         });
//         //     },
//         //     () => {
//         //         return [this.search.delimiter, this.search.term];
//         //     }
//         // );
//     }

//     getPartnerSuggestions(thread) {
//         console.log(this.config.mailServices.storeService);
//         let partners;
//         const isNonPublicChannel =
//             thread &&
//             (thread.channel_type === "group" ||
//                 thread.channel_type === "chat" ||
//                 (thread.channel_type === "channel" && thread.authorizedGroupFullName));
//         if (isNonPublicChannel) {
//             // Only return the channel members when in the context of a
//             // group restricted channel. Indeed, the message with the mention
//             // would be notified to the mentioned partner, so this prevents
//             // from inadvertently leaking the private message to the
//             // mentioned partner.
//             partners = thread.channel_member_ids
//                 .map((member) => member.persona)
//                 .filter((persona) => persona.type === "partner");
//         } else {
//             partners = Object.values(this.config.mailServices.storeService.Persona.records).filter(
//                 (persona) => {
//                     if (
//                         thread?.model !== "discuss.channel" &&
//                         persona.eq(this.config.mailServices.storeService.odoobot)
//                     ) {
//                         return false;
//                     }
//                     return persona.type === "partner";
//                 }
//             );
//         }
//         return partners;
//     }
//     searchSuggestion(searchTerm) {
//         const partners = this.getPartnerSuggestions();
//         const suggestions = [];
//         for (const partner of partners) {
//             if (!partner.name) {
//                 continue;
//             }
//             if (
//                 cleanTerm(partner.name).includes(searchTerm) ||
//                 (partner.email && cleanTerm(partner.email).includes(searchTerm))
//             ) {
//                 suggestions.push({
//                     title: partner.name,
//                     categoryName: "partner",
//                     description: partner.email,
//                 });
//             }
//         }
//         return suggestions;
//     }

//     onBeforeInput(ev) {
//         if (ev.data === "@") {
//             this.historySavePointRestore = this.dependencies.history.makeSavePoint();
//         }
//     }
//     onInput(ev) {
//         if (ev.data === "@") {
//             this.open();
//         } else {
//             this.update();
//         }
//     }
//     update() {
//         if (!this.shouldUpdate) {
//             return;
//         }
//         const selection = this.dependencies.selection.getEditableSelection();
//         this.searchNode = selection.startContainer;
//         if (!this.isSearching(selection)) {
//             this.dependencies.suggestion.close();
//             return;
//         }
//         const searchTerm = this.searchNode.nodeValue.slice(this.offset + 1, selection.endOffset);
//         if (!searchTerm) {
//             // this.dependencies.suggestion.update(
//             //     this.enabledCommands,
//             //     this.categories
//             // );
//             return;
//         }
//         if (searchTerm.includes(" ")) {
//             this.dependencies.suggestion.close();
//             return;
//         }
//         const commands = this.searchSuggestion(searchTerm);
//         if (!commands.length) {
//             this.dependencies.suggestion.close();
//             this.shouldUpdate = true;
//             return;
//         }
//         this.dependencies.suggestion.update(commands);
//     }
//     // get isSearchMoreSpecificThanLastFetch() {
//     //     return (
//     //         this.lastFetchedSearch.delimiter === this.search.delimiter &&
//     //         this.search.term.startsWith(this.lastFetchedSearch.term)
//     //     );
//     // }
//     /**
//      * @param {string} searchTerm
//      */
//     filterCommands(searchTerm) {
//         return [{ title: "Marc Demo", categoryName: "parter", description: "mark@example.com" }];
//     }
//     /**
//      * @param {EditorSelection} selection
//      */
//     isSearching(selection) {
//         return (
//             selection.endContainer === this.searchNode &&
//             this.searchNode.nodeValue &&
//             this.searchNode.nodeValue[this.offset] === "@" &&
//             selection.endOffset >= this.offset
//         );
//     }
//     open() {
//         const selection = this.dependencies.selection.getEditableSelection();
//         this.offset = selection.startOffset - 1;
//         this.enabledCommands = [{ title: "test", categoryName: "test", description: "test" }];
//         this.dependencies.suggestion.open({
//             suggestions: this.enabledCommands,
//             categories: this.categories,
//             onApplySuggestion: () => {
//                 this.historySavePointRestore();
//                 const partnerBlock = renderToElement("mail.Suggestion.Partner", {
//                     href: `wow`,
//                     partnerId: 1,
//                     displayName: "Marc Demo",
//                 });
//                 this.dependencies.dom.insert(partnerBlock);
//                 const [anchorNode, anchorOffset] = rightPos(partnerBlock);
//                 this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
//                 this.dependencies.history.addStep();
//             },
//             onClose: () => {
//                 this.shouldUpdate = false;
//             },
//         });
//         this.shouldUpdate = true;
//     }
// }
