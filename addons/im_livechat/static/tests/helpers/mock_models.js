odoo.define('im_livechat/static/tests/helpers/mock_models.js', function (require) {
'use strict';

const MockModels = require('mail/static/tests/helpers/mock_models.js');

MockModels.patch('im_livechat/static/tests/helpers/mock_models.js', T =>
    class extends T {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static generateData() {
            const data = super.generateData(...arguments);
            Object.assign(data['mail.channel'].fields, {
                // fake type, not on Python models but is the result of a formatter
                livechat_visitor: { string: 'livechat_visitor', type: 'Object', default: false },
            });
            return data;
        }

    }
);

});
