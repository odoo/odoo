/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred';
import {
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_sidebar_tests.js');

QUnit.test('sidebar find shows channels matching search term', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [],
        channel_type: 'channel',
        name: 'test',
        public: 'public',
    });
    const searchReadDef = makeDeferred();
    const { click } = await start({
        autoOpenDiscuss: true,
        hasDiscuss: true,
        async mockRPC(route, args) {
            const res = await this._super(...arguments);
            if (args.method === 'search_read') {
                searchReadDef.resolve();
            }
            return res;
        },
    });
    await click(`.o_DiscussSidebarCategory_commandAdd`);
    document.querySelector(`.o_DiscussSidebarCategory_addingItem`).focus();
    document.execCommand('insertText', false, "test");
    document.querySelector(`.o_DiscussSidebarCategory_addingItem`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_DiscussSidebarCategory_addingItem`)
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

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
        ],
        channel_type: 'channel',
        name: 'test',
        public: 'public',
    });
    const searchReadDef = makeDeferred();
    const { click } = await start({
        autoOpenDiscuss: true,
        hasDiscuss: true,
        async mockRPC(route, args) {
            const res = await this._super(...arguments);
            if (args.method === 'search_read') {
                searchReadDef.resolve();
            }
            return res;
        },
    });
    await click(`.o_DiscussSidebarCategory_commandAdd`);
    document.querySelector(`.o_DiscussSidebarCategory_addingItem`).focus();
    document.execCommand('insertText', false, "test");
    document.querySelector(`.o_DiscussSidebarCategory_addingItem`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_DiscussSidebarCategory_addingItem`)
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

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create([
        { name: "Xyz" },
        { name: "abc" },
        { name: "Abc" },
        { name: "Xyz" },
    ]);
    await start({
        autoOpenDiscuss: true,
        hasDiscuss: true,
    });
    const results = document.querySelectorAll('.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategoryItem_name');
    assert.deepEqual(
        [results[0].textContent, results[1].textContent, results[2].textContent, results[3].textContent],
        ["abc", "Abc", "Xyz", "Xyz"],
        "Channel name should be in case insensitive alphabetical order"
    );
});

});
});
