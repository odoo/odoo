odoo.define('website_livechat.legacy.website_livechat.livechat_request', function (require) {
"use strict";

var LivechatButton = require('@im_livechat/legacy/widgets/livechat_button')[Symbol.for("default")];

LivechatButton.include({
    className: `${LivechatButton.prototype.className} o_bottom_fixed_element o_bottom_fixed_element_move_up o_website_livechat_button fa fa-commenting`,
});

return {
    LivechatButton: LivechatButton,
};

});
