odoo.define('mail/static/src/components/partner_mention_suggestion/partner_mention_suggestion_tests.js', function (require) {
'use strict';

const components = {
    PartnerMentionSuggestion: require('mail/static/src/components/partner_mention_suggestion/partner_mention_suggestion.js'),
};
const {
    afterEach,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('partner_mention_suggestion', {}, function () {
QUnit.module('partner_mention_suggestion_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createPartnerMentionSuggestion = async partner => {
            await createRootComponent(this, components.PartnerMentionSuggestion, {
                props: { isActive: true, partnerLocalId: partner.localId },
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

QUnit.test('partner mention suggestion displayed', async function (assert) {
    assert.expect(1);

    await this.start();
    const partner = this.env.models['mail.partner'].create({
        id: 7,
        im_status: 'online',
        name: "Demo User",
    });
    await this.createPartnerMentionSuggestion(partner);

    assert.containsOnce(
        document.body,
        `.o_PartnerMentionSuggestion`,
        "Partner mention suggestion should be present"
    );
});

QUnit.test('partner mention suggestion correct data', async function (assert) {
    assert.expect(6);

    await this.start();
    const partner = this.env.models['mail.partner'].create({
        email: "demo_user@odoo.com",
        id: 7,
        im_status: 'online',
        name: "Demo User",
    });
    await this.createPartnerMentionSuggestion(partner);

    assert.containsOnce(
        document.body,
        '.o_PartnerMentionSuggestion',
        "Partner mention suggestion should be present"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_PartnerImStatusIcon`).length,
        1,
        "Partner's im_status should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_PartnerMentionSuggestion_name',
        "Partner's name should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_PartnerMentionSuggestion_name`).textContent,
        "Demo User",
        "Partner's name should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_PartnerMentionSuggestion_email',
        "Partner's email should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_PartnerMentionSuggestion_email`).textContent,
        "(demo_user@odoo.com)",
        "Partner's email should be displayed"
    );
});

QUnit.test('partner mention suggestion active', async function (assert) {
    assert.expect(2);

    await this.start();
    const partner = this.env.models['mail.partner'].create({
        email: "demo_user@odoo.com",
        id: 7,
        im_status: 'online',
        name: "Demo User",
    });
    await this.createPartnerMentionSuggestion(partner);

    assert.containsOnce(
        document.body,
        '.o_PartnerMentionSuggestion',
        "Partner mention suggestion should be displayed"
    );
    assert.hasClass(
        document.querySelector('.o_PartnerMentionSuggestion'),
        'active',
        "should be active initially"
    );
});

});
});
});

});
