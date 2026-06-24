import { Composer } from "@mail/core/common/composer";

import { patch } from '@web/core/utils/patch';

Composer.props = [...Composer.props, "websiteId?"];

patch(Composer.prototype, {
    get postData() {
        const postData = super.postData;
        postData.website_id = this.props.websiteId;
        return postData;
    },
});
