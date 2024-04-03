/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('website_slides', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity_tests.js');

QUnit.test('grant course access', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const slideChannelId1 = pyEnv['slide.channel'].create({});
    pyEnv['mail.activity'].create({
        can_write: true,
        res_id: slideChannelId1,
        request_partner_id: resPartnerId1,
        res_model: 'slide.channel',
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'action_grant_access') {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], slideChannelId1);
                assert.strictEqual(args.kwargs.partner_id, resPartnerId1);
                assert.step('access_grant');
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
        },
    });
    await openView({
        res_id: slideChannelId1,
        res_model: 'slide.channel',
        views: [[false, 'form']],
    });

    assert.containsOnce(document.body, '.o_Activity', "should have activity component");
    assert.containsOnce(document.body, '.o_Activity_grantAccessButton', "should have grant access button");

    document.querySelector('.o_Activity_grantAccessButton').click();
    assert.verifySteps(['access_grant'], "Grant button should trigger the right rpc call");
});

QUnit.test('refuse course access', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const slideChannelId1 = pyEnv['slide.channel'].create({});
    pyEnv['mail.activity'].create({
        can_write: true,
        res_id: slideChannelId1,
        request_partner_id: resPartnerId1,
        res_model: 'slide.channel',
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'action_refuse_access') {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], slideChannelId1);
                assert.strictEqual(args.kwargs.partner_id, resPartnerId1);
                assert.step('access_refuse');
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
        },
    });
    await openView({
        res_id: slideChannelId1,
        res_model: 'slide.channel',
        views: [[false, 'form']],
    });

    assert.containsOnce(document.body, '.o_Activity', "should have activity component");
    assert.containsOnce(document.body, '.o_Activity_refuseAccessButton', "should have refuse access button");

    document.querySelector('.o_Activity_refuseAccessButton').click();
    assert.verifySteps(['access_refuse'], "refuse button should trigger the right rpc call");
});

});
});
