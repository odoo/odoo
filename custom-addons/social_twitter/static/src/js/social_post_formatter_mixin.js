/** @odoo-module **/

import { SocialPostFormatterMixinBase, SocialPostFormatterRegex } from '@social/js/social_post_formatter_mixin';

import { patch } from "@web/core/utils/patch";

/*
 * Add Twitter @tag and #hashtag support.
 * Replace all occurrences of `#hashtag` by a HTML link to a search of the hashtag
 * on the media website
 */
patch(SocialPostFormatterMixinBase, {

    _formatPost(value) {
        value = super._formatPost(...arguments);
        if (this._getMediaType() === 'twitter') {
            value = value.replace(SocialPostFormatterRegex.REGEX_HASHTAG,
                `$1<a href='https://twitter.com/hashtag/$2?src=hash' target='_blank'>#$2</a>`);
            value = value.replace(SocialPostFormatterRegex.REGEX_AT,
                `<a href='https://twitter.com/$1' target='_blank'>@$1</a>`);
        }
        return value;
    }

});
