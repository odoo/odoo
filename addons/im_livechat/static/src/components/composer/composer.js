odoo.define('im_livechat/static/src/components/composer/composer.js', function (require) {
'use strict';

const components = {
    Composer: require('mail/static/src/components/composer/composer.js'),
};

const { patch } = require('web.utils');

patch(components.Composer, 'im_livechat/static/src/components/composer/composer.js', {
    _update() {
        this._super.apply(this, arguments);
        if (this.composer.thread && !this.composer.thread.isLiveChatActive) {
            this.composer.thread.disableComposer();
        }
    },
});

});
