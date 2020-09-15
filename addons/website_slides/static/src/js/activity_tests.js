odoo.define('website_slides/static/src/js/activity_tests.js', function (require) {
'use strict';

const components = {
    Activity: require('mail/static/src/components/activity/activity.js'),
};
const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const Bus = require('web.Bus');
const { date_to_str } = require('web.time');
const { Component, tags: { xml } } = owl;

QUnit.module('website_slides', {}, function () {
QUnit.module('static', {}, function () {
QUnit.module('src', {}, function () {
QUnit.module('js', {}, function () {
QUnit.module('activity_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createActivityComponent = async function (activity) {
            await createRootComponent(this, components.Activity, {
                props: { activityLocalId: activity.localId },
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

QUnit.only('website slides activity layout', async function (assert) {
    assert.expect(3);
    await this.start();
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        assignee: [['insert', { id: 1, model: "res.user"}]],
        creator:[['insert', { id: 7, model: "res.user",
            partner: [['insert', {id:5, model:"res.partner"}]],
            partnerDisplayName: "Joel Willis"}]],
        type: [['insert', { id: 7, displayName: "Access Request"}]],
        res_id: 1,
        id: 1,
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_GrantAccessButton').length,
        1,
        "should have grant access button"
    );
    await afterNextRender(() => {
        document.querySelector('.o_Activity_GrantAccessButton').click();
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_RefuseAccessButton').length,
        1,
        "should have refuse access button"
    );
    await afterNextRender(() => {
        document.querySelector('.o_Activity_RefuseAccessButton').click();
    });

});
});
});
});
});
});