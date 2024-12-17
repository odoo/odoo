import { Plugin } from "@html_editor/plugin";
// import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { toRaw, reactive } from "@odoo/owl";
import { rotate } from "@web/core/utils/arrays";
import { SuggestionList } from "./suggestion_list";
// import { omit, pick } from "@web/core/utils/objects";
import { renderToElement } from "@web/core/utils/render";
import { rightPos } from "@html_editor/utils/position";
import { cleanTerm } from "@mail/utils/common/format";
import { stateToUrl } from "@web/core/browser/router";
import { partnerCompareRegistry } from "@mail/core/common/partner_compare";
import { escape } from "@web/core/utils/strings";

export class SuggestionPlugin extends Plugin {
    static id = "suggestion";
    static dependencies = ["overlay", "selection", "history", "userCommand", "dom"];
    static shared = ["close", "open", "update", "fetch", "search", "insert"];
    resources = {
        supported_delimiters: ["@", "#", ":"],
    };
    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.dependencies.overlay.createOverlay(SuggestionList);

        this.state = reactive({});
        this.overlayProps = {
            document: this.document,
            close: () => this.overlay.close(),
            state: this.state,
            activateSuggestion: (currentIndex) => {
                this.state.currentIndex = currentIndex;
            },
            applySuggestion: this.applySuggestion.bind(this),
        };
        this.addDomListener(this.editable.ownerDocument, "keydown", this.onKeyDown);
    }

    /**
     * @param {Object} params
     * @param {PowerboxCommand[]} params.suggestions
     * @param {PowerboxCategory[]} [params.categories]
     * @param {Function} [params.onApplySuggestion=() => {}]
     * @param {Function} [params.onClose=() => {}]
     */
    open({ suggestions, categories, onApplySuggestion = () => {}, onClose = () => {} } = {}) {
        this.close();
        this.onApplySuggestion = onApplySuggestion;
        this.onClose = onClose;
        this.update(suggestions, categories);
    }

    /**
     * @param {PowerboxCommand[]} suggestions
     * @param {PowerboxCategory[]} [categories]
     */
    update(suggestions, categories) {
        if (categories) {
            const orderCommands = [];
            for (const category of categories) {
                orderCommands.push(
                    ...suggestions.filter((suggestion) => suggestion.categoryId === category.id)
                );
            }
            suggestions = orderCommands;
        }
        Object.assign(this.state, {
            showCategories: !!categories,
            suggestions,
            currentIndex: 0,
        });
        this.overlay.open({ props: this.overlayProps });
    }

    close() {
        if (!this.overlay.isOpen) {
            return;
        }
        this.onClose();
        this.overlay.close();
    }

    onKeyDown(ev) {
        if (!this.overlay.isOpen) {
            return;
        }
        const key = ev.key;
        switch (key) {
            case "Escape":
                this.close();
                break;
            case "Enter":
            case "Tab":
                ev.preventDefault();
                ev.stopImmediatePropagation();
                this.applySuggestion(this.state.suggestions[this.state.currentIndex]);
                break;
            case "ArrowUp": {
                ev.preventDefault();
                this.state.currentIndex = rotate(
                    this.state.currentIndex,
                    this.state.suggestions,
                    -1
                );
                break;
            }
            case "ArrowDown": {
                ev.preventDefault();
                this.state.currentIndex = rotate(
                    this.state.currentIndex,
                    this.state.suggestions,
                    1
                );
                break;
            }
            case "ArrowLeft":
            case "ArrowRight": {
                this.close();
                break;
            }
        }
    }

    applySuggestion(suggestion) {
        this.onApplySuggestion(suggestion);
        this.close();
        this.dependencies.selection.focusEditable();
    }

    async fetch({ delimiter, term }, { thread } = {}) {
        const cleanedSearchTerm = cleanTerm(term);
        switch (delimiter) {
            case "@": {
                await this.fetchPartners(cleanedSearchTerm, thread);
                break;
            }
            case "#":
                await this.fetchThreads(cleanedSearchTerm);
                break;
            // case ":":
            //     await this.store.cannedReponses.fetch();
            //     break;
        }
    }

    /**
     * @param {string} term
     */
    async fetchThreads(term) {
        const suggestedThreads = await this.config.mailServices.orm.silent.call(
            "discuss.channel",
            "get_mention_suggestions",
            [],
            { search: term }
        );
        this.store.Thread.insert(suggestedThreads);
    }

    /**
     * @param {string} term
     * @param {import("models").Thread} [thread]
     */
    async fetchPartners(term, thread) {
        const kwargs = { search: term };
        if (thread?.model === "discuss.channel") {
            kwargs.channel_id = thread.id;
        }
        const data = await this.config.mailServices.orm.silent.call(
            "res.partner",
            thread?.model === "discuss.channel"
                ? "get_mention_suggestions_from_channel"
                : "get_mention_suggestions",
            [],
            kwargs
        );
        this.config.mailServices.store.insert(data);
    }

    search({ delimiter, term } = {}, { thread, sort = false } = {}) {
        thread = toRaw(thread);
        const cleanedSearchTerm = cleanTerm(term);
        switch (delimiter) {
            case "@":
                return this.searchPartnerSuggestions(cleanedSearchTerm, thread, sort);
            case "#":
                return this.searchChannelSuggestions(cleanedSearchTerm, sort);
            // case ":":
            //     commands = this.searchCannedResponseSuggestions(cleanedSearchTerm, sort);
            //     break;
        }
    }

    searchChannelSuggestions(cleanedSearchTerm, sort) {
        const suggestions = [];
        Object.values(this.config.mailServices.store.Thread.records)
            .filter(
                (thread) =>
                    thread.channel_type === "channel" &&
                    thread.displayName &&
                    cleanTerm(thread.displayName).includes(cleanedSearchTerm)
            )
            .forEach((thread) =>
                suggestions.push({
                    title: thread.displayName,
                    description: thread.description,
                    thread,
                })
            );
        const sortFunc = (c1, c2) => {
            const isPublicChannel1 = c1.channel_type === "channel" && !c2.authorizedGroupFullName;
            const isPublicChannel2 = c2.channel_type === "channel" && !c2.authorizedGroupFullName;
            if (isPublicChannel1 && !isPublicChannel2) {
                return -1;
            }
            if (!isPublicChannel1 && isPublicChannel2) {
                return 1;
            }
            if (c1.hasSelfAsMember && !c2.hasSelfAsMember) {
                return -1;
            }
            if (!c1.hasSelfAsMember && c2.hasSelfAsMember) {
                return 1;
            }
            const cleanedDisplayName1 = cleanTerm(c1.displayName);
            const cleanedDisplayName2 = cleanTerm(c2.displayName);
            if (
                cleanedDisplayName1.startsWith(cleanedSearchTerm) &&
                !cleanedDisplayName2.startsWith(cleanedSearchTerm)
            ) {
                return -1;
            }
            if (
                !cleanedDisplayName1.startsWith(cleanedSearchTerm) &&
                cleanedDisplayName2.startsWith(cleanedSearchTerm)
            ) {
                return 1;
            }
            if (cleanedDisplayName1 < cleanedDisplayName2) {
                return -1;
            }
            if (cleanedDisplayName1 > cleanedDisplayName2) {
                return 1;
            }
            return c1.id - c2.id;
        };
        // return {
        //     type: "Thread",
        //     suggestions: sort ? suggestionList.sort(sortFunc) : suggestionList,
        // };
        return suggestions;
    }

    getPartnerSuggestions(thread) {
        let partners;
        const isNonPublicChannel =
            thread &&
            (thread.channel_type === "group" ||
                thread.channel_type === "chat" ||
                (thread.channel_type === "channel" && thread.authorizedGroupFullName));
        if (isNonPublicChannel) {
            // Only return the channel members when in the context of a
            // group restricted channel. Indeed, the message with the mention
            // would be notified to the mentioned partner, so this prevents
            // from inadvertently leaking the private message to the
            // mentioned partner.
            partners = thread.channel_member_ids
                .map((member) => member.persona)
                .filter((persona) => persona.type === "partner");
        } else {
            partners = Object.values(this.config.mailServices.store.Persona.records).filter(
                (persona) => {
                    if (
                        thread?.model !== "discuss.channel" &&
                        persona.eq(this.config.mailServices.store.odoobot)
                    ) {
                        return false;
                    }
                    return persona.type === "partner";
                }
            );
        }
        return partners;
    }

    searchPartnerSuggestions(cleanedSearchTerm, thread, sort) {
        const partners = this.getPartnerSuggestions(thread);
        const suggestions = [];
        for (const partner of partners) {
            if (!partner.name) {
                continue;
            }
            if (
                cleanTerm(partner.name).includes(cleanedSearchTerm) ||
                (partner.email && cleanTerm(partner.email).includes(cleanedSearchTerm))
            ) {
                suggestions.push({
                    title: partner.name,
                    description: partner.email,
                    partner,
                });
            }
        }
        // TODO: special mentions
        // return sort
        //     ? [...this.sortPartnerSuggestions(suggestions, cleanedSearchTerm, thread)]
        //     : suggestions;
        return suggestions;
    }

    sortPartnerSuggestions(suggestions, searchTerm = "", thread = undefined) {
        const cleanedSearchTerm = cleanTerm(searchTerm);
        const compareFunctions = partnerCompareRegistry.getAll();
        const context = this.sortPartnerSuggestionsContext();
        const memberPartnerIds = new Set(
            thread?.channel_member_ids
                .filter((member) => member.persona.type === "partner")
                .map((member) => member.persona.id)
        );
        return suggestions.sort((s1, s2) => {
            const p1 = toRaw(s1.partner);
            const p2 = toRaw(s2.partner);
            // if (p1.isSpecial || p2.isSpecial) {
            //     return 0;
            // }
            for (const fn of compareFunctions) {
                const result = fn(p1, p2, {
                    env: this.env,
                    memberPartnerIds,
                    searchTerms: cleanedSearchTerm,
                    thread,
                    context,
                });
                if (result !== undefined) {
                    return result;
                }
            }
        });
    }

    sortPartnerSuggestionsContext() {
        return {};
    }

    insert(option) {
        if (option.partner) {
            const partnerBlock = renderToElement("mail.Suggestion.Partner", {
                href: stateToUrl({ model: "res.partner", resId: option.partner.id }),
                partnerId: option.partner.id,
                displayName: option.partner.name,
            });
            this.dependencies.dom.insert(partnerBlock);
            const [anchorNode, anchorOffset] = rightPos(partnerBlock);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        }
        if (option.thread) {
            const thread = option.thread;
            let className, text;
            if (thread.parent_channel_id) {
                className = "o_channel_redirect o_channel_redirect_asThread";
                text = escape(`#${thread.parent_channel_id.displayName} > ${thread.displayName}`);
            } else {
                className = "o_channel_redirect";
                text = escape(`#${thread.displayName}`);
            }
            const threadBlock = renderToElement("mail.Suggestion.Thread", {
                href: stateToUrl({ model: "discuss.channel", resId: thread.id }),
                threadId: option.thread.id,
                displayName: text,
                className,
            });
            this.dependencies.dom.insert(threadBlock);
            const [anchorNode, anchorOffset] = rightPos(threadBlock);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        }
        // if (option.cannedResponse) {
        //     this.composer.cannedResponses.push(option.cannedResponse);
        // }
    }
}
