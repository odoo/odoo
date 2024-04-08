/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import "@website/js/content/snippets.animation";
import { renderToElement } from "@web/core/utils/render";

// FIXME There is no reason to inherit from socialShare here
const ForumShare = publicWidget.registry.socialShare.extend({
    selector: '',
    events: {},

    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     * @param {string} targetType
     */
    init: function (parent, options, targetType) {
        this._super.apply(this, arguments);
        this.targetType = targetType;
    },
    /**
     * @override
     */
    start: function () {
        const def = this._super.apply(this, arguments);
        this._onMouseEnter();
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _render: function () {
        const question = document.querySelector('article.question');
        if (!this.targetType) {
            this._super.apply(this, arguments);
        } else if (this.targetType === 'social-alert') {
            question.insertAdjacentHTML('beforebegin', renderToElement('website.social_alert', {medias: this.socialList}));
        } else {
            document.body.insertAdjacentHTML('beforeend', renderToElement('website.social_modal', {
                medias: this.socialList,
                target_type: this.targetType,
                state: question.dataset.state,
            }));
            const modal = document.querySelector('#oe_social_share_modal');
            new Modal(modal).show();
        }
    },
});

publicWidget.registry.websiteForumShare = publicWidget.Widget.extend({
    selector: '.website_forum',

    /**
     * @override
     */
    start: function () {
        // Retrieve stored social data
        if (sessionStorage.getItem('social_share')) {
            const socialData = JSON.parse(sessionStorage.getItem('social_share'));
            (new ForumShare(this, false, socialData.targetType)).attachTo(document.body);
            sessionStorage.removeItem('social_share');
        }

        return this._super.apply(this, arguments);
    },
});
