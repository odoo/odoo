import { addLink, parseAndTransform } from "@mail/utils/common/format";
import { useSequential } from "@mail/utils/common/hooks";
import {
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "./mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";

describe.current.tags("desktop");
defineMailModels();

test("add_link utility function", () => {
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
        "https://github.com/odoo/enterprise/compare/16.0...odoo-dev:enterprise:16.0-voip-fix_demo_data-tsm?expand=1": true,
        "https://github.com/odoo/enterprise/compare/16.0...16.0-voip-fix_demo_data-tsm?expand=1": true,
        "https://github.com/odoo/enterprise/compare/16.0...chỗgiặt-voip-fix_demo_data-tsm?expand=1": true,
        "https://github.com/odoo/enterprise/compare/chỗgiặt...chỗgiặt-voip-fix_demo_data-tsm?expand=1": true,
        "https://github.com/odoo/enterprise/compare/@...}-voip-fix_demo_data-tsm?expand=1": true,
        "https://x.com": true,
    };

    for (const [content, willLinkify] of Object.entries(testInputs)) {
        const output = parseAndTransform(content, addLink);
        if (willLinkify) {
            expect(output.indexOf("<a ")).toBe(0);
            expect(output.indexOf("</a>")).toBe(output.length - 4);
        } else {
            expect(output.indexOf("<a ")).toBe(-1);
        }
    }
});

test("addLink: utility function and special entities", () => {
    const testInputs = [
        // textContent not unescaped
        [
            markup`<p>https://example.com/?&amp;currency_id</p>`,
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/?&amp;currency_id">https://example.com/?&amp;currency_id</a></p>',
        ],
        // entities not unescaped
        [markup`&amp; &amp;amp; &gt; &lt;`, "&amp; &amp;amp; &gt; &lt;"],
        // > and " not linkified since they are not in URL regex
        [
            markup`<p>https://example.com/&gt;</p>`,
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/">https://example.com/</a>&gt;</p>',
        ],
        [
            markup`<p>https://example.com/"hello"&gt;</p>`,
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/">https://example.com/</a>"hello"&gt;</p>',
        ],
        // & and ' linkified since they are in URL regex
        [
            markup`<p>https://example.com/&amp;hello</p>`,
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/&amp;hello">https://example.com/&amp;hello</a></p>',
        ],
        [
            markup`<p>https://example.com/'yeah'</p>`,
            '<p><a target="_blank" rel="noreferrer noopener" href="https://example.com/\'yeah\'">https://example.com/\'yeah\'</a></p>',
        ],
        [markup`<p>:'(</p>`, "<p>:'(</p>"],
        [markup`:'(`, ":&#x27;("],
        ["<p>:'(</p>", "&lt;p&gt;:&#x27;(&lt;/p&gt;"],
        [":'(", ":&#x27;("],
        [markup`<3`, "&lt;3"],
        [markup`&lt;3`, "&lt;3"],
        ["<3", "&lt;3"],
        // Already encoded url should not be encoded twice
        [
            markup`https://odoo.com/%5B%5D`,
            `<a target="_blank" rel="noreferrer noopener" href="https://odoo.com/%5B%5D">https://odoo.com/[]</a>`,
        ],
    ];

    for (const [content, result] of testInputs) {
        const output = parseAndTransform(content, addLink);
        expect(output).toBeInstanceOf(markup().constructor);
        expect(output.toString()).toBe(result);
    }
});

test("addLink: linkify inside text node (1 occurrence)", async () => {
    const content = markup`<p>some text https://somelink.com</p>`;
    const linkified = parseAndTransform(content, addLink);
    expect(linkified.startsWith("<p>some text <a")).toBe(true);
    expect(linkified.endsWith("</a></p>")).toBe(true);

    // linkify may add some attributes. Since we do not care of their exact
    // stringified representation, we continue deeper assertion with query
    // selectors.
    const fragment = document.createDocumentFragment();
    const div = document.createElement("div");
    fragment.appendChild(div);
    div.innerHTML = linkified;
    expect(div).toHaveText("some text https://somelink.com");
    await contains("a", { target: div });
    expect(div.querySelector(":scope a")).toHaveText("https://somelink.com");
});

test("addLink: linkify inside text node (2 occurrences)", () => {
    // linkify may add some attributes. Since we do not care of their exact
    // stringified representation, we continue deeper assertion with query
    // selectors.
    const content = markup(
        "<p>some text https://somelink.com and again https://somelink2.com ...</p>"
    );
    const linkified = parseAndTransform(content, addLink);
    const fragment = document.createDocumentFragment();
    const div = document.createElement("div");
    fragment.appendChild(div);
    div.innerHTML = linkified;
    expect(div).toHaveText("some text https://somelink.com and again https://somelink2.com ...");
    expect(div.querySelectorAll(":scope a")).toHaveCount(2);
    expect(div.querySelectorAll(":scope a")[0]).toHaveText("https://somelink.com");
    expect(div.querySelectorAll(":scope a")[1]).toHaveText("https://somelink2.com");
});

test("url", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // see: https://www.ietf.org/rfc/rfc1738.txt
    const messageBody = "https://odoo.com?test=~^|`{}[]#";
    await insertText(".o-mail-Composer-input", messageBody);
    await press("Enter");
    await contains(`.o-mail-Message a:contains(${messageBody})`);
});

test("url with comma at the end", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    const messageBody = "Go to https://odoo.com, it's great!";
    await insertText(".o-mail-Composer-input", messageBody);
    await press("Enter");
    await contains(".o-mail-Message a:contains(https://odoo.com)");
    await contains(`.o-mail-Message-content:contains(${messageBody}`);
});

test("url with dot at the end", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    const messageBody = "Go to https://odoo.com. It's great!";
    await insertText(".o-mail-Composer-input", messageBody);
    await press("Enter");
    await contains(".o-mail-Message a:contains(https://odoo.com)");
    await contains(`.o-mail-Message-content:contains(${messageBody})`);
});

test("url with semicolon at the end", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    const messageBody = "Go to https://odoo.com; it's great!";
    await insertText(".o-mail-Composer-input", messageBody);
    await press("Enter");
    await contains(".o-mail-Message a:contains(https://odoo.com)");
    await contains(`.o-mail-Message-content:contains(${messageBody})`);
});

test("url with ellipsis at the end", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    const messageBody = "Go to https://odoo.com... it's great!";
    await insertText(".o-mail-Composer-input", messageBody);
    await press("Enter");
    await contains(".o-mail-Message a:contains(https://odoo.com)");
    await contains(`.o-mail-Message-content:contains(${messageBody})`);
});

test("url with number in subdomain", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    const messageBody = "https://www.45017478-master-all.runbot134.odoo.com/odoo";
    await insertText(".o-mail-Composer-input", messageBody);
    await press("Enter");
    await contains(
        ".o-mail-Message a:contains(https://www.45017478-master-all.runbot134.odoo.com/odoo)"
    );
});

test("isSequential doesn't execute intermediate call.", async () => {
    const sequential = useSequential();
    let index = 0;
    const sequence = () => {
        index++;
        const i = index;
        return sequential(async () => {
            expect.step(i.toString());
            return new Promise((r) => setTimeout(() => r(i), 1));
        });
    };
    const result = await Promise.all([sequence(), sequence(), sequence(), sequence(), sequence()]);
    expect(result).toEqual([1, undefined, undefined, undefined, 5]);
    expect.verifySteps(["1", "5"]);
});
