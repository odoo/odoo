/* Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {Chatter} from "@mail/chatter/web_portal/chatter";
import {patch} from "@web/core/utils/patch";
import {useEffect} from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        useEffect(this._resetScrollToAttachmentsEffect.bind(this), () => [
            this.state.isAttachmentBoxOpened,
        ]);
    },
    /**
     * Prevent scrollIntoView error
     * @param {Boolean} isAttachmentBoxOpened
     * @private
     */
    _resetScrollToAttachmentsEffect(isAttachmentBoxOpened) {
        if (!isAttachmentBoxOpened) {
            this.state.scrollToAttachments = 0;
        }
    },
});
