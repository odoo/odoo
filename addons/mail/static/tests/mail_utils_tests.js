/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { addLink, parseAndTransform } from "@mail/utils/common/format";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("Mail utils");

QUnit.test("add_link utility function", function (assert) {
    const testInputs = {
        "http://admin:password@example.com:8/%2020": true,
        "https://admin:password@example.com/test": true,
        "www.example.com:8/test": true,
        "https://127.0.0.5:8069": true,
        "www.127.0.0.5": false,
        "should.notmatch": false,
        "fhttps://test.example.com/test": false,
        "https://www.transifex.com/odoo/odoo-11/translate/#fr/lunch?q=text%3A'La+Tartiflette'": true,
        "https://www.transifex.com/odoo/odoo-11/translate/#fr/$/119303430?q=text%3ATartiflette": true,
        "https://tenor.com/view/chỗgiặt-dog-smile-gif-13860250": true,
        "http://www.boîtenoire.be": true,
        "https://x.com": true,
    };

    for (const [content, willLinkify] of Object.entries(testInputs)) {
        const output = parseAndTransform(content, addLink);
        if (willLinkify) {
            assert.strictEqual(output.indexOf("<a "), 0);
            assert.strictEqual(output.indexOf("</a>"), output.length - 4);
        } else {
            assert.strictEqual(output.indexOf("<a "), -1);
        }
    }
});

QUnit.test("addLink: utility function and special entities", function (assert) {
    const testInputs = {
        // textContent not unescaped
        "<p>https://example.com/?&amp;currency_id</p>":
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/?&amp;currency_id">https://example.com/?&amp;currency_id</a></p>',
        // entities not unescaped
        "&amp; &amp;amp; &gt; &lt;": "&amp; &amp;amp; &gt; &lt;",
        // > and " not linkified since they are not in URL regex
        "<p>https://example.com/&gt;</p>":
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/">https://example.com/</a>&gt;</p>',
        '<p>https://example.com/"hello"&gt;</p>':
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/">https://example.com/</a>"hello"&gt;</p>',
        // & and ' linkified since they are in URL regex
        "<p>https://example.com/&amp;hello</p>":
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/&amp;hello">https://example.com/&amp;hello</a></p>',
        "<p>https://example.com/'yeah'</p>":
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/\'yeah\'">https://example.com/\'yeah\'</a></p>',
        // normal character should not be escaped
        ":'(": ":'(",
        // special character in smileys should be escaped
        "&lt;3": "&lt;3",
        // Already encoded url should not be encoded twice
        "https://odoo.com/%5B%5D": `<a target="_blank" rel="noreferrer noopener" href="https://odoo.com/%5B%5D">https://odoo.com/[]</a>`,
    };

    for (const [content, result] of Object.entries(testInputs)) {
        const output = parseAndTransform(content, addLink);
        assert.strictEqual(output, result);
    }
});

QUnit.test("addLink: linkify inside text node (1 occurrence)", async (assert) => {
    const content = "<p>some text https://somelink.com</p>";
    const linkified = parseAndTransform(content, addLink);
    assert.ok(linkified.startsWith("<p>some text <a"));
    assert.ok(linkified.endsWith("</a></p>"));

    // linkify may add some attributes. Since we do not care of their exact
    // stringified representation, we continue deeper assertion with query
    // selectors.
    const fragment = document.createDocumentFragment();
    const div = document.createElement("div");
    fragment.appendChild(div);
    div.innerHTML = linkified;
    assert.strictEqual(div.textContent, "some text https://somelink.com");
    await contains("a", { target: div });
    assert.strictEqual(div.querySelector(":scope a").textContent, "https://somelink.com");
});

QUnit.test("addLink: linkify inside text node (2 occurrences)", function (assert) {
    // linkify may add some attributes. Since we do not care of their exact
    // stringified representation, we continue deeper assertion with query
    // selectors.
    const content = "<p>some text https://somelink.com and again https://somelink2.com ...</p>";
    const linkified = parseAndTransform(content, addLink);
    const fragment = document.createDocumentFragment();
    const div = document.createElement("div");
    fragment.appendChild(div);
    div.innerHTML = linkified;
    assert.strictEqual(
        div.textContent,
        "some text https://somelink.com and again https://somelink2.com ..."
    );
    assert.strictEqual(div.querySelectorAll(":scope a").length, 2);
    assert.strictEqual(div.querySelectorAll(":scope a")[0].textContent, "https://somelink.com");
    assert.strictEqual(div.querySelectorAll(":scope a")[1].textContent, "https://somelink2.com");
});

QUnit.test("url", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    // see: https://www.ietf.org/rfc/rfc1738.txt
    const messageBody = "https://odoo.com?test=~^|`{}[]#";
    await insertText(".o-mail-Composer-input", messageBody);
    await click("button:enabled", { text: "Send" });
    await contains(".o-mail-Message a", { text: messageBody });
});

QUnit.test("url with comma at the end", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const messageBody = "Go to https://odoo.com, it's great!";
    await insertText(".o-mail-Composer-input", messageBody);
    await click("button:enabled", { text: "Send" });
    await contains(".o-mail-Message a", { text: "https://odoo.com" });
    await contains(".o-mail-Message-content", { text: messageBody });
});

QUnit.test("url with dot at the end", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const messageBody = "Go to https://odoo.com. It's great!";
    await insertText(".o-mail-Composer-input", messageBody);
    await click("button:enabled", { text: "Send" });
    await contains(".o-mail-Message a", { text: "https://odoo.com" });
    await contains(".o-mail-Message-content", { text: messageBody });
});

QUnit.test("url with semicolon at the end", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const messageBody = "Go to https://odoo.com; it's great!";
    await insertText(".o-mail-Composer-input", messageBody);
    await click("button:enabled", { text: "Send" });
    await contains(".o-mail-Message a", { text: "https://odoo.com" });
    await contains(".o-mail-Message-content", { text: messageBody });
});

QUnit.test("url with ellipsis at the end", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const messageBody = "Go to https://odoo.com... it's great!";
    await insertText(".o-mail-Composer-input", messageBody);
    await click("button:enabled", { text: "Send" });
    await contains(".o-mail-Message a", { text: "https://odoo.com" });
    await contains(".o-mail-Message-content", { text: messageBody });
});

QUnit.test("url with number in subdomain", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const messageBody = "https://www.45017478-master-all.runbot134.odoo.com/web";
    await insertText(".o-mail-Composer-input", messageBody);
    await click("button:enabled", { text: "Send" });
    await contains(".o-mail-Message a", {
        text: "https://www.45017478-master-all.runbot134.odoo.com/web",
    });
});
