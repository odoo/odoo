/** @odoo-module **/

import * as utils from '@mail/js/utils';
import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module('mail', {}, function () {

QUnit.module('Mail utils');

QUnit.test('add_link utility function', function (assert) {
    assert.expect(29);

    var testInputs = {
        'http://admin:password@example.com:8/%2020': true,
        'https://admin:password@example.com/test': true,
        'www.example.com:8/test': true,
        'https://127.0.0.5:8069': true,
        'www.127.0.0.5': false,
        'should.notmatch': false,
        'fhttps://test.example.com/test': false,
        "https://www.transifex.com/odoo/odoo-11/translate/#fr/lunch?q=text%3A'La+Tartiflette'": true,
        'https://www.transifex.com/odoo/odoo-11/translate/#fr/$/119303430?q=text%3ATartiflette': true,
        'https://tenor.com/view/chỗgiặt-dog-smile-gif-13860250': true,
        'http://www.boîtenoire.be': true,
        // Subdomain different than `www` with long domain name
        'https://xyz.veryveryveryveryverylongdomainname.com/example': true,
        // Two subdomains
        'https://abc.xyz.veryveryveryveryverylongdomainname.com/example': true,
        // Long domain name with www
        'https://www.veryveryveryveryverylongdomainname.com/example': true,
        // Subdomain with numbers
        'https://www.45017478-master-all.runbot134.odoo.com/web': true,
        "https://x.com": true,
    };

    _.each(testInputs, function (willLinkify, content) {
        var output = utils.parseAndTransform(content, utils.addLink);
        if (willLinkify) {
            assert.strictEqual(output.indexOf('<a '), 0, "There should be a link");
            assert.strictEqual(output.indexOf('</a>'), (output.length - 4), "Link should match the whole text");
        } else {
            assert.strictEqual(output.indexOf('<a '), -1, "There should be no link");
        }
    });
});

QUnit.test('addLink: utility function and special entities', function (assert) {
    assert.expect(8);

    var testInputs = {
        // textContent not unescaped
        '<p>https://example.com/?&amp;currency_id</p>':
        '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/?&amp;currency_id">https://example.com/?&amp;currency_id</a></p>',
        // entities not unescaped
        '&amp; &amp;amp; &gt; &lt;': '&amp; &amp;amp; &gt; &lt;',
        // > and " not linkified since they are not in URL regex
        '<p>https://example.com/&gt;</p>':
        '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/">https://example.com/</a>&gt;</p>',
        '<p>https://example.com/"hello"&gt;</p>':
        '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/">https://example.com/</a>"hello"&gt;</p>',
        // & and ' linkified since they are in URL regex
        '<p>https://example.com/&amp;hello</p>':
        '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/&amp;hello">https://example.com/&amp;hello</a></p>',
        '<p>https://example.com/\'yeah\'</p>':
        '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/\'yeah\'">https://example.com/\'yeah\'</a></p>',
        // normal character should not be escaped
        ':\'(': ':\'(',
        // special character in smileys should be escaped
        '&lt;3': '&lt;3',
    };

    _.each(testInputs, function (result, content) {
        var output = utils.parseAndTransform(content, utils.addLink);
        assert.strictEqual(output, result);
    });
});

QUnit.test('addLink: linkify inside text node (1 occurrence)', function (assert) {
    assert.expect(5);

    const content = '<p>some text https://somelink.com</p>';
    const linkified = utils.parseAndTransform(content, utils.addLink);
    assert.ok(
        linkified.startsWith('<p>some text <a'),
        "linkified text should start with non-linkified start part, followed by an '<a>' tag"
    );
    assert.ok(
        linkified.endsWith('</a></p>'),
        "linkified text should end with closing '<a>' tag"
    );

    // linkify may add some attributes. Since we do not care of their exact
    // stringified representation, we continue deeper assertion with query
    // selectors.
    const fragment = document.createDocumentFragment();
    const div = document.createElement('div');
    fragment.appendChild(div);
    div.innerHTML = linkified;
    assert.strictEqual(
        div.textContent,
        'some text https://somelink.com',
        "linkified text should have same text content as non-linkified version"
    );
    assert.strictEqual(
        div.querySelectorAll(':scope a').length,
        1,
        "linkified text should have an <a> tag"
    );
    assert.strictEqual(
        div.querySelector(':scope a').textContent,
        'https://somelink.com',
        "text content of link should be equivalent of its non-linkified version"
    );
});

QUnit.test('addLink: linkify inside text node (2 occurrences)', function (assert) {
    assert.expect(4);

    // linkify may add some attributes. Since we do not care of their exact
    // stringified representation, we continue deeper assertion with query
    // selectors.
    const content = '<p>some text https://somelink.com and again https://somelink2.com ...</p>';
    const linkified = utils.parseAndTransform(content, utils.addLink);
    const fragment = document.createDocumentFragment();
    const div = document.createElement('div');
    fragment.appendChild(div);
    div.innerHTML = linkified;
    assert.strictEqual(
        div.textContent,
        'some text https://somelink.com and again https://somelink2.com ...',
        "linkified text should have same text content as non-linkified version"
    );
    assert.strictEqual(
        div.querySelectorAll(':scope a').length,
        2,
        "linkified text should have 2 <a> tags"
    );
    assert.strictEqual(
        div.querySelectorAll(':scope a')[0].textContent,
        'https://somelink.com',
        "text content of 1st link should be equivalent to its non-linkified version"
    );
    assert.strictEqual(
        div.querySelectorAll(':scope a')[1].textContent,
        'https://somelink2.com',
        "text content of 2nd link should be equivalent to its non-linkified version"
    );
});

QUnit.test("url", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    // see: https://www.ietf.org/rfc/rfc1738.txt
    const messageBody = "https://odoo.com?test=~^|`{}[]#";
    await insertText(".o_ComposerTextInput_textarea", messageBody);
    await click("button:contains(Send)");
    assert.containsOnce($, `.o_Message a:contains(${messageBody})`);
});

QUnit.test("url with comma at the end", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    const messageBody = "Go to https://odoo.com, it's great!";
    await insertText(".o_ComposerTextInput_textarea", messageBody);
    await click("button:contains(Send)");
    assert.containsOnce($, `.o_Message a:contains(https://odoo.com)`);
    assert.containsOnce($, `.o_Message:contains(${messageBody})`);
});

QUnit.test("url with dot at the end", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    const messageBody = "Go to https://odoo.com. It's great!";
    await insertText(".o_ComposerTextInput_textarea", messageBody);
    await click("button:contains(Send)");
    assert.containsOnce($, `.o_Message a:contains(https://odoo.com)`);
    assert.containsOnce($, `.o_Message:contains(${messageBody})`);
});

QUnit.test("url with semicolon at the end", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    const messageBody = "Go to https://odoo.com; it's great!";
    await insertText(".o_ComposerTextInput_textarea", messageBody);
    await click("button:contains(Send)");
    assert.containsOnce($, `.o_Message a:contains(https://odoo.com)`);
    assert.containsOnce($, `.o_Message:contains(${messageBody})`);
});

QUnit.test("url with ellipsis at the end", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    const messageBody = "Go to https://odoo.com... it's great!";
    await insertText(".o_ComposerTextInput_textarea", messageBody);
    await click("button:contains(Send)");
    assert.containsOnce($, `.o_Message a:contains(https://odoo.com)`);
    assert.containsOnce($, `.o_Message:contains(${messageBody})`);
});

});
