odoo.define('website.widgets.media', function (require) {
'use strict';

const {ImageWidget} = require('wysiwyg.widgets.media');

ImageWidget.include({
    _getAttachmentsDomain() {
        const domain = this._super(...arguments);
        domain.push('|', ['url', '=', false], '!', ['url', '=like', '/web/image/website.%']);
        domain.push(['key', '=', false]);
        return domain;
    }
});
});
