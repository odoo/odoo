/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { emojis, getEmojisCategories, getEmojiesFromCategoryAsArray, getRecentlyUsedEmojis, setLastUsedEmoji, getEmojiClassName } from '@mail/emojis/emojis';

import { useAutofocus } from "web.custom_hooks"

const { Component, useState } = owl;
export class EmojisPopover extends Component {

    setup(...args) {
        this.state = useState({ search: "", activeCategory: null });
        this.emojisAllCategories = getEmojisCategories();
        this.getEmojiClassName = getEmojiClassName;
        useAutofocus();
    }

    get EMOJI_SEARCH_PLACEHOLDER() {
        return this.env._t("Search emojis...");
    }

    get NO_EMOJIS_FOUND_AFTER_SEARCH() {
        return this.env._t("Nothing found");
    }

    get RECENTLY_USED() {
        return this.env._t("Recently used");
    }

    get CATEGORIES() {
        return this.env._t("Categories");
    }

    get filteredEmojis() {
        if (!this.state.search) return this.emojis;
        return emojis.filter( (key, _) => key.description.includes(this.state.search));
    }

    emojisByCategory(category) {
        return getEmojiesFromCategoryAsArray(category)
    }

    get recentlyUsedEmojis() {
        return getRecentlyUsedEmojis(this.env);
    }

    get emojisCategories() {
        if (!this.state.activeCategory) {
            return getEmojisCategories();
        }
        return [this.state.activeCategory];
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    close() {
        this.trigger('o-popover-close');
    }

    /**
     * Returns whether the given node is self or a children of self.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    contains(node) {
        if (!this.el) {
            return false;
        }
        return this.el.contains(node);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEmoji(ev) {
        this.close();
        setLastUsedEmoji(this.env, ev.currentTarget.dataset.unicode);
        this.trigger('o-emoji-selection', {
            unicode: ev.currentTarget.dataset.unicode,
            source: ev.currentTarget.dataset.source
        });
    }

    _onClickEmojisCategory(category) {
        if (this.state.activeCategory === category) {
            this.state.activeCategory = null;
        }
        else {
            this.state.activeCategory = category;
        }
    }

}

Object.assign(EmojisPopover, {
    props: {},
    template: 'mail.EmojisPopover',
});

registerMessagingComponent(EmojisPopover);
