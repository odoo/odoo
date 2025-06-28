/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import "@website/js/content/snippets.animation";
import { renderToElement } from "@web/core/utils/render";

// FIXME There is no reason to inherit from socialShare here
var ForumShare = publicWidget.registry.socialShare.extend({
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
        var def = this._super.apply(this, arguments);
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
        var $question = this.$('article.question');
        if (!this.targetType) {
            this._super.apply(this, arguments);
        } else if (this.targetType === 'social-alert') {
            $question.before(renderToElement('website.social_alert', {medias: this.socialList}));
        } else {
            const socialModalEl = renderToElement('website.social_modal', {
                medias: this.socialList,
                target_type: this.targetType,
                state: $question.data('state'),
            });
            document.body.append(socialModalEl);
            $('#oe_social_share_modal').modal('show');
        }
    },
    /**
    * @override
    * TODO remove me in master. This has been introduced as a stable fix to not
    * remove the document body at the `destroy()` of the `ForumShare` public
    * widget.
    *
    * Background: The `ForumShare` public widget is initially attached to the document
    * body upon instantiation, which means its root element (`this.$el`) is set
    * to the document body. Normally, when a widget is destroyed, its root
    * element is removed which, in this case, would result in the document body
    * removal.
    *
    * To prevent this, the fix assigns `null` to the root element before
    * invoking the `destroy()` method, ensuring that the document body remains
    * intact.
    */
    destroy: function () {
        this.setElement(null);
        const socialModalEl = document.querySelector("body #oe_social_share_modal");
        if (socialModalEl) {
            socialModalEl.remove();
        }
        this._super();
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
            var socialData = JSON.parse(sessionStorage.getItem('social_share'));
            (new ForumShare(this, false, socialData.targetType)).attachTo($(document.body));
            sessionStorage.removeItem('social_share');
        }

        return this._super.apply(this, arguments);
    },
});
