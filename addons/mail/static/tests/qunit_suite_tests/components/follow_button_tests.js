/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follow_button_tests.js');

QUnit.test('base rendering not editable', async function (assert) {
    assert.expect(2);

    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                </div>
            </form>`,
    };
    const { openView, pyEnv } = await start({
        serverData: { views },
    });
    await openView({
        res_id: pyEnv.currentPartnerId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_follow',
        "should have 'Follow' button"
    );
});

QUnit.test('hover following button', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const threadId = pyEnv['res.partner'].create({});
    const followerId = pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: pyEnv.currentPartnerId,
        res_id: threadId,
        res_model: 'res.partner',
    });
    pyEnv['res.partner'].write([pyEnv.currentPartnerId], {
        message_follower_ids: [followerId],
    });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_unfollow',
        "should have 'Unfollow' button"
    );
    assert.strictEqual(
        document.querySelector('.o_FollowButton_unfollow').textContent.trim(),
        'Following',
        "'unfollow' button should display 'Following' as text when not hovered"
    );
    assert.containsNone(
        document.querySelector('.o_FollowButton_unfollow'),
        '.fa-times',
        "'unfollow' button should not contain a cross icon when not hovered"
    );
    assert.containsOnce(
        document.querySelector('.o_FollowButton_unfollow'),
        '.fa-check',
        "'unfollow' button should contain a check icon when not hovered"
    );

    await afterNextRender(() => {
        document
            .querySelector('.o_FollowButton_unfollow')
            .dispatchEvent(new window.MouseEvent('mouseenter'));
        }
    );
    assert.strictEqual(
        document.querySelector('.o_FollowButton_unfollow').textContent.trim(),
        'Unfollow',
        "'unfollow' button should display 'Unfollow' as text when hovered"
    );
    assert.containsOnce(
        document.querySelector('.o_FollowButton_unfollow'),
        '.fa-times',
        "'unfollow' button should contain a cross icon when hovered"
    );
    assert.containsNone(
        document.querySelector('.o_FollowButton_unfollow'),
        '.fa-check',
        "'unfollow' button should not contain a check icon when hovered"
    );
});

QUnit.test('click on "follow" button', async function (assert) {
    assert.expect(4);

    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                </div>
            </form>`,
    };
    const { click, openView, pyEnv } = await start({
        serverData: { views },
    });
    await openView({
        res_id: pyEnv.currentPartnerId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_follow',
        "should have button follow"
    );

    await click('.o_FollowButton_follow');
    assert.containsNone(
        document.body,
        '.o_FollowButton_follow',
        "should not have follow button after clicked on follow"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_unfollow',
        "should have unfollow button after clicked on follow"
    );
});

QUnit.test('click on "unfollow" button', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const threadId = pyEnv['res.partner'].create({});
    const followerId = pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: pyEnv.currentPartnerId,
        res_id: threadId,
        res_model: 'res.partner',
    });
    pyEnv['res.partner'].write([pyEnv.currentPartnerId], {
        message_follower_ids: [followerId],
    });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                </div>
            </form>`,
    };
    const { click, openView } = await start({
        serverData: { views },
    });
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsNone(
        document.body,
        '.o_FollowButton_follow',
        "should not have button follow"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_unfollow',
        "should have button unfollow"
    );

    await click('.o_FollowButton_unfollow');
    assert.containsOnce(
        document.body,
        '.o_FollowButton_follow',
        "should have follow button after clicked on unfollow"
    );
    assert.containsNone(
        document.body,
        '.o_FollowButton_unfollow',
        "should not have unfollow button after clicked on unfollow"
    );
});

});
});
