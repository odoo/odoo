/** @odoo-module **/

import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion', {}, function () {
QUnit.module('composer_suggestion_canned_response_tests.js', {
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

QUnit.test('canned response suggestion displayed', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerSuggestionComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const cannedResponse = this.messaging.models['mail.canned_response'].create({
        id: 7,
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'mail.canned_response',
        recordLocalId: cannedResponse.localId,
    });

    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestion`,
        "Canned response suggestion should be present"
    );
});

QUnit.test('canned response suggestion correct data', async function (assert) {
    assert.expect(5);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerSuggestionComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const cannedResponse = this.messaging.models['mail.canned_response'].create({
        id: 7,
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'mail.canned_response',
        recordLocalId: cannedResponse.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Canned response suggestion should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part1',
        "Canned response source should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part1`).textContent,
        "hello",
        "Canned response source should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part2',
        "Canned response substitution should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part2`).textContent,
        "Hello, how are you?",
        "Canned response substitution should be displayed"
    );
});

QUnit.test('canned response suggestion active', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerSuggestionComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const cannedResponse = this.messaging.models['mail.canned_response'].create({
        id: 7,
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'mail.canned_response',
        recordLocalId: cannedResponse.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Canned response suggestion should be displayed"
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
