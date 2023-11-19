import { expect, test } from "@odoo/hoot";
import { URL_REGEX } from "@html_editor/utils/regex";

function testUrlRegex(content, { expectedUrl, insideText } = {}) {
    const message = expectedUrl
        ? `should have the text be "${content}" with one link ${expectedUrl}`
        : `should be a link: ${content}`;
    test(message, () => {
        if (insideText) {
            expectedUrl = expectedUrl || content;
            content = `abc ${content} abc`;
        }
        if (expectedUrl) {
            const match = content.match(URL_REGEX);
            expect(expectedUrl).toBe(match && match[0]);
        } else {
            expect(content).toMatch(URL_REGEX);
        }
    });
}

function testNotUrlRegex(content, { insideText } = {}) {
    test(`should NOT be/content a link: ${content}`, () => {
        if (insideText) {
            content = `abc ${content} abc`;
        }
        expect(content).not.toMatch(URL_REGEX);
    });
}

testUrlRegex("google.com");
testUrlRegex("a google.com b", { expectedUrl: "google.com" });

// Url separator
testUrlRegex("google.com/", { expectedUrl: "google.com/" });
testUrlRegex("google.com?", { expectedUrl: "google.com?" });
testUrlRegex("google.com#", { expectedUrl: "google.com#" });

testUrlRegex("google.com!", { expectedUrl: "google.com" });
testUrlRegex("google.com)", { expectedUrl: "google.com" });
testUrlRegex("google.com(", { expectedUrl: "google.com" });
testUrlRegex("google.com/ a", { expectedUrl: "google.com/" });
testUrlRegex("google.com. a", { expectedUrl: "google.com" });
testUrlRegex("google.com, a", { expectedUrl: "google.com" });

// Some special characters should not be included if at the end.
testUrlRegex("google.com/.", { expectedUrl: "google.com/" });
testUrlRegex("google.com/,", { expectedUrl: "google.com/" });
testUrlRegex("google.com/)", { expectedUrl: "google.com/" });
testUrlRegex("google.com/]", { expectedUrl: "google.com/" });
testUrlRegex("google.com/}", { expectedUrl: "google.com/" });
testUrlRegex("google.com/'", { expectedUrl: "google.com/" });
testUrlRegex('google.com/"', { expectedUrl: "google.com/" });
testUrlRegex("google.com#.", { expectedUrl: "google.com#" });
testUrlRegex("google.com#,", { expectedUrl: "google.com#" });
testUrlRegex("google.com#)", { expectedUrl: "google.com#" });
testUrlRegex("google.com#]", { expectedUrl: "google.com#" });
testUrlRegex("google.com#}", { expectedUrl: "google.com#" });
testUrlRegex("google.com#'", { expectedUrl: "google.com#" });
testUrlRegex('google.com#"', { expectedUrl: "google.com#" });
testUrlRegex("google.com?,", { expectedUrl: "google.com?" });
testUrlRegex("google.com?.", { expectedUrl: "google.com?" });
testUrlRegex("google.com?)", { expectedUrl: "google.com?" });
testUrlRegex("google.com?]", { expectedUrl: "google.com?" });
testUrlRegex("google.com?}", { expectedUrl: "google.com?" });
testUrlRegex("google.com?'", { expectedUrl: "google.com?" });
testUrlRegex('google.com?"', { expectedUrl: "google.com?" });

// The previous special character should be included when they are nt at the end.
testUrlRegex("google.com/.a", { expectedUrl: "google.com/.a" });
testUrlRegex("google.com/,a", { expectedUrl: "google.com/,a" });
testUrlRegex("google.com/)a", { expectedUrl: "google.com/)a" });
testUrlRegex("google.com/]a", { expectedUrl: "google.com/]a" });
testUrlRegex("google.com/}a", { expectedUrl: "google.com/}a" });
testUrlRegex("google.com/'a", { expectedUrl: "google.com/'a" });
testUrlRegex('google.com/"a', { expectedUrl: 'google.com/"a' });

// Other special character can be included at the end.
testUrlRegex("google.com/(", { expectedUrl: "google.com/(" });
testUrlRegex("google.com/[", { expectedUrl: "google.com/[" });
testUrlRegex("google.com/{", { expectedUrl: "google.com/{" });
testUrlRegex("google.com?(", { expectedUrl: "google.com?(" });
testUrlRegex("google.com?[", { expectedUrl: "google.com?[" });
testUrlRegex("google.com?{", { expectedUrl: "google.com?{" });
testUrlRegex("google.com#(", { expectedUrl: "google.com#(" });
testUrlRegex("google.com#[", { expectedUrl: "google.com#[" });
testUrlRegex("google.com#{", { expectedUrl: "google.com#{" });

testUrlRegex("google.co.uk");
testUrlRegex("google123.com");
testUrlRegex("http://google.com");
testUrlRegex("http://google123.com");
testUrlRegex("https://google.com");
testUrlRegex("https://google123.com");
testUrlRegex("https://www.google.com");
testUrlRegex("https://google.shop");
testNotUrlRegex("google.shop");
testUrlRegex("google.com/");
testUrlRegex("google.com/path/123/abc/4");
testUrlRegex("http://google.com/");
testUrlRegex("http://google.com/home");
testUrlRegex("http://google.com/home/");
testUrlRegex("https://google.com/");
testUrlRegex("https://google.co.uk/");
testUrlRegex("https://www.google.com/");
testNotUrlRegex("google.shop/");
testUrlRegex("http://google.com/foo#test");
testUrlRegex("http://google.com/#test");
testNotUrlRegex("a.bcd.ef");
testUrlRegex("a.bc.de");
testNotUrlRegex("a.bc.d");
testNotUrlRegex("a.b.bc");
testNotUrlRegex("20.08.2022");
testNotUrlRegex("31.12");

// Url data and anchors count as part of the url.
testUrlRegex("google.com?data=hello", { expectedUrl: "google.com?data=hello" });
testUrlRegex("google.com/?data=hello", { expectedUrl: "google.com/?data=hello" });
testUrlRegex("google.com/foo/?data=hello", { expectedUrl: "google.com/foo/?data=hello" });
testUrlRegex("google.com/foo/?data1=hello1&data2=hello2", {
    expectedUrl: "google.com/foo/?data1=hello1&data2=hello2",
});
testUrlRegex("google.com/.?data=hello", { expectedUrl: "google.com/.?data=hello" });
testUrlRegex("google.com?data=hello#anchor", { expectedUrl: "google.com?data=hello#anchor" });
testUrlRegex("google.com/?data=hello#anchor", { expectedUrl: "google.com/?data=hello#anchor" });
testUrlRegex("google.com/.?data=hello#anchor", { expectedUrl: "google.com/.?data=hello#anchor" });
testUrlRegex("google.com/foo/?data=hello&data2=foo#anchor", {
    expectedUrl: "google.com/foo/?data=hello&data2=foo#anchor",
});

// Url containing some special characters
testUrlRegex("www.google.com/path/1-2-3", { expectedUrl: "www.google.com/path/1-2-3" });
testUrlRegex("https://google.com/abc..def", { expectedUrl: "https://google.com/abc..def" });
testUrlRegex("https://google.com/a/b+c@d", { expectedUrl: "https://google.com/a/b+c@d" });
testUrlRegex("sub.example-website.com", { expectedUrl: "sub.example-website.com" });
testUrlRegex("http://sub.example-website.com", { expectedUrl: "http://sub.example-website.com" });
testUrlRegex("http://user:password@example.com", {
    expectedUrl: "http://user:password@example.com",
});
testUrlRegex("http://google.com/a_b", { expectedUrl: "http://google.com/a_b" });
testUrlRegex("https://google.com?query=ab.cd", { expectedUrl: "https://google.com?query=ab.cd" });
testUrlRegex(`google.com/'ab'/cd`, { expectedUrl: "google.com/'ab'/cd" });
testUrlRegex(`www.google.com/a!b/c?d,e,f#g!i`, { expectedUrl: "www.google.com/a!b/c?d,e,f#g!i" });
testUrlRegex(`www.google.com/a%b%c`, { expectedUrl: "www.google.com/a%b%c" });
testUrlRegex(`http://google.com?a.b.c&d!e#e'f`, { expectedUrl: "http://google.com?a.b.c&d!e#e'f" });

// URL inside text
testUrlRegex("foo.com", { insideText: true });
testNotUrlRegex("foo.else", { insideText: true });
testUrlRegex("www.abc.abc", { insideText: true });
testUrlRegex("abc.abc.com", { insideText: true });
testNotUrlRegex("abc.abc.abc", { insideText: true });
testUrlRegex("http://abc.abc.abc", { insideText: true });
testUrlRegex("https://abc.abc.abc", { insideText: true });
testUrlRegex("1234-abc.runbot007.odoo.com/web#id=3&menu_id=221", { insideText: true });
testUrlRegex("https://1234-abc.runbot007.odoo.com/web#id=3&menu_id=221", { insideText: true });
