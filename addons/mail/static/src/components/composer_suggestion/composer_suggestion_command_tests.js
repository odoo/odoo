/** @odoo-module **/

import ComposerSuggestion from '@mail/components/composer_suggestion/composer_suggestion';
import { link } from '@mail/model/model_field_command';
import {
    afterEach,
    beforeEach,
    createRootComponent,
    start,
} from '@mail/utils/test_utils';

const components = { ComposerSuggestion };

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion', {}, function () {
QUnit.module('composer_suggestion_command_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createComposerSuggestion = async props => {
            await createRootComponent(this, components.ComposerSuggestion, {
                props,
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('command suggestion displayed', async function (assert) {
    assert.expect(1);

    await this.start();
    const command = this.env.models['mail.channel_command'].create({
        name: 'whois',
        help: "Displays who it is",
    });
    await this.createComposerSuggestion({
        suggestionListItemLocalId: this.env.models['mail.suggestion_list_item'].create({
            record: link(command),
        }).localId
    });

    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestion`,
        "Command suggestion should be present"
    );
});

QUnit.test('command suggestion correct data', async function (assert) {
    assert.expect(5);

    await this.start();
    const command = this.env.models['mail.channel_command'].create({
        name: 'whois',
        help: "Displays who it is",
    });
    await this.createComposerSuggestion({
        suggestionListItemLocalId: this.env.models['mail.suggestion_list_item'].create({
            record: link(command),
        }).localId
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Command suggestion should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part1',
        "Command name should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part1`).textContent,
        "whois",
        "Command name should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part2',
        "Command help should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part2`).textContent,
        "Displays who it is",
        "Command help should be displayed"
    );
});

QUnit.test('command suggestion should be highlighted according to its corresponding value', async function (assert) {
    assert.expect(2);

    await this.start();
    const command = this.env.models['mail.channel_command'].create({
        name: 'whois',
        help: "Displays who it is",
    });
    await this.createComposerSuggestion({
        suggestionListItemLocalId: this.env.models['mail.suggestion_list_item'].create({
            isHighlighted: true,
            record: link(command),
        }).localId
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Command suggestion should be displayed"
    );
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestion'),
        'active',
        "should be highlighted according to its corresponding value"
    );
});

});
});
});
