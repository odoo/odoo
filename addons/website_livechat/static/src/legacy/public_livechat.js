odoo.define('website_livechat.legacy.website_livechat.livechat_request', function (require) {
"use strict";

const config = require('web.config');
var LivechatButton = require('@im_livechat/legacy/widgets/livechat_button')[Symbol.for("default")];

LivechatButton.include({
    className: `${LivechatButton.prototype.className} o_bottom_fixed_element o_bottom_fixed_element_move_up o_website_livechat_button fa fa-commenting`,

    /**
     * @override
     */
    async start() {
        // We trigger a resize to launch the event that checks if this element hides
        // a button when the page is loaded.
        $(window).trigger('resize');
        await this._super(...arguments);
        this.el.innerHTML = "";
        if (this.messaging.publicLivechatGlobal.livechatButtonView.buttonText && !config.device.touch) {
            this.el.dataset.content = this.messaging.publicLivechatGlobal.livechatButtonView.buttonText;
            this.el.dataset.toggle = "popover";
            this.el.dataset.trigger = "hover";
            this.$el.popover({
                animation: true,
            });
        }
    },
});

return {
    LivechatButton: LivechatButton,
};

});
