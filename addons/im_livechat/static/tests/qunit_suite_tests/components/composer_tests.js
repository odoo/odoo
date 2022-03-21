/** @odoo-module **/

import { beforeEach, start } from '@mail/../tests/helpers/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_tests.js', {
    async beforeEach() {
        await beforeEach(this);
    },
});

QUnit.test('livechat: no add attachment button', async function (assert) {
    // Attachments are not yet supported in livechat, especially from livechat
    // visitor PoV. This may likely change in the future with task-2029065.
    assert.expect(2);

    const { createComposerComponent, messaging } = await start({ data: this.data });
    const thread = messaging.models['Thread'].create({
        channel_type: 'livechat',
        id: 10,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
    assert.containsOnce(document.body, '.o_Composer', "should have a composer");
    assert.containsNone(
        document.body,
        '.o_Composer_buttonAttachment',
        "composer linked to livechat should not have a 'Add attachment' button"
    );
});

});
});
