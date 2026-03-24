import { Plugin } from "@html_editor/plugin";
import { isContentEditable, isTextNode } from "@html_editor/utils/dom_info";
import { rightPos } from "@html_editor/utils/position";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { NavigableList } from "@mail/core/common/navigable_list";
import {
    prepareSuggestionListOptions,
    SuggestionCore,
} from "@mail/core/common/suggestion_hook";
import {
    generateChannelMentionElement,
    generatePartnerMentionElement,
    generateRoleMentionElement,
    generateSpecialMentionElement,
} from "@mail/utils/common/format";
import { reactive } from "@web/owl2/utils";
import { user } from "@web/core/user";
import { createTextNode } from "@web/core/utils/xml";

class MentionSuggestion extends SuggestionCore {
    /** @param {MentionPlugin} plugin */
    constructor(plugin) {
        super();
        this.plugin = plugin;
        this.search = plugin.search;
        this.state = plugin.state;
        this.suggestionService = plugin.services["mail.suggestion"];
    }

    get env() {
        return this.plugin.env;
    }

    get thread() {
        return this.plugin.config.thread;
    }

    get isDestroyed() {
        return this.plugin.isDestroyed;
    }

    get canFetchSuggestions() {
        return user.isInternalUser;
    }

    getSearchContext() {
        const selection = this.plugin.dependencies.selection.getEditableSelection();
        if (
            !isTextNode(selection.startContainer) ||
            !isContentEditable(selection.startContainer) ||
            !selection.isCollapsed
        ) {
            return { start: 0, end: 0, text: "", isValid: false };
        }
        return {
            start: selection.startOffset,
            end: selection.endOffset,
            text: selection.anchorNode.textContent,
            isValid: true,
        };
    }

    insert(option, getSelection, setSelection, insertDom, addHistoryStep) {
        const position = this.getInsertPosition({ isHtmlEditor: true });
        const { startContainer, endContainer, endOffset } = getSelection();
        setSelection({
            anchorNode: startContainer,
            anchorOffset: position,
            focusNode: endContainer,
            focusOffset: endOffset,
        });
        let inlineElement;
        if (option.partner) {
            inlineElement = generatePartnerMentionElement(option.partner, this.thread);
        } else if (option.isSpecial) {
            inlineElement = generateSpecialMentionElement(option.label);
        } else if (option.role) {
            inlineElement = generateRoleMentionElement(option.role);
        } else if (option.channel) {
            inlineElement = generateChannelMentionElement(option.channel);
        } else {
            inlineElement = createTextNode(option.label);
        }
        insertDom(inlineElement);
        const [anchorNode, anchorOffset] = rightPos(inlineElement);
        setSelection({ anchorNode, anchorOffset });
        insertDom("\u00A0");
        addHistoryStep();
    }
}

export class MentionPlugin extends Plugin {
    static id = "mention";
    static dependencies = [
        "baseContainer",
        "selection",
        "history",
        "overlay",
        "dom",
        "input",
    ];
    resources = {
        on_selectionchange_handlers: this.detectMentions.bind(this),
        on_deleted_handlers: this.detectSuggestions.bind(this),
        on_input_handlers: this.detectSuggestions.bind(this),
        on_redone_handlers: this.detectSuggestions.bind(this),
        on_undone_handlers: this.detectSuggestions.bind(this),
        is_node_editable_predicates: (node) => {
            for (const { selector } of this.MENTION_SELECTORS) {
                if (closestElement(node, selector)) {
                    return true;
                }
            }
        },
        select_all_overrides: this.selectAll.bind(this),
        on_selectionchange_handlers: this.detectMentions.bind(this),
        selectors_for_feff_providers: () =>
            this.MENTION_SELECTORS.map(({ selector }) => selector).join(", "),
    };

    setup() {
        super.setup();
        /** @type {import("models").Store} */
        this.store = this.services["mail.store"];
        this.suggestionList = this.dependencies.overlay.createOverlay(
            NavigableList,
            {
                hasAutofocus: false,
                className: "shadow",
            }
        );
        this.search = reactive(
            {
                delimiter: undefined,
                position: undefined,
                term: "",
            },
            () => this.suggestion?.onSearchChange()
        );
        this.suggestionListProps = reactive({
            position: "bottom-fit",
            onSelect: (ev, option) => this.suggestion.insert(
                option,
                () => this.dependencies.selection.getEditableSelection(),
                this.dependencies.selection.setSelection.bind(this.dependencies.selection),
                this.dependencies.dom.insert.bind(this.dependencies.dom),
                this.dependencies.history.addStep.bind(this.dependencies.history)
            ),
            isLoading: false,
            options: [],
            optionTemplate: undefined,
        });
        this.state = reactive(
            {
                count: 0,
                items: undefined,
                isFetching: false,
            },
            () => {
                if (this.state.items) {
                    this.updateSuggestionListProps();
                    this.suggestionList.open({
                        props: this.suggestionListProps,
                    });
                } else {
                    this.suggestionList.close();
                }
            }
        );
        this.suggestion = new MentionSuggestion(this);
    }

    detectSuggestions() {
        this.suggestion?.detect();
    }

    updateSuggestionListProps() {
        const selection = this.dependencies.selection.getEditableSelection();
        Object.assign(this.suggestionListProps, {
            anchorRef: selection.startContainer.el,
            position: "bottom-fit",
            isLoading: !!this.search.term && this.state.isFetching,
            options: [],
            optionTemplate: undefined,
        });
        Object.assign(
            this.suggestionListProps,
            prepareSuggestionListOptions(this.state.items, this.config.thread)
        );
    }

    /**
     * Extend the selection to include whole mention elements at the borders
     * so that it doesn't get stuck into the contenteditable=false
     */
    selectAll({ anchorNode, anchorOffset, focusNode, focusOffset }) {
        const SELECTOR = this.MENTION_SELECTORS.map(({ selector }) => selector).join(", ");
        if (closestElement(anchorNode, SELECTOR)) {
            const startMention = closestElement(anchorNode, SELECTOR);
            anchorNode = startMention.parentNode;
            anchorOffset = Array.prototype.indexOf.call(anchorNode.childNodes, startMention);
        }
        if (closestElement(focusNode, SELECTOR)) {
            const endMention = closestElement(focusNode, SELECTOR);
            focusNode = endMention.parentNode;
            focusOffset = Array.prototype.indexOf.call(focusNode.childNodes, endMention) + 1;
        }
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        });
    }

    get MENTION_SELECTORS() {
        return [
            {
                selector: "a.o_channel_redirect",
                checker: (el) => this.isValidChannelMentionElement(el),
                validMentionsHandler: (channelLinks) => {
                    this.store.handleValidChannelMention(channelLinks);
                    this.dependencies.history.addStep();
                },
            },
            {
                selector: "a.o_mail_redirect",
                checker: (el) => true,
            },
            {
                selector: "a.o-discuss-mention",
                checker: (el) => true,
            },
        ];
    }

    async detectMentions(ev) {
        for (const { selector, checker, validMentionsHandler } of this.MENTION_SELECTORS) {
            const mentionLinks = Array.from(this.editable.querySelectorAll(selector)) || [];
            const validMentionLinks = (
                await Promise.all(
                    mentionLinks.map(async (el) => ({
                        el,
                        isValid: await checker(el),
                    }))
                )
            )
                .filter(({ isValid }) => isValid)
                .map(({ el }) => el);
            this.prepareValidMentionLinks(validMentionLinks);
            validMentionsHandler?.(validMentionLinks);
        }
    }

    prepareValidMentionLinks(validMentionLinks) {
        for (const el of validMentionLinks) {
            // if el's parent is odoo-editor-editable, which happens when the html is computed or set with setContent,
            // considering the mention blocks are protected and not editable.
            // This will lead to issues where the mention cannot be deleted or edited properly.
            // In this case, we wrap the mention with a base container.
            if (el.parentElement === this.editable) {
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                baseContainer.appendChild(el.cloneNode(true));
                this.editable.replaceChild(baseContainer, el);
                this.dependencies.history.addStep();
            }
        }
    }

    async isValidChannelMentionElement(el) {
        if (el.dataset.oeModel !== "discuss.channel") {
            return false;
        }
        const channel = await this.store["discuss.channel"].getOrFetch(Number(el.dataset.oeId));
        if (!channel) {
            return false;
        }
        const validChannelMention = generateChannelMentionElement(channel);
        return (
            validChannelMention.getAttribute("href") === el.getAttribute("href") &&
            [...validChannelMention.classList].every((cls) => el.classList.contains(cls))
        );
    }
}
