odoo.define('mail/static/src/components/canned_response_suggestion/canned_response_suggestion_tests.js', function (require) {
'use strict';

const components = {
    CannedResponseSuggestion: require('mail/static/src/components/canned_response_suggestion/canned_response_suggestion.js'),
};
const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('canned_response_suggestion', {}, function () {
QUnit.module('canned_response_suggestion_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);
        this.createCannedResponseSuggestion = async cannedResponse => {
            const CannedResponseSuggestionComponent = components.CannedResponseSuggestion;
            CannedResponseSuggestionComponent.env = this.env;
            this.component = new CannedResponseSuggestionComponent(
                null,
                {
                    isActive: true,
                    cannedResponseLocalId: cannedResponse.localId,
                });
            await this.component.mount(this.widget.el);
        };
        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.CannedResponseSuggestion.env;
    },
});

QUnit.test('canned response suggestion displayed', async function (assert) {
    assert.expect(1);

    await this.start();
    const cannedResponse = this.env.models['mail.canned_response'].create({
        description: false,
        id: 1,
        source: 'hello',
        substitution: "Hello Odoo",
    });
    await this.createCannedResponseSuggestion(cannedResponse);

    assert.containsOnce(
        document.body,
        `.o_CannedResponseSuggestion`,
        "Canned response suggestion should be present"
    );
});

QUnit.test('canned response suggestion correct data', async function (assert) {
    assert.expect(5);

    await this.start();
    const cannedResponse = this.env.models['mail.canned_response'].create({
        description: false,
        id: 1,
        source: 'hello',
        substitution: "Hello Odoo",
    });
    await this.createCannedResponseSuggestion(cannedResponse);

    assert.containsOnce(
        document.body,
        '.o_CannedResponseSuggestion',
        "Canned response suggestion should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_CannedResponseSuggestion_source',
        "Canned response source should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_CannedResponseSuggestion_source`).textContent,
        "hello",
        "Canned response source should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_CannedResponseSuggestion_substitution',
        "Canned response substitution should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_CannedResponseSuggestion_substitution`).textContent,
        "Hello Odoo",
        "Canned response substitution should be displayed"
    );
});

QUnit.test('canned response suggestion active', async function (assert) {
    assert.expect(2);

    await this.start();
    const cannedResponse = this.env.models['mail.canned_response'].create({
        description: false,
        id: 1,
        source: 'hello',
        substitution: "Hello Odoo",
    });
    await this.createCannedResponseSuggestion(cannedResponse);

    assert.containsOnce(
        document.body,
        '.o_CannedResponseSuggestion',
        "Canned response suggestion should be present"
    );
    assert.hasClass(
        document.querySelector('.o_CannedResponseSuggestion'),
        'active',
        "should be active initially"
    );
});

});
});
});

});
