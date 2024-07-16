import {
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

let i = 1;
function assert(input, output) {
    test(`test ${i}`, async () => {
        patchWithCleanup(window, {
            alert() {
                expect.step("markdown link or image should not trigger alerts");
            },
            prompt() {
                expect.step("markdown link or image should not trigger prompts");
            },
        });
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "general" });
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        pyEnv["res.users"].create({
            partner_id: partnerId,
            name: "Demo",
        });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: `<odoo-markdown>${input}</odoo-markdown>`,
            date: "2019-04-20 10:00:00",
            model: "discuss.channel",
            res_id: channelId,
        });
        await start();
        await openDiscuss(channelId);
        await contains(".o-mail-Message-body odoo-markdown");
        expect(queryFirst(".o-mail-Message-body odoo-markdown").innerHTML).toBe(output);
        expect.verifySteps([]);
    });
    i++;
}

// list of potential malicious markdown elements that should not be active
// taken from https://book.hacktricks.xyz/pentesting-web/xss-cross-site-scripting/xss-in-markdown
assert("[a](javascript:prompt(document.cookie))", "<p>a</p>\n");
assert("[Basic](javascript: alert('Basic'))", "<p>[Basic](javascript: alert('Basic'))</p>\n");
assert(
    "[Local Storage](javascript: alert(JSON.stringify(localStorage)))",
    "<p>[Local Storage](javascript: alert(JSON.stringify(localStorage)))</p>\n"
);
assert(
    "[CaseInsensitive](JaVaScRiPt: alert('CaseInsensitive'))",
    "<p>[CaseInsensitive](JaVaScRiPt: alert('CaseInsensitive'))</p>\n"
);
assert("[URL](javascript://www.google.com%0Aalert('URL'))", "<p>URL</p>\n");
assert(`[In Quotes]('javascript:alert("InQuotes")')`, "<p>In Quotes</p>\n");
assert(
    "[a](j a v a s c r i p t: prompt(document.cookie))",
    "<p>[a](j a v a s c r i p t: prompt(document.cookie))</p>\n"
);
assert(
    "[a](data: text / html; base64, PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)", // <script>alert('XSS)</script> in base64
    "<p>[a](data: text / html; base64, PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)</p>\n"
);
assert(
    "[a](javascript: window.onerror = alert; throw% 201)",
    "<p>[a](javascript: window.onerror = alert; throw% 201)</p>\n"
);
assert(
    `![Uh oh...]("onerror="alert('XSS'))`,
    `<p><img alt="Uh oh..." src="%22onerror=%22alert('XSS')"></p>\n`
);
assert(
    `![Uh oh...](https://www.example.com/image.png"onload="alert('XSS'))`,
    `<p><img alt="Uh oh..." src="https://www.example.com/image.png%22onload=%22alert('XSS')"></p>\n`
);
assert(
    `![Escape SRC - onload](https://www.example.com/image.png"onload="alert('ImageOnLoad'))`,
    `<p><img alt="Escape SRC - onload" src="https://www.example.com/image.png%22onload=%22alert('ImageOnLoad')"></p>\n`
);
assert(
    `![Escape SRC - onerror]("onerror="alert('ImageOnError'))`,
    `<p><img alt="Escape SRC - onerror" src="%22onerror=%22alert('ImageOnError')"></p>\n`
);
assert(
    "[a](j    a   v   a   s   c   r   i   p   t:prompt(document.cookie))",
    "<p>[a](j    a   v   a   s   c   r   i   p   t:prompt(document.cookie))</p>\n"
);
assert(
    "<javascript:prompt(document.cookie)>",
    "<p>javascript:prompt(document.cookie)&lt;/javascript:prompt(document.cookie)&gt;</p>\n"
);
assert(
    "<&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29>",
    "<p>&lt;javascript:alert('XSS')&gt;</p>\n"
);
assert(
    "![a](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)\\", // <script>alert('XSS)</script> in base64
    `<p><img alt="a" src="data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K">\\</p>\n`
);
assert("[a](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)", "<p>a</p>\n"); // <script>alert('XSS)</script> in base64
assert(
    "[a](&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29)",
    "<p>a</p>\n"
);
assert(
    `![a'"\`onerror=prompt(document.cookie)](x)\\`,
    `<p>![a'"\`onerror=prompt(document.cookie)](x)\\</p>\n`
);
assert("[citelol]: (javascript:prompt(document.cookie))", "");
assert(
    "[notmalicious](javascript:window.onerror=alert;throw%20document.cookie)",
    "<p>notmalicious</p>\n"
);
assert("[test](javascript://%0d%0aprompt(1))", "<p>test</p>\n");
assert("[test](javascript://%0d%0aprompt(1);com)", "<p>test</p>\n");
assert(
    "[notmalicious](javascript:window.onerror=alert;throw%20document.cookie)",
    "<p>notmalicious</p>\n"
);
assert(
    "[notmalicious](javascript://%0d%0awindow.onerror=alert;throw%20document.cookie)",
    "<p>notmalicious</p>\n"
);
assert("[a](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)", "<p>a</p>\n"); // <script>alert('XSS)</script> in base64
assert("[clickme](vbscript:alert(document.domain))", "<p>clickme</p>\n");
assert(
    `_http://danlec_@.1 style=background-image:url(data:image/png;base64,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);background-repeat:no-repeat;display:block;width:100%;height:100px; onclick=alert(unescape(/Oh%20No!/.source));return(false);//`,
    `<p><em><a rel="noreferrer noopener" target="_blank" href="http://danlec">http://danlec</a></em>@.1 style=background-image:url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAABACAMAAADlCI9NAAACcFBMVEX/AAD//////f3//v7/0tL/AQH/cHD/Cwv/+/v/CQn/EBD/FRX/+Pj/ISH/PDz/6Oj/CAj/FBT/DAz/Bgb/rq7/p6f/gID/mpr/oaH/NTX/5+f/mZn/wcH/ICD/ERH/Skr/3Nz/AgL/trb/QED/z8//6+v/BAT/i4v/9fX/ZWX/x8f/aGj/ysr/8/P/UlL/8vL/T0//dXX/hIT/eXn/bGz/iIj/XV3/jo7/W1v/wMD/Hh7/+vr/t7f/1dX/HBz/zc3/nJz/4eH/Zmb/Hx//RET/Njb/jIz/f3//Ojr/w8P/Ghr/8PD/Jyf/mJj/AwP/srL/Cgr/1NT/5ub/PT3/fHz/Dw//eHj/ra3/IiL/DQ3//Pz/9/f/Ly//+fn/UFD/MTH/vb3/7Oz/pKT/1tb/2tr/jY3/6en/QkL/5OT/ubn/JSX/MjL/Kyv/Fxf/Rkb/sbH/39//iYn/q6v/qqr/Y2P/Li7/wsL/uLj/4+P/yMj/S0v/GRn/cnL/hob/l5f/s7P/Tk7/WVn/ior/09P/hYX/bW3/GBj/XFz/aWn/Q0P/vLz/KCj/kZH/5eX/U1P/Wlr/cXH/7+//Kir/r6//LS3/vr7/lpb/lZX/WFj/ODj/a2v/TU3/urr/tbX/np7/BQX/SUn/Bwf/4uL/d3f/ExP/y8v/NDT/KSn/goL/8fH/qan/paX/2Nj/HR3/4OD/VFT/Z2f/SEj/bm7/v7//RUX/Fhb/ycn/V1f/m5v/IyP/xMT/rKz/oKD/7e3/dHT/h4f/Pj7/b2//fn7/oqL/7u7/2dn/TEz/Gxv/6ur/3d3/Nzf/k5P/EhL/Dg7/o6P/UVHe/LWIAAADf0lEQVR4Xu3UY7MraRRH8b26g2Pbtn1t27Zt37Ft27Zt6yvNpPqpPp3GneSeqZo3z3r5T1XXL6nOFnc6nU6n0+l046tPruw/+Vil/C8tvfscquuuOGTPT2ZnRySwWaFQqGG8Y6j6Zzgggd0XChWLf/U1OFoQaVJ7AayUwPYALHEM6UCWBDYJbhXfHjUBOHvVqz8YABxfnDCArrED7jSAs13Px4Zo1jmA7eGEAXvXjRVQuQE4USWqp5pNoCthALePFfAQ0OcchoCGBAEPgPGiE7AiacChDfBmjjg7DVztAKRtnJsXALj/Hpiy2B9wofqW9AQAg8Bd8VOpCR02YMVEE4xli/L8AOmtQMQHsP9IGUBZedq/AWJfIez+x4KZqgDtBlbzon6A8GnonOwBXNONavlmUS2Dx8XTjcCwe1wNvGQB2gxaKhbV7Ubx3QC5bRMUuAEvA9kFzzW3TQAeVoB5cFw8zQUGPH9M4LwFgML5IpL6BHCvH0DmAD3xgIUpUJcTmy7UQHaV/bteKZ6GgGr3eAq4QQEmWlNqJ1z0BeTvgGfz4gAFsDXfUmbeAeoAF0OfuLL8C91jHnCtBchYq7YzsMsXIFkmDDsBjwBfi2o6GM9IrOshIp5mA6vc42Sg1wJMEVUJlPgDpBzWb3EAVsMOm5m7Hg5KrAjcJJ5uRn3uLAvosgBrRPUgnAgApC2HjtpRwFTneZRpqLs6Ak+Lp5lAj9+LccoCzLYPZjBA3gIGRgHj4EuxewH6JdZhKBVPM4CL7rEIiKo7kMAvILIEXplvA/bCR2JXAYMSawtkiqfaDHjNtYVfhzJJBvBGJ3zmADhv6054W71ZrBNvHZDigr0DDCcFkHeB8wog70G/2LXA+xIrh03i02Zgavx0Blo+SA5Q+yEcrVSAYvjYBhwEPrEoDZ+KX20wIe7G1ZtwTJIDyMYU+FwBeuGLpaLqg91NcqnqgQU9Yre/ETpzkwXIIKAAmRnQruboUeiVS1cHmF8pcv70bqBVkgak1tgAaYbuw9bj9kFjVN28wsJvxK9VFQDGzjVF7d9+9z1ARJIHyMxRQNo2SDn2408HBsY5njZJPcFbTomJo59H5HIAUmIDpPQXVGS0igfg7detBqptv/0ulwfIbbQB8kchVtNmiQsQUO7Qru37jpQX7WmS/6YZPXP+LPprbVgC0ul0Op1Op9Pp/gYrAa7fWhG7QQAAAABJRU5ErkJggg==);background-repeat:no-repeat;display:block;width:100%;height:100px; onclick=alert(unescape(/Oh%20No!/.source));return(false);//</p>\n`
);
assert(
    `<http://<meta http-equiv="refresh" content="0; url=http://danlec.com/">>`,
    `<p>&lt;http: &lt;meta="" http-equiv="refresh" content="0; url=<a rel="noreferrer noopener" target="_blank" href="http://danlec.com/%22%3E%3E">http://danlec.com/"&gt;&gt;</a></p>\n`
);
assert(
    `[text](http://danlec.com " [@danlec](/danlec) ")`,
    `<p><a rel="noreferrer noopener" target="_blank" title="[@danlec](/danlec)" href="http://danlec.com">text</a></p>\n`
);
assert("[a](javascript:this;alert(1))", "<p>a</p>\n");
assert("[a](javascript:this;alert(1&#41;)", "<p>a</p>\n");
assert("[a](javascript&#58this;alert(1&#41;)", "<p>a</p>\n");
assert("[a](Javas&#99;ript:alert(1&#41;)", "<p>a</p>\n");
assert("[a](Javas%26%2399;ript:alert(1&#41;)", "<p>a</p>\n");
assert("[a](javascript:alert&#65534;(1&#41;)", "<p>a</p>\n");
assert("[a](javascript:confirm(1)", "<p>a</p>\n");
assert("[a](javascript://www.google.com%0Aprompt(1))", "<p>a</p>\n");
assert("[a](javascript://%0d%0aconfirm(1);com)", "<p>a</p>\n");
assert("[a](javascript:window.onerror=confirm;throw%201)", "<p>a</p>\n");
assert(
    "[a](javascript:alert(document.domain&#41;)",
    "<p>[a](javascript:alert(document.domain))</p>\n"
);
assert("[a](javascript://www.google.com%0Aalert(1))", "<p>a</p>\n");
assert(`[a]('javascript:alert("1")')`, "<p>a</p>\n");
assert("[a](JaVaScRiPt:alert(1))", "<p>a</p>\n");
assert(
    `![a](https://www.google.com/image.png"onload="alert(1))`,
    `<p><img alt="a" src="https://www.google.com/image.png%22onload=%22alert(1)"></p>\n`
);
assert(`![a]("onerror="alert(1))`, `<p><img alt="a" src="%22onerror=%22alert(1)"></p>\n`);
assert("</http://<?php><h1><script:script>confirm(2)", `<h1>confirm(2)</h1>`);
assert(
    "[XSS](.alert(1);)",
    `<p><a rel="noreferrer noopener" target="_blank" href=".alert(1);">XSS</a></p>\n`
);
assert(
    "[ ](https://a.de?p=[[/data-x=. style=background-color:#000000;z-index:999;width:100%;position:fixed;top:0;left:0;right:0;bottom:0; data-y=.]])",
    `<p>[ ](<a rel="noreferrer noopener" target="_blank" href="https://a.de?p=%5B%5B/data-x=">https://a.de?p=[[/data-x=</a>. style=background-color:#000000;z-index:999;width:100%;position:fixed;top:0;left:0;right:0;bottom:0; data-y=.]])</p>\n`
);
assert(
    "[ ](http://a?p=[[/onclick=alert(0) .]])",
    `<p><a rel="noreferrer noopener" target="_blank" href="http://a?p=%5B%5B/onclick=alert(0"> </a> .]])</p>\n`
);
assert("[a](javascript:new%20Function`alert`1``;)", "<p>a</p>\n");
assert("[XSS](javascript:prompt(document.cookie))", "<p>XSS</p>\n");
assert(
    "[XSS](j    a   v   a   s   c   r   i   p   t:prompt(document.cookie))",
    "<p>[XSS](j    a   v   a   s   c   r   i   p   t:prompt(document.cookie))</p>\n"
);
assert("[XSS](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)", "<p>XSS</p>\n"); // <script>alert('XSS)</script> in base64
assert(
    "[XSS](&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29)",
    "<p>XSS</p>\n"
);
assert("[XSS]: (javascript:prompt(document.cookie))", "");
assert("[XSS](javascript:window.onerror=alert;throw%20document.cookie)", "<p>XSS</p>\n");
assert("[XSS](javascript://%0d%0aprompt(1))", "<p>XSS</p>\n");
assert("[XSS](javascript://%0d%0aprompt(1);com)", "<p>XSS</p>\n");
assert("[XSS](javascript:window.onerror=alert;throw%20document.cookie)", "<p>XSS</p>\n");
assert("[XSS](javascript://%0d%0awindow.onerror=alert;throw%20document.cookie)", "<p>XSS</p>\n");
assert("[XSS](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)", "<p>XSS</p>\n"); // <script>alert('XSS)</script> in base64
assert("[XSS](vbscript:alert(document.domain))", "<p>XSS</p>\n");
assert("[XSS](javascript:this;alert(1))", "<p>XSS</p>\n");
assert("[XSS](javascript:this;alert(1&#41;)", "<p>XSS</p>\n");
assert("[XSS](javascript&#58this;alert(1&#41;)", "<p>XSS</p>\n");
assert("[XSS](Javas&#99;ript:alert(1&#41;)", "<p>XSS</p>\n");
assert("[XSS](Javas%26%2399;ript:alert(1&#41;)", "<p>XSS</p>\n");
assert("[XSS](javascript:alert&#65534;(1&#41;)", "<p>XSS</p>\n");
assert("[XSS](javascript:confirm(1)", "<p>XSS</p>\n");
assert("[XSS](javascript://www.google.com%0Aprompt(1))", "<p>XSS</p>\n");
assert("[XSS](javascript://%0d%0aconfirm(1);com)", "<p>XSS</p>\n");
assert("[XSS](javascript:window.onerror=confirm;throw%201)", "<p>XSS</p>\n");
assert("[XSS](�javascript:alert(document.domain&#41;)", "<p>XSS</p>\n");
assert("![XSS](javascript:prompt(document.cookie))\\", `<p><img alt="XSS">\\</p>\n`);
assert(
    "![XSS](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K)\\", // <script>alert('XSS)</script> in base64
    `<p><img alt="XSS" src="data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K">\\</p>\n`
);
assert(
    "![XSS'\"`onerror=prompt(document.cookie)](x)\\",
    `<p>![XSS'"\`onerror=prompt(document.cookie)](x)\\</p>\n`
);
