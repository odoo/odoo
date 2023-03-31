/** @odoo-module alias=website_livechat.legacy.website_livechat.livechat_request **/

import LivechatButton from "@im_livechat/legacy/widgets/livechat_button";

LivechatButton.include({
    className: `${LivechatButton.prototype.className} o_bottom_fixed_element o_bottom_fixed_element_move_up o_website_livechat_button fa fa-commenting`,
});

export default {
    LivechatButton: LivechatButton,
};
