import { Plugin } from "@html_editor/plugin";
import { renderToElement } from "@web/core/utils/render";
import { rightPos } from "@html_editor/utils/position";
import { cleanTerm } from "@mail/utils/common/format";
import { stateToUrl } from "@web/core/browser/router";
import { reactive } from "@odoo/owl";
import { useSequential } from "@mail/utils/common/hooks";

export class SearchSuggestionPlugin extends Plugin {
    static id = "searchSuggestion";
    static dependencies = ["suggestion", "selection", "dom", "history"];
    resources = {
        beforeinput_handlers: this.onBeforeInput.bind(this),
        input_handlers: this.onInput.bind(this),
        delete_handlers: this.update.bind(this),
        post_undo_handlers: this.update.bind(this),
        post_redo_handlers: this.update.bind(this),
    };
    setup() {
        this.supportedDelimiters = this.getResource("supported_delimiters");
        this.sequential = useSequential();
        this.state = reactive({
            count: 0,
            items: undefined,
            isFetching: false,
        });
        this.param = {
            term: "",
        };
        this.lastFetchedSearch = undefined;
    }

    get isSearchMoreSpecificThanLastFetch() {
        return (
            // this.lastFetchedSearch.delimiter === this.search.delimiter &&
            this.search.term.startsWith(this.lastFetchedSearch.term)
        );
    }

    get thread() {
        const composer = this.config.mailServices.composer;
        return composer.thread || composer.message.thread;
    }

    getPartnerSuggestions(thread = this.thread) {
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

    searchSuggestion(searchTerm) {
        const partners = this.getPartnerSuggestions();
        const suggestions = [];
        for (const partner of partners) {
            if (!partner.name) {
                continue;
            }
            if (
                cleanTerm(partner.name).includes(searchTerm) ||
                (partner.email && cleanTerm(partner.email).includes(searchTerm))
            ) {
                suggestions.push({
                    title: partner.name,
                    description: partner.email,
                    partner,
                });
            }
        }
        // this.state.items = { suggestions };
        return suggestions;
    }

    onBeforeInput(ev) {
        if (ev.data === "@") {
            this.historySavePointRestore = this.dependencies.history.makeSavePoint();
        }
    }

    onInput(ev) {
        if (ev.data === "@") {
            this.open();
        } else {
            this.update();
        }
    }

    update() {
        if (!this.shouldUpdate) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        this.searchNode = selection.startContainer;
        if (!this.isSearching(selection)) {
            this.dependencies.suggestion.close();
            return;
        }
        const searchTerm = this.searchNode.nodeValue.slice(this.offset + 1, selection.endOffset);
        if (searchTerm.includes(" ")) {
            this.dependencies.suggestion.close();
            return;
        }
        this.param.term = searchTerm;
        this.search(searchTerm);
        this.sequential(async () => {
            if (
                // this.search.delimiter !== delimiter ||
                // this.search.position !== position ||
                this.param.term !== searchTerm
            ) {
                return; // ignore obsolete call
            }
            if (
                this.lastFetchedSearch?.count === 0
                // (!this.param.delimiter || this.isSearchMoreSpecificThanLastFetch)
            ) {
                return; // no need to fetch since this is more specific than last and last had no result
            }
            this.state.isFetching = true;
            try {
                await this.fetch(this.param, {
                    thread: this.thread,
                });
            } catch {
                this.lastFetchedSearch = null;
            } finally {
                this.state.isFetching = false;
            }
            this.search(searchTerm);
            this.lastFetchedSearch = {
                ...this.param,
                count: this.state.items?.suggestions.length ?? 0,
            };
            if (
                // this.search.delimiter === delimiter &&
                // this.search.position === position &&
                this.param.term === searchTerm &&
                !this.state.items?.suggestions.length
            ) {
                this.clear();
            }
        });
        // const commands = this.searchSuggestion(searchTerm);
        // if (!commands.length) {
        //     this.dependencies.suggestion.close();
        //     this.shouldUpdate = true;
        //     return;
        // }
        // this.dependencies.suggestion.update(commands);
    }

    /**
     * @param {EditorSelection} selection
     */
    isSearching(selection) {
        return (
            selection.endContainer === this.searchNode &&
            this.searchNode.nodeValue &&
            this.searchNode.nodeValue[this.offset] === "@" &&
            selection.endOffset >= this.offset
        );
    }

    open() {
        const selection = this.dependencies.selection.getEditableSelection();
        this.offset = selection.startOffset - 1;
        this.enabledCommands = this.searchSuggestion("");
        this.dependencies.suggestion.open({
            suggestions: this.enabledCommands,
            categories: this.categories,
            onApplySuggestion: (suggestion) => {
                this.historySavePointRestore();
                const partnerBlock = renderToElement("mail.Suggestion.Partner", {
                    href: stateToUrl({ model: "res.partner", resId: suggestion.partner.id }),
                    partnerId: suggestion.partner.id,
                    displayName: suggestion.partner.name,
                });
                this.dependencies.dom.insert(partnerBlock);
                const [anchorNode, anchorOffset] = rightPos(partnerBlock);
                this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
                this.dependencies.history.addStep();
            },
            onClose: () => {
                this.shouldUpdate = false;
            },
        });
        this.shouldUpdate = true;
    }

    async fetch({ term }, { thread } = {}) {
        const cleanedSearchTerm = cleanTerm(term);
        await this.fetchPartners(cleanedSearchTerm, thread);
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
        console.log(data);
        this.config.mailServices.store.insert(data);
    }

    search(term) {
        const commands = this.searchSuggestion(term);
        if (!commands.length) {
            this.dependencies.suggestion.close();
            this.shouldUpdate = true;
            return;
        }
        this.dependencies.suggestion.update(commands);
    }

    sort() {}

    clear() {
        Object.assign(this.param, {
            delimiter: undefined,
            term: "",
        });
        this.state.items = undefined;
    }
}
