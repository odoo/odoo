odoo.define('hr_holidays/static/tests/helpers/mock_server.js', function (require) {
'use strict';

require('@mail/../tests/helpers/mock_server'); // ensure mail overrides are applied first

const MockServer = require('web.MockServer');

MockServer.include({
    /**
     * Overrides to add out of office to employees.
     *
     * @override
     */
    _mockResPartnerMailPartnerFormat(ids) {
        const partnerFormats = this._super(...arguments);
        const partners = this.getRecords(
            'res.partner',
            [['id', 'in', ids]],
            { active_test: false },
        );
        for (const partner of partners) {
            // Not a real field but ease the testing
            partnerFormats.get(partner.id).out_of_office_date_end = partner.out_of_office_date_end;
        }
        return partnerFormats;
    },
});

});
