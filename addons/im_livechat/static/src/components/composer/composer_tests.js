odoo.define('im_livechat/static/src/components/composer/composer_tests.js', function (require) {
'use strict';

const components = {
    Composer: require('mail/static/src/components/composer/composer.js'),
};
const {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer', {}, function () {
QUnit.module('composer_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createComposerComponent = async (composer, otherProps) => {
            const ComposerComponent = components.Composer;
            ComposerComponent.env = this.env;
            this.component = new ComposerComponent(null, Object.assign({
                composerLocalId: composer.localId,
            }, otherProps));
            delete ComposerComponent.env;
            await afterNextRender(() => this.component.mount(this.widget.el));
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

QUnit.test('livechat: no add attachment button', async function (assert) {
    // Attachments are not yet supported in livechat, especially from livechat
    // visitor PoV. This may likely change in the future with task-2029065.
    assert.expect(2);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        channel_type: 'livechat',
        id: 10,
        model: 'mail.channel',
    });
    await this.createComposerComponent(thread.composer);
    assert.containsOnce(document.body, '.o_Composer', "should have a composer");
    assert.containsNone(
        document.body,
        '.o_Composer_buttonAttachment',
        "composer linked to livechat should not have a 'Add attachment' button"
    );
});

});
});
});

});
