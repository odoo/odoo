/** @odoo-module **/

import { SocialPostFormatterMixinBase, SocialPostFormatterRegex } from '@social/js/social_post_formatter_mixin';

import { patch } from "@web/core/utils/patch";

/*
 * Add Instagram #hashtag and @mention support.
 * Replace all occurrences of `#hashtag` and `@mention` by a HTML link to a
 * search of the hashtag/mention on the media website
 */
patch(SocialPostFormatterMixinBase, {

    _formatPost(value) {
        value = super._formatPost(...arguments);
        if (this._getMediaType() === 'instagram') {
            value = value.replace(SocialPostFormatterRegex.REGEX_HASHTAG,
                `$1<a href='https://www.instagram.com/explore/tags/$2' target='_blank'>#$2</a>`);
            value = value.replace(SocialPostFormatterRegex.REGEX_AT,
                `<a href='https://www.instagram.com/$1' target='_blank'>@$1</a>`);
        }
        return value;
    }

});
