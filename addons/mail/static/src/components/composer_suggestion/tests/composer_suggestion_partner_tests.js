/** @odoo-module **/

import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion', {}, function () {
QUnit.module('composer_suggestion_partner_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const res = await start({ ...params, data: this.data });
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

QUnit.test('partner mention suggestion displayed', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerSuggestionComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        im_status: 'online',
        name: "Demo User",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'mail.partner',
        recordLocalId: partner.localId,
    });

    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestion`,
        "Partner mention suggestion should be present"
    );
});

QUnit.test('partner mention suggestion correct data', async function (assert) {
    assert.expect(6);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerSuggestionComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const partner = this.messaging.models['mail.partner'].create({
        email: "demo_user@odoo.com",
        id: 7,
        im_status: 'online',
        name: "Demo User",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'mail.partner',
        recordLocalId: partner.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Partner mention suggestion should be present"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon`).length,
        1,
        "Partner's im_status should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part1',
        "Partner's name should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part1`).textContent,
        "Demo User",
        "Partner's name should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part2',
        "Partner's email should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part2`).textContent,
        "(demo_user@odoo.com)",
        "Partner's email should be displayed"
    );
});

QUnit.test('partner mention suggestion active', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerSuggestionComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const partner = this.messaging.models['mail.partner'].create({
        id: 7,
        im_status: 'online',
        name: "Demo User",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'mail.partner',
        recordLocalId: partner.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Partner mention suggestion should be displayed"
    );
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestion'),
        'active',
        "should be active initially"
    );
});

});
});
});
