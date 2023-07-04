/** @odoo-module **/

import '@mail/../tests/helpers/mock_server/models/res_partner'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Overrides to add out of office to employees.
     *
     * @override
     */
    _mockResPartnerMailPartnerFormat(ids) {
        const partnerFormats = super._mockResPartnerMailPartnerFormat(...arguments);
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
