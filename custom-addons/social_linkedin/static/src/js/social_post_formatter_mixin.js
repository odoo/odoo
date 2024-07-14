/** @odoo-module **/

import { SocialPostFormatterMixinBase, SocialPostFormatterRegex } from '@social/js/social_post_formatter_mixin';

import { patch } from "@web/core/utils/patch";

/*
 * Add LinkedIn #hashtag support.
 * Replace all occurrences of `#hashtag` by a HTML link to a search of the hashtag
 * on the media website
 */
patch(SocialPostFormatterMixinBase, {

    _formatPost(value) {
        value = super._formatPost(...arguments);
        if (this._getMediaType() === 'linkedin') {
            const LINKEDIN_HASHTAG_REGEX = /{hashtag\|#\|([a-zA-Z\d\-_]+)}/g;
            value = value.replace(SocialPostFormatterRegex.REGEX_HASHTAG,
                `$1<a href='https://www.linkedin.com/feed/hashtag/$2' target='_blank'>#$2</a>`);
            value = value.replace(LINKEDIN_HASHTAG_REGEX,
                `<a href='https://www.linkedin.com/feed/hashtag/$1' target='_blank'>#$1</a>`);
        }
        return value;
    }

});
