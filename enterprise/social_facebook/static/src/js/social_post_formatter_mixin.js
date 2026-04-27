/** @odoo-module **/

import { SocialPostFormatterMixinBase, SocialPostFormatterRegex } from '@social/js/social_post_formatter_mixin';

import { patch } from "@web/core/utils/patch";

/*
 * Add Facebook @tag and #hashtag support.
 * Replace all occurrences of `#hashtag` and of `@tag` by a HTML link to a
 * search of the hashtag/tag on the media website
 */
patch(SocialPostFormatterMixinBase, {

    _formatPost(value) {
        value = super._formatPost(...arguments);
        const mediaType = this._getMediaType();
        if (['facebook', 'facebook_preview'].includes(mediaType)) {
            value = value.replace(SocialPostFormatterRegex.REGEX_HASHTAG,
                `$1<a href='https://www.facebook.com/hashtag/$2' target='_blank'>#$2</a>`);

            const accountId = this.record && this.record.account_id.raw_value ||
                this.originalPost && this.originalPost.account_id.raw_value;
            if (accountId) {
                // Facebook uses a special regex for "@person" support.
                // See social.stream.post#_format_facebook_message for more information.
                const REGEX_AT_FACEBOOK = /\B@\[([0-9]*)\]\s([\w\dÀ-ÿ-]+)/g;
                value = value.replace(REGEX_AT_FACEBOOK,
                    `<a href='/social_facebook/redirect_to_profile/` + encodeURIComponent(accountId) + `/$1?name=$2' target='_blank'>$2</a>`);
            }
        }
        return value;
    },

});
