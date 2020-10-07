odoo.define('mail/static/src/components/discuss/tests/discuss_sidebar_tests.js', function (require) {
'use strict';

const { makeDeferred } = require('mail/static/src/utils/deferred/deferred.js');
const {
    afterEach,
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_sidebar_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('sidebar find shows channels matching search term', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({
        channel_partner_ids: [],
        channel_type: 'channel',
        id: 20,
        members: [],
        name: 'test',
        public: 'public',
    });
    const searchReadDef = makeDeferred();
    await this.start({
        async mockRPC(route, args) {
            const res = await this._super(...arguments);
            if (args.method === 'search_read') {
                searchReadDef.resolve();
            }
            return res;
        },
    });
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebar_groupHeaderItemAdd`).click()
    );
    document.querySelector(`.o_DiscussSidebar_itemNew`).focus();
    document.execCommand('insertText', false, "test");
    document.querySelector(`.o_DiscussSidebar_itemNew`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_DiscussSidebar_itemNew`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));

    await searchReadDef;
    await nextAnimationFrame(); // ensures search_read rpc is rendered.
    const results = document.querySelectorAll('.ui-autocomplete .ui-menu-item a');
    assert.ok(
        results,
        "should have autocomplete suggestion after typing on 'find or create channel' input"
    );
    assert.strictEqual(
        results.length,
        // When searching for a single existing channel, the results list will have at least 3 lines:
        // One for the existing channel itself
        // One for creating a public channel with the search term
        // One for creating a private channel with the search term
        3
    );
    assert.strictEqual(
        results[0].textContent,
        "test",
        "autocomplete suggestion should target the channel matching search term"
    );
});

QUnit.test('sidebar find shows channels matching search term even when user is member', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({
        channel_partner_ids: [this.data.currentPartnerId],
        channel_type: 'channel',
        id: 20,
        members: [this.data.currentPartnerId],
        name: 'test',
        public: 'public',
    });
    const searchReadDef = makeDeferred();
    await this.start({
        async mockRPC(route, args) {
            const res = await this._super(...arguments);
            if (args.method === 'search_read') {
                searchReadDef.resolve();
            }
            return res;
        },
    });
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebar_groupHeaderItemAdd`).click()
    );
    document.querySelector(`.o_DiscussSidebar_itemNew`).focus();
    document.execCommand('insertText', false, "test");
    document.querySelector(`.o_DiscussSidebar_itemNew`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_DiscussSidebar_itemNew`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));

    await searchReadDef;
    await nextAnimationFrame();
    const results = document.querySelectorAll('.ui-autocomplete .ui-menu-item a');
    assert.ok(
        results,
        "should have autocomplete suggestion after typing on 'find or create channel' input"
    );
    assert.strictEqual(
        results.length,
        // When searching for a single existing channel, the results list will have at least 3 lines:
        // One for the existing channel itself
        // One for creating a public channel with the search term
        // One for creating a private channel with the search term
        3
    );
    assert.strictEqual(
        results[0].textContent,
        "test",
        "autocomplete suggestion should target the channel matching search term even if user is member"
    );
});

});
});
});

});
