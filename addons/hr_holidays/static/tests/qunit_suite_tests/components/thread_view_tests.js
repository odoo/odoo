/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('hr_holidays', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_view_tests.js');

QUnit.test('out of office message on direct chat with out of office partner', async function (assert) {
    assert.expect(2);

    // Returning date of the out of office partner, simulates he'll be back in a month
    const returningDate = moment.utc().add(1, 'month');
    const pyEnv = await startServer();
    // Needed partner & user to allow simulation of message reception
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Foreigner partner",
        out_of_office_date_end: returningDate.format("YYYY-MM-DD"),
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
    });
    const { openDiscuss, messaging } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_ThreadView_outOfOffice',
        "should have an out of office alert on thread view"
    );
    const formattedDate = returningDate.toDate().toLocaleDateString(
        messaging.locale.language.replace(/_/g, '-'),
        { day: 'numeric', month: 'short' }
    );
    assert.ok(
        document.querySelector('.o_ThreadView_outOfOffice').textContent.includes(formattedDate),
        "out of office message should mention the returning date"
    );
});

});
});
