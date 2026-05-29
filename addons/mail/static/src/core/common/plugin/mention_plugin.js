import { effect, proxy } from "@odoo/owl";

import { Plugin } from "@html_editor/plugin";
import { isContentEditable, isTextNode } from "@html_editor/utils/dom_info";
import { rightPos } from "@html_editor/utils/position";

import { NavigableList } from "@mail/core/common/navigable_list";
import {
    SuggestionCore,
    makeMentionFromOption,
    mapSuggestionsToOptions,
} from "@mail/core/common/suggestion_hook";
import { generateChannelMentionElement } from "@mail/utils/common/format";

/**
 * Detects/validates mention links in the html composer AND drives the mention
 * suggestion dropdown (the overlay-based {@link NavigableList}). Used by both
 * the inline composer (via `MAIL_CORE_PLUGINS`) and the full composer (added in
 * `HtmlComposerMessageField.getConfig`).
 *
 * Configuration is read from `config.mentionPluginDependencies`: the inline
 * composer passes `{ composer, composerType, suggestionPosition }` (so
 * selections are recorded on `composer.mentionedPartners` etc.), while the full
 * composer passes `{ thread, composerType }` and extracts mentions from the html
 * server-side instead.
 *
 * @typedef {Object} MentionPluginDependencies
 * @property {import("@mail/core/common/composer_model").Composer} [composer]
 * @property {string} [composerType]
 * @property {import("models").Thread} [thread]
 * @property {string} [suggestionPosition]
 */
export class MentionPlugin extends Plugin {
    static id = "mention";
    static dependencies = ["baseContainer", "dom", "history", "input", "overlay", "selection"];
    resources = {
        on_deleted_handlers: this.detectSuggestion.bind(this),
        on_input_handlers: this.detectSuggestion.bind(this),
        on_redone_handlers: this.detectSuggestion.bind(this),
        on_selectionchange_handlers: this.validateMentions.bind(this),
        on_undone_handlers: this.detectSuggestion.bind(this),
        selectors_for_feff_providers: () =>
            this.MENTION_SELECTORS.map(({ selector }) => selector).join(", "),
    };

    setup() {
        super.setup();
        /** @type {import("models").Store} */
        this.store = this.services["mail.store"];
        /** @type {MentionPluginDependencies} */
        this.mentionDeps = this.config.mentionPluginDependencies ?? {};
        this.suggestionList = this.dependencies.overlay.createOverlay(NavigableList, {
            className: "shadow",
            hasAutofocus: false,
        });
        this.suggestionListProps = proxy({
            anchorRef: undefined,
            isLoading: false,
            onSelect: (ev, option) => this.insert(option),
            options: [],
            optionTemplate: undefined,
            position: this.mentionDeps.suggestionPosition ?? "bottom-fit",
        });
        this.suggestion = new SuggestionCore({
            canFetch: () => !!this.thread && !this.isDestroyed && !!this.store.self_user,
            getComposerType: () => this.mentionDeps.composerType,
            getThread: () => this.thread,
            suggestionService: this.services["mail.suggestion"],
        });
        this._cleanups.push(
            () => this.suggestion.dispose(),
            effect(() => {
                if (this.suggestion.search.results) {
                    this.updateSuggestionListProps();
                    this.suggestionList.open({ props: this.suggestionListProps });
                } else {
                    this.suggestionList.close();
                }
            })
        );
    }

    /** @returns {import("models").Thread|undefined} */
    get thread() {
        return (
            this.mentionDeps.thread ??
            this.mentionDeps.composer?.thread ??
            this.mentionDeps.composer?.message?.thread
        );
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

    async validateMentions(ev) {
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

    detectSuggestion() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (
            !isTextNode(selection.startContainer) ||
            !isContentEditable(selection.startContainer) ||
            !selection.isCollapsed
        ) {
            this.suggestion.clearSearch();
            return;
        }
        this.suggestion.processDetection(selection.startOffset, selection.anchorNode.textContent);
    }

    insert(option) {
        const { composer } = this.mentionDeps;
        if (composer) {
            if (option.partner) {
                composer.mentionedPartners.add({ id: option.partner.id });
            } else if (option.role) {
                composer.mentionedRoles.add(option.role);
            } else if (option.channel) {
                composer.mentionedChannels.add(option.channel.id);
            } else if (option.cannedResponse) {
                composer.cannedResponses.push(option.cannedResponse);
            }
        }
        const { detection } = this.suggestion;
        // only "/" steps the cursor past the delimiter; others anchor on it
        const position =
            detection.delimiter === "/" ? detection.position + 1 : detection.position;
        const { selection } = this.dependencies;
        const { startContainer, endContainer, endOffset } = selection.getEditableSelection();
        selection.setSelection({
            anchorNode: startContainer,
            anchorOffset: position,
            focusNode: endContainer,
            focusOffset: endOffset,
        });
        const inlineElement = makeMentionFromOption(option, { thread: this.thread });
        this.dependencies.dom.insert(inlineElement);
        const [anchorNode, anchorOffset] = rightPos(inlineElement);
        selection.setSelection({ anchorNode, anchorOffset });
        this.dependencies.dom.insert("\u00A0");
        this.dependencies.history.addStep();
    }

    updateSuggestionListProps() {
        const selection = this.dependencies.selection.getEditableSelection();
        const { type, suggestions } = this.suggestion.search.results;
        const { optionTemplate, options } = mapSuggestionsToOptions(type, suggestions, {
            thread: this.thread,
        });
        Object.assign(this.suggestionListProps, {
            anchorRef: selection.anchorNode?.el,
            isLoading: !!this.suggestion.detection.term && this.suggestion.search.loading,
            optionTemplate,
            options,
        });
    }

    prepareValidMentionLinks(validMentionLinks) {
        for (const el of validMentionLinks) {
            // if el's parent is odoo-editor-editable, which happens when the html is computed or set with setContent,
            // considering the mention blocks are protected and not editable.
            // This will lead to issues where the mention cannot be deleted or edited properly.
            // In this case, we wrap the mention with a base container.
            if (el.parentElement === this.editable) {
                const baseContainer = this.dependencies.baseContainer.createBaseContainer({
                    children: [el.cloneNode(true)],
                });
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
