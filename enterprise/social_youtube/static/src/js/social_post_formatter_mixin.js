/** @odoo-module **/

import { SocialPostFormatterMixinBase, SocialPostFormatterRegex } from '@social/js/social_post_formatter_mixin';

import { patch } from "@web/core/utils/patch";

/*
 * Add Youtube #hashtag support.
 * Replace all occurrences of `#hashtag` by a HTML link to a search of the hashtag
 * on the media website
 */
patch(SocialPostFormatterMixinBase, {

    _formatPost(value) {
        value = super._formatPost(...arguments);
        if (['youtube', 'youtube_preview'].includes(this._getMediaType())) {
            value = value.replace(SocialPostFormatterRegex.REGEX_HASHTAG,
                `$1<a href='https://www.youtube.com/results?search_query=%23$2' target='_blank'>#$2</a>`);
        }
        return value;
    }

});
