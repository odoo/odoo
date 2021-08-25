/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred/deferred';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
    start,
} from '@mail/utils/test_utils';

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
        document.querySelector(`.o_DiscussSidebarCategory_commandAdd`).click()
    );
    document.querySelector(`.o_DiscussSidebarCategory_newItem`).focus();
    document.execCommand('insertText', false, "test");
    document.querySelector(`.o_DiscussSidebarCategory_newItem`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_DiscussSidebarCategory_newItem`)
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
        document.querySelector(`.o_DiscussSidebarCategory_commandAdd`).click()
    );
    document.querySelector(`.o_DiscussSidebarCategory_newItem`).focus();
    document.execCommand('insertText', false, "test");
    document.querySelector(`.o_DiscussSidebarCategory_newItem`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_DiscussSidebarCategory_newItem`)
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

QUnit.test('sidebar channels should be ordered case insensitive alphabetically', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push(
        { id: 19, name: "Xyz" },
        { id: 20, name: "abc" },
        { id: 21, name: "Abc" },
        { id: 22, name: "Xyz" }
    );
    await this.start();
    const results = document.querySelectorAll('.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategoryItem_name');
    assert.deepEqual(
        [results[0].textContent, results[1].textContent, results[2].textContent, results[3].textContent],
        ["abc", "Abc", "Xyz", "Xyz"],
        "Channel name should be in case insensitive alphabetical order"
    );
});

});
});
});
