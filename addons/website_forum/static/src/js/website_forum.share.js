import publicWidget from "@web/legacy/js/public/public_widget";
import "@website/js/content/snippets.animation";
import { renderToElement } from "@web/core/utils/render";

const ForumShare = publicWidget.Widget.extend({
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
        var $question = this.$('article.question');
        if (this.targetType) {
            const modalEl = renderToElement("website.social_modal", {
                target_type: this.targetType,
                state: $question.data('state'),
            });
            // Remove modal from DOM once it's closed.
            modalEl.addEventListener("hidden.bs.modal", () => {
                modalEl.remove();
            });
            this.el.appendChild(modalEl);
            this.trigger_up('widgets_start_request', {
                editableMode: false,
                $target: $(modalEl.querySelector(".s_share")),
            });
            $('#oe_social_share_modal').modal('show');
        }
        return def;
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
            // Dummy div to attach the ForumShare publicwidget
            const divEl = document.createElement("div");
            divEl.classList.add("social-modal");
            document.body.appendChild(divEl);
            (new ForumShare(this, false, socialData.targetType)).attachTo(divEl);
            sessionStorage.removeItem('social_share');
        }

        return this._super.apply(this, arguments);
    },
});
