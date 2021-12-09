/** @odoo-module **/

import { addRecordMethods } from '@mail/model/model_core';
import core from 'web.core';

addRecordMethods('Chatter', {
    onClickChatterSearchArticle(event) {
        core.bus.trigger("openMainPalette", {
            searchValue: "?",
        });
    },
});
