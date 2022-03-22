/** @odoo-module **/

import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_message_edit_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const res = await start(Object.assign({}, params, {
                data: this.data,
                hasDiscuss: true,
            }));
            const { env, widget } = res;
            this.env = env;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('click on message edit button should open edit composer', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['mail.message'].records.push({
        body: 'not empty',
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
    });
    const { click, openDiscuss } = await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    await openDiscuss();
    await click('.o_Message');
    await click('.o_MessageActionList_actionEdit');
    assert.containsOnce(document.body, '.o_Message_composer', 'click on message edit button should open edit composer');
});

});
});
});
