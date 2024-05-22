odoo.define('mail/static/src/components/dialog_manager/dialog_manager_tests.js', function (require) {
'use strict';

const { makeDeferred } = require('mail/static/src/utils/deferred/deferred.js');
const {
    afterEach,
    beforeEach,
    nextAnimationFrame,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('dialog_manager', {}, function () {
QUnit.module('dialog_manager_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign(
                { hasDialog: true },
                params,
                { data: this.data }
            ));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('[technical] messaging not created', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(2);

    const messagingBeforeCreationDeferred = makeDeferred();
    await this.start({
        messagingBeforeCreationDeferred,
        waitUntilMessagingCondition: 'none',
    });
    assert.containsOnce(
        document.body,
        '.o_DialogManager',
        "should have dialog manager even when messaging is not yet created"
    );

    // simulate messaging being created
    messagingBeforeCreationDeferred.resolve();
    await nextAnimationFrame();

    assert.containsOnce(
        document.body,
        '.o_DialogManager',
        "should still contain dialog manager after messaging has been created"
    );
});

QUnit.test('initial mount', async function (assert) {
    assert.expect(1);

    await this.start();
    assert.containsOnce(
        document.body,
        '.o_DialogManager',
        "should have dialog manager"
    );
});

});
});
});

});
