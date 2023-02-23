/** @odoo-module **/

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';

LivechatButton.include({
    className: `${LivechatButton.prototype.className} o_website_livechat_button o-isExternalLib`,
});
