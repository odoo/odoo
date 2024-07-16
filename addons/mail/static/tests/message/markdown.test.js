import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("basic rendering of markdown message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<odoo-markdown>**body**</odoo-markdown>",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message .o-mail-Message-content p strong", { text: "body" });
});

test("basic rendering of markdown message with code snippet", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<odoo-markdown>```javascript \n const highlight = 'code'; \n ```</odoo-markdown>",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-content pre code");
});

test(`Markdown links should have target="_blank" attribute`, async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<odoo-markdown>[Odoo](https://odoo.com)</odoo-markdown>",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(`.o-mail-Message-content a[target="_blank"]`);
});

test("Link should not be processed inside a markdown code fence", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const codeSnippet = "https://odoo.com \n" +
          "```html \n" +
          "https://odoo.com \n" +
          "``` \n" +
          "test \n" +
          "```html \n" +
          "https://borderdens.com \n" +
          "```";
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", codeSnippet);
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-content a");
    await contains(".o-mail-Message-content pre code", { count: 2 });
});

test("Mentions should not be processed inside a markdown code fence", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    const codeSnippetOpen = "```html\n";
    const codeSnippetClose = "\n```";
    await insertText(".o-mail-Composer-input", codeSnippetOpen);
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
    await contains(".o-mail-Composer-input", { value: "```html\n@TestPartner "});
    await insertText(".o-mail-Composer-input", codeSnippetClose);
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-content pre code");
    await contains(`.o-mail-Message-content a`, { count: 0 }); // code block should no contains html tags
});

test("Link inside inline code should not be processed", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "https://odoo.com \n `https://odoo.com`");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-content a");
    await contains(".o-mail-Message-content code a", { count: 0 });
});



// list of potential malicious markdown elements that should not be active
// taken from https://book.hacktricks.xyz/pentesting-web/xss-cross-site-scripting/xss-in-markdown
test("Link and image generated by markdown are safe", async () => {
    patchWithCleanup(window, {
        alert() {
            expect.step("markdown link or image should not trigger alerts");
        },
        prompt() {
            expect.step("markdown link or image should not trigger prompts");
        },
    });
    const markdownContent = [
        "[a](javascript:prompt(document.cookie))",
        "[Basic](javascript: alert('Basic'))",
        "[Local Storage](javascript: alert(JSON.stringify(localStorage)))",
        "[CaseInsensitive](JaVaScRiPt: alert('CaseInsensitive'))",
        "[URL](javascript://www.google.com%0Aalert('URL'))",
        `[In Quotes]('javascript:alert("InQuotes")')`,
        "[a](j a v a s c r i p t: prompt(document.cookie))",
        "[a](data: text / html; base64, PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)",
        "[a](javascript: window.onerror = alert; throw% 201)",
        `![Uh oh...]("onerror="alert('XSS'))`,
        `![Uh oh...](https://www.example.com/image.png"onload="alert('XSS'))`,
        `![Escape SRC - onload](https://www.example.com/image.png"onload="alert('ImageOnLoad'))`,
        `![Escape SRC - onerror]("onerror="alert('ImageOnError'))`,
        "[a](j    a   v   a   s   c   r   i   p   t:prompt(document.cookie))",
        "<javascript:prompt(document.cookie)>",
        "<&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29>",
        "![a](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)\\",
        "[a](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)",
        "[a](&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29)",
        `![a'"\`onerror=prompt(document.cookie)](x)\\`,
        "[citelol]: (javascript:prompt(document.cookie))",
        "[notmalicious](javascript:window.onerror=alert;throw%20document.cookie)",
        "[test](javascript://%0d%0aprompt(1))",
        "[test](javascript://%0d%0aprompt(1);com)",
        "[notmalicious](javascript:window.onerror=alert;throw%20document.cookie)",
        "[notmalicious](javascript://%0d%0awindow.onerror=alert;throw%20document.cookie)",
        "[a](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)",
        "[clickme](vbscript:alert(document.domain))",
        // `http://danlec_@.1 style=background-image:url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAABACAMAAADlCI9NAAACcFBMVEX/AAD//////f3//v7/0tL/AQH/cHD/Cwv/+/v/CQn/EBD/FRX/+Pj/ISH/PDz/6Oj/CAj/FBT/DAz/Bgb/rq7/p6f/gID/mpr/oaH/NTX/5+f/mZn/wcH/ICD/ERH/Skr/3Nz/AgL/trb/QED/z8//6+v/BAT/i4v/9fX/ZWX/x8f/aGj/ysr/8/P/UlL/8vL/T0//dXX/hIT/eXn/bGz/iIj/XV3/jo7/W1v/wMD/Hh7/+vr/t7f/1dX/HBz/zc3/nJz/4eH/Zmb/Hx//RET/Njb/jIz/f3//Ojr/w8P/Ghr/8PD/Jyf/mJj/AwP/srL/Cgr/1NT/5ub/PT3/fHz/Dw//eHj/ra3/IiL/DQ3//Pz/9/f/Ly//+fn/UF→
        // `<http://\<meta\ http-equiv=\"refresh\"\ content=\"0;\ url=http://danlec.com/\"\>>`,
        // `[text](http://danlec.com " [@danlec](/danlec) ")`,
        "[a](javascript:this;alert(1))",
        "[a](javascript:this;alert(1&#41;)",
        "[a](javascript&#58this;alert(1&#41;)",
        "[a](Javas&#99;ript:alert(1&#41;)",
        "[a](Javas%26%2399;ript:alert(1&#41;)",
        "[a](javascript:alert&#65534;(1&#41;)",
        "[a](javascript:confirm(1)",
        "[a](javascript://www.google.com%0Aprompt(1))",
        "[a](javascript://%0d%0aconfirm(1);com)",
        "[a](javascript:window.onerror=confirm;throw%201)",
        "[a](javascript:alert(document.domain&#41;)",
        "[a](javascript://www.google.com%0Aalert(1))",
        `[a]('javascript:alert("1")')`,
        "[a](JaVaScRiPt:alert(1))",
        `![a](https://www.google.com/image.png"onload="alert(1))`,
        `![a]("onerror="alert(1))`,
        // "</http://<?php\><\h1\><script:script>confirm(2)",
        // "[XSS](.alert(1);)",
        // "[ ](https://a.de?p=[[/data-x=. style=background-color:#000000;z-index:999;width:100%;position:fixed;top:0;left:0;right:0;bottom:0; data-y=.]])",
        // "[ ](http://a?p=[[/onclick=alert(0) .]])",
        "[a](javascript:new%20Function`al\ert\`1\``;)",
        "[XSS](javascript:prompt(document.cookie))",
        "[XSS](j    a   v   a   s   c   r   i   p   t:prompt(document.cookie))",
        "[XSS](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)",
        "[XSS](&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29)",
        "[XSS]: (javascript:prompt(document.cookie))",
        "[XSS](javascript:window.onerror=alert;throw%20document.cookie)",
        "[XSS](javascript://%0d%0aprompt(1))",
        "[XSS](javascript://%0d%0aprompt(1);com)",
        "[XSS](javascript:window.onerror=alert;throw%20document.cookie)",
        "[XSS](javascript://%0d%0awindow.onerror=alert;throw%20document.cookie)",
        "[XSS](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)",
        "[XSS](vbscript:alert(document.domain))",
        "[XSS](javascript:this;alert(1))",
        "[XSS](javascript:this;alert(1&#41;)",
        "[XSS](javascript&#58this;alert(1&#41;)",
        "[XSS](Javas&#99;ript:alert(1&#41;)",
        "[XSS](Javas%26%2399;ript:alert(1&#41;)",
        "[XSS](javascript:alert&#65534;(1&#41;)",
        "[XSS](javascript:confirm(1)",
        "[XSS](javascript://www.google.com%0Aprompt(1))",
        "[XSS](javascript://%0d%0aconfirm(1);com)",
        "[XSS](javascript:window.onerror=confirm;throw%201)",
        "[XSS](�javascript:alert(document.domain&#41;)",
        "![XSS](javascript:prompt(document.cookie))\\",
        "![XSS](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)\\",
        "![XSS'\"`onerror=prompt(document.cookie)](x)\\",
    ];
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    let lastMessageId;
    for (const markdown of markdownContent) {
        lastMessageId = pyEnv["mail.message"].create({
            body: `<odoo-markdown>**processed** ${markdown}</odoo-markdown>`,
            message_type: "comment",
            model: "discuss.channel",
            author_id: serverState.partnerId,
            res_id: channelId,
        });
    }
    const [member] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([member], {
        seen_message_id: lastMessageId,
        new_message_separator: lastMessageId+ 1
    });
    await start();
    await openDiscuss(channelId);
    await contains("odoo-markdown strong", { count: 30 });
    await tick();
    await scroll(".o-mail-Thread", 0);
    await contains("odoo-markdown strong", { count: 60 });
    await tick();
    await scroll(".o-mail-Thread", 0);
    await contains("odoo-markdown strong", { count: markdownContent.length }); // await markdown processing
    await contains("odoo-markdown a", { count: 0 });
    expect.verifySteps([]);
});
