odoo.define('hr_holidays/static/tests/helpers/mock_server.js', function (require) {
'use strict';

require('mail.MockServer'); // ensure mail overrides are applied first

const MockServer = require('web.MockServer');

MockServer.include({
    /**
     * Overrides to add visitor information to livechat channels.
     *
     * @override
     */
    _mockMailChannelPartnerInfo(ids, extra_info) {
        const partnerInfos = this._super(...arguments);
        const partners = this._getRecords(
            'res.partner',
            [['id', 'in', ids]],
            { active_test: false },
        );
        for (const partner of partners) {
            // Not a real field but ease the testing
            partnerInfos[partner.id].out_of_office_date_end = partner.out_of_office_date_end;
        }
        return partnerInfos;
    },
});

});
