/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follower_subtype_tests.js');

QUnit.test('simplest layout of a followed subtype', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const subtypeId = pyEnv['mail.message.subtype'].create({
        default: true,
        name: 'TestSubtype',
    });
    const followerId = pyEnv['mail.followers'].create({
        display_name: "François Perusse",
        partner_id: pyEnv.currentPartnerId,
        res_model: 'res.partner',
        res_id: pyEnv.currentPartnerId,
        subtype_ids: [subtypeId],
    });
    pyEnv['res.partner'].write([pyEnv.currentPartnerId], {
        message_follower_ids: [followerId],
    });
    const { click, openView } = await start({
        // FIXME: should adapt mock server code to provide `hasWriteAccess`
        async mockRPC(route, args, performRPC) {
            if (route === '/mail/thread/data') {
                // mimic user with write access
                const res = await performRPC(...arguments);
                res['hasWriteAccess'] = true;
                return res;
            }
        },
    });
    await openView({
        res_model: 'res.partner',
        res_id: pyEnv.currentPartnerId,
        views: [[false, 'form']],
    });
    await click('.o_FollowerListMenu_buttonFollowers');
    await click('.o_Follower_editButton');
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype:contains(TestSubtype)',
        "should have a follower subtype for 'TestSubtype'"
    );
    assert.containsOnce(
        document.querySelector('.o_FollowerSubtype'),
        '.o_FollowerSubtype_label',
        "should have a label"
    );
    assert.containsOnce(
       $('.o_FollowerSubtype:contains(TestSubtype)'),
        '.o_FollowerSubtype_checkbox',
        "should have a checkbox"
    );
    assert.strictEqual(
        $('.o_FollowerSubtype:contains(TestSubtype) .o_FollowerSubtype_label')[0].textContent,
        "TestSubtype",
        "should have the name of the subtype as label"
    );
    assert.ok(
        $('.o_FollowerSubtype:contains(TestSubtype) .o_FollowerSubtype_checkbox')[0].checked,
        "checkbox should be checked as follower subtype is followed"
    );
});

QUnit.test('simplest layout of a not followed subtype', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.message.subtype'].create({
        default: true,
        name: 'TestSubtype',
    });
    const followerId = pyEnv['mail.followers'].create({
        display_name: "François Perusse",
        partner_id: pyEnv.currentPartnerId,
        res_model: 'res.partner',
        res_id: pyEnv.currentPartnerId,
    });
    pyEnv['res.partner'].write([pyEnv.currentPartnerId], {
        message_follower_ids: [followerId],
    });
    const { click, openView } = await start({
        // FIXME: should adapt mock server code to provide `hasWriteAccess`
        async mockRPC(route, args, performRPC) {
            if (route === '/mail/thread/data') {
                // mimic user with write access
                const res = await performRPC(...arguments);
                res['hasWriteAccess'] = true;
                return res;
            }
        },
    });
    await openView({
        res_model: 'res.partner',
        res_id: pyEnv.currentPartnerId,
        views: [[false, 'form']],
    });
    await click('.o_FollowerListMenu_buttonFollowers');
    await click('.o_Follower_editButton');
    assert.notOk(
        $('.o_FollowerSubtype:contains(TestSubtype) .o_FollowerSubtype_checkbox')[0].checked,
        "checkbox should not be checked as follower subtype is not followed"
    );
});

QUnit.test('toggle follower subtype checkbox', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const followerSubtypeId = pyEnv['mail.message.subtype'].create({
        default: true,
        name: 'TestSubtype',
    });
    const followerId = pyEnv['mail.followers'].create({
        display_name: "François Perusse",
        partner_id: pyEnv.currentPartnerId,
        res_model: 'res.partner',
        res_id: pyEnv.currentPartnerId,
    });
    pyEnv['res.partner'].write([pyEnv.currentPartnerId], {
        message_follower_ids: [followerId],
    });
    const { click, openView } = await start({
        // FIXME: should adapt mock server code to provide `hasWriteAccess`
        async mockRPC(route, args, performRPC) {
            if (route === '/mail/thread/data') {
                // mimic user with write access
                const res = await performRPC(...arguments);
                res['hasWriteAccess'] = true;
                return res;
            }
        },
    });
    await openView({
        res_model: 'res.partner',
        res_id: pyEnv.currentPartnerId,
        views: [[false, 'form']],
    });
    await click('.o_FollowerListMenu_buttonFollowers');
    await click('.o_Follower_editButton');
    assert.notOk(
        document.querySelector(`.o_FollowerSubtype[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtype_checkbox`).checked,
        "checkbox should not be checked as follower subtype is not followed"
    );

    await click(`.o_FollowerSubtype[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtype_checkbox`);
    assert.ok(
        document.querySelector(`.o_FollowerSubtype[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtype_checkbox`).checked,
        "checkbox should now be checked"
    );

    await click(`.o_FollowerSubtype[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtype_checkbox`);
    assert.notOk(
        document.querySelector(`.o_FollowerSubtype[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtype_checkbox`).checked,
        "checkbox should be no more checked"
    );
});

});
});
