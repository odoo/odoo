/** @odoo-module **/

import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";

// List of icons that should be avoided when adding a random icon
const iconsBlocklist = ["💩", "💀", "☠️", "🤮", "🖕", "🤢", "😒"];

/**
 * Get a random icon (that is not in the icons blocklist)
 * @returns {String} emoji
 */
export async function getRandomIcon() {
    const { emojis } = await loadEmoji();
    const randomEmojis = emojis.filter((emoji) => !iconsBlocklist.includes(emoji.codepoints));
    return randomEmojis[Math.floor(Math.random() * randomEmojis.length)].codepoints;
}

/**
 * Set an intersection observer on the given element. This function will ensure
 * that the given callback function will be called at most once when the given
 * element becomes visible on screen. This function can be used to load
 * components lazily (see: 'EmbeddedViewComponent').
 * @param {HTMLElement} element
 * @param {Function} callback
 * @returns {IntersectionObserver}
 */
export function setIntersectionObserver (element, callback) {
    const options = {
        root: null,
        rootMargin: '0px'
    };
    const observer = new window.IntersectionObserver(entries => {
        const entry = entries[0];
        if (entry.isIntersecting) {
            observer.unobserve(entry.target);
            callback();
        }
    }, options);
    observer.observe(element);
    return observer;
}
