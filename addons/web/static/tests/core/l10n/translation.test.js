/* eslint no-restricted-syntax: 0 */
import { after, describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    defineParams,
    makeMockEnv,
    mountWithCleanup,
    onRpc,
    patchTranslations,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { _t as basic_t, translatedTerms, translationLoaded } from "@web/core/l10n/translation";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { session } from "@web/session";

import { Component, markup, xml } from "@odoo/owl";
const { DateTime } = luxon;

function _t() {
    odoo.translationContext = "web";
    const translatedTerm = basic_t(...arguments);
    odoo.translationContext = null;
    return translatedTerm;
}

let id = 0;

const frenchTerms = { Hello: "Bonjour" };
class TestComponent extends Component {
    // For performance reasons, HOOT caches the compiled templates
    // (with the terms already translated).
    // In this test suite, since the translations are being tested,
    // we need that each template to be unique (to avoid using a cached template).
    // To do this, we create a unique empty node in each template.
    static get template() {
        return xml`${this._template}<div id="${id++}"/>`;
    }
    static _template = "";
    static props = ["*"];
}

/**
 * Patches the 'lang' of the user session and context.
 *
 * @param {string} lang
 * @returns {Promise<void>}
 */
async function mockLang(lang) {
    serverState.lang = lang;
    await makeMockEnv();
}

test("lang is given by the user context", async () => {
    onRpc("/web/webclient/translations", (request) => {
        const urlParams = new URLSearchParams(new URL(request.url).search);
        expect.step(urlParams.get("lang"));
    });
    await mockLang("fr_FR");
    expect.verifySteps(["fr_FR"]);
});

test("lang is given by an attribute on the DOM root node", async () => {
    serverState.lang = null;
    onRpc("/web/webclient/translations", (request) => {
        const urlParams = new URLSearchParams(new URL(request.url).search);
        expect.step(urlParams.get("lang"));
    });
    document.documentElement.setAttribute("lang", "fr-FR");
    after(() => {
        document.documentElement.removeAttribute("lang");
    });
    await makeMockEnv();
    expect.verifySteps(["fr_FR"]);
});

test("url is given by the session", async () => {
    patchWithCleanup(session, {
        translationURL: "/get_translations",
    });
    onRpc("/get_translations", function (request) {
        expect.step("/get_translations");
        return this.loadTranslations(request);
    });
    await makeMockEnv();
    expect.verifySteps(["/get_translations"]);
});

test("can translate a text node", async () => {
    TestComponent._template = `<div id="main" t-translation-context="web">Hello</div>`;
    defineParams({
        translations: frenchTerms,
    });
    await mountWithCleanup(TestComponent);
    expect("#main").toHaveText("Bonjour");
});

test("[cache] write into the cache", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        write(table, key, value) {
            expect.step(`table: ${table}`);
            expect.step(`key: ${key}`);
            expect.step(`value: ${JSON.stringify(value)}`);
        },
    });
    onRpc("/web/webclient/translations", (request) => {
        expect.step(`hash: ${new URL(request.url).searchParams.get("hash")}`);
    });
    TestComponent._template = `<div id="main" t-translation-context="web">Hello</div>`;
    defineParams({
        translations: frenchTerms,
    });
    await mountWithCleanup(TestComponent);
    expect("#main").toHaveText("Bonjour");
    const expectedValue = {
        lang: "en",
        lang_parameters: {
            date_format: "%m/%d/%Y",
            decimal_point: ".",
            direction: "ltr",
            grouping: "[3,0]",
            time_format: "%H:%M:%S",
            thousands_sep: ",",
            week_start: 7,
        },
        modules: { web: { messages: [{ id: "Hello", string: "Bonjour" }] } },
        multi_lang: false,
        hash: "ab5379cf",
    };
    expect.verifySteps([
        "hash: ",
        "table: /web/webclient/translations",
        'key: {"lang":"en"}',
        `value: ${JSON.stringify(expectedValue)}`,
    ]);
});

test("[cache] read from cache, and don't wait to render", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        read() {
            return {
                lang: "en",
                lang_parameters: {
                    date_format: "%m/%d/%Y",
                    decimal_point: ".",
                    direction: "ltr",
                    grouping: "[3,0]",
                    time_format: "%H:%M:%S",
                    thousands_sep: ",",
                    week_start: 7,
                },
                modules: { web: { messages: [{ id: "Hello", string: "Bonjour" }] } },
                multi_lang: false,
                hash: "30b70a0e",
            };
        },
    });
    const def = new Deferred();
    onRpc("/web/webclient/translations", async (request) => {
        await def;
        expect.step(`hash: ${new URL(request.url).searchParams.get("hash")}`);
    });
    TestComponent._template = `<div id="main" t-translation-context="web">Hello</div>`;
    defineParams({
        translations: frenchTerms,
    });
    await mountWithCleanup(TestComponent);
    expect("#main").toHaveText("Bonjour"); //Don't wait the end of the fetch to render
    def.resolve();
    await animationFrame();
    expect.verifySteps(["hash: 30b70a0e"]); //Fetch with the hash of the translation in cache
});

test("[cache] update the cache if hash are different - template", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        read() {
            return {
                lang: "en",
                lang_parameters: {
                    date_format: "%m/%d/%Y",
                    decimal_point: ".",
                    direction: "ltr",
                    grouping: "[3,0]",
                    time_format: "%H:%M:%S",
                    thousands_sep: ",",
                    week_start: 7,
                },
                modules: { web: { messages: [{ id: "Hello", string: "Different Bonjour" }] } },
                multi_lang: false,
                hash: "30b",
            };
        },
        write(table, key, value) {
            expect.step(`table: ${table}`);
            expect.step(`key: ${key}`);
            expect.step(`value: ${JSON.stringify(value)}`);
        },
    });
    const def = new Deferred();
    onRpc("/web/webclient/translations", async (request) => {
        await def;
        expect.step(`hash: ${new URL(request.url).searchParams.get("hash")}`);
    });
    TestComponent._template = `<div id="main" t-translation-context="web">Hello</div>`;
    defineParams({
        translations: frenchTerms,
    });
    const component = await mountWithCleanup(TestComponent);
    expect("#main").toHaveText("Different Bonjour"); //Value came from the cache!
    def.resolve();
    await animationFrame();
    const expectedValue = {
        lang: "en",
        lang_parameters: {
            date_format: "%m/%d/%Y",
            decimal_point: ".",
            direction: "ltr",
            grouping: "[3,0]",
            time_format: "%H:%M:%S",
            thousands_sep: ",",
            week_start: 7,
        },
        modules: { web: { messages: [{ id: "Hello", string: "Bonjour" }] } }, // value was updated in the cache
        multi_lang: false,
        hash: "ab5379cf", // hash was updated in the cache
    };
    expect.verifySteps([
        "hash: 30b", //Fetch with the hash of the translation in cache
        "table: /web/webclient/translations",
        'key: {"lang":"en"}',
        `value: ${JSON.stringify(expectedValue)}`,
    ]);

    component.render();
    await animationFrame();
    // The value hasn't been updated with the new translation, this is because owl caches the translated templates for performance reasons.
    // This is a known limitation.
    expect("#main").toHaveText("Different Bonjour");
});

test("[cache] update the cache if hash are different - js", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        read() {
            return {
                lang: "en",
                lang_parameters: {
                    date_format: "%m/%d/%Y",
                    decimal_point: ".",
                    direction: "ltr",
                    grouping: "[3,0]",
                    time_format: "%H:%M:%S",
                    thousands_sep: ",",
                    week_start: 7,
                },
                modules: {
                    web: {
                        messages: [{ id: "Hi", string: "Different Salut" }],
                    },
                },
                multi_lang: false,
                hash: "30b",
            };
        },
        write(table, key, value) {
            expect.step(`table: ${table}`);
            expect.step(`key: ${key}`);
            expect.step(`value: ${JSON.stringify(value)}`);
        },
    });
    const def = new Deferred();
    onRpc("/web/webclient/translations", async (request) => {
        await def;
        expect.step(`hash: ${new URL(request.url).searchParams.get("hash")}`);
    });
    class MyTestComponent extends Component {
        static template = xml`<div id="main" t-translation-context="web"><t t-esc="otherText"/></div>`;
        static props = ["*"];

        get otherText() {
            return _t("Hi");
        }
    }

    defineParams({
        translations: { Hi: "Salut" },
    });
    const component = await mountWithCleanup(MyTestComponent);
    // The cached translated terms are used
    expect("#main").toHaveText("Different Salut");

    def.resolve();
    await animationFrame();
    const expectedValue = {
        lang: "en",
        lang_parameters: {
            date_format: "%m/%d/%Y",
            decimal_point: ".",
            direction: "ltr",
            grouping: "[3,0]",
            time_format: "%H:%M:%S",
            thousands_sep: ",",
            week_start: 7,
        },
        modules: {
            web: {
                messages: [{ id: "Hi", string: "Salut" }],
            },
        }, // value was updated in the cache
        multi_lang: false,
        hash: "5a528fc2", // hash was updated in the cache
    };
    expect.verifySteps([
        "hash: 30b", //Fetch with the hash of the translation in cache
        "table: /web/webclient/translations",
        'key: {"lang":"en"}',
        `value: ${JSON.stringify(expectedValue)}`,
    ]);

    component.render();
    await animationFrame();
    // Using the updated translated terms
    expect("#main").toHaveText("Salut");
});

test("can lazy translate", async () => {
    // Can't use patchWithCleanup cause it doesn't support Symbol
    translatedTerms[translationLoaded] = false;
    TestComponent._template = `<div id="main" t-translation-context="web"><t t-esc="constructor.someLazyText" /></div>`;
    TestComponent.someLazyText = _t("Hello");
    expect(() => TestComponent.someLazyText.toString()).toThrow();
    expect(() => TestComponent.someLazyText.valueOf()).toThrow();
    defineParams({
        translations: frenchTerms,
    });
    await mountWithCleanup(TestComponent);
    expect("#main").toHaveText("Bonjour");
});

test("luxon is configured in the correct lang", async () => {
    await mockLang("fr_BE");
    expect(DateTime.utc(2021, 12, 10).toFormat("MMMM")).toBe("décembre");
});

test("arabic has the correct numbering system (generic)", async () => {
    await mockLang("ar_001");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("١٠/١٢/٢٠٢١ ١٢:٠٠:٠٠");
});

test("arabic has the correct numbering system (Algeria)", async () => {
    await mockLang("ar_DZ");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("10/12/2021 12:00:00");
});

test("arabic has the correct numbering system (Lybia)", async () => {
    await mockLang("ar_LY");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("10/12/2021 12:00:00");
});

test("arabic has the correct numbering system (Morocco)", async () => {
    await mockLang("ar_MA");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("10/12/2021 12:00:00");
});

test("arabic has the correct numbering system (Saudi Arabia)", async () => {
    await mockLang("ar_SA");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("١٠/١٢/٢٠٢١ ١٢:٠٠:٠٠");
});

test("arabic has the correct numbering system (Tunisia)", async () => {
    await mockLang("ar_TN");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("10/12/2021 12:00:00");
});

test("bengalese has the correct numbering system", async () => {
    await mockLang("bn");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("১০/১২/২০২১ ১২:০০:০০");
});

test("punjabi (gurmukhi) has the correct numbering system", async () => {
    await mockLang("pa_IN");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("੧੦/੧੨/੨੦੨੧ ੧੨:੦੦:੦੦");
});

test("tamil has the correct numbering system", async () => {
    await mockLang("ta");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe("௧௦/௧௨/௨௦௨௧ ௧௨:௦௦:௦௦");
});

test("_t fills the format specifiers in translated terms with its extra arguments", async () => {
    patchTranslations({
        web: {
            "Due in %s days": "Échéance dans %s jours",
        },
    });
    const translatedStr = _t("Due in %s days", 513);
    expect(translatedStr).toBe("Échéance dans 513 jours");
});

test("_t fills the format specifiers in translated terms with formatted lists", async () => {
    await mockLang("fr_FR");
    patchTranslations({
        web: {
            "Due in %s days": "Échéance dans %s jours",
            "Due in %(due_dates)s days for %(user)s":
                "Échéance dans %(due_dates)s jours pour %(user)s",
        },
    });
    const translatedStr1 = _t("Due in %s days", ["30", "60", "90"]);
    const translatedStr2 = _t("Due in %(due_dates)s days for %(user)s", {
        due_dates: ["30", "60", "90"],
        user: "Mitchell",
    });
    expect(translatedStr1).toBe("Échéance dans 30, 60 et 90 jours");
    expect(translatedStr2).toBe("Échéance dans 30, 60 et 90 jours pour Mitchell");
});

test("_t fills the format specifiers in lazy translated terms with its extra arguments", async () => {
    translatedTerms[translationLoaded] = false;
    const translatedStr = _t("Due in %s days", 513);
    patchTranslations({
        web: {
            "Due in %s days": "Échéance dans %s jours",
        },
    });
    expect(translatedStr.toString()).toBe("Échéance dans 513 jours");
});

describe("_t with markups", () => {
    test("non-markup values are escaped", () => {
        translatedTerms[translationLoaded] = true;
        const maliciousUserInput = "<script>alert('This should've been escaped')</script>";
        const translatedStr = _t(
            "FREE %(blink_start)sROBUX%(blink_end)s, please contact %(email)s",
            {
                blink_start: markup`<blink>`,
                blink_end: markup`</blink>`,
                email: maliciousUserInput,
            }
        );
        expect(translatedStr).toBeInstanceOf(markup().constructor);
        expect(translatedStr.valueOf()).toBe(
            "FREE <blink>ROBUX</blink>, please contact &lt;script&gt;alert(&#x27;This should&#x27;ve been escaped&#x27;)&lt;/script&gt;"
        );
    });
    test("translations are escaped", () => {
        translatedTerms[translationLoaded] = true;
        const maliciousTranslation = "<script>document.write('pizza hawai')</script> %s";
        patchTranslations({
            web: {
                "I love %s": maliciousTranslation,
            },
        });
        const translatedStr = _t("I love %s", markup`<blink>Mario Kart</blink>`);
        expect(translatedStr.valueOf()).toBe(
            "&lt;script&gt;document.write(&#x27;pizza hawai&#x27;)&lt;/script&gt; <blink>Mario Kart</blink>"
        );
    });
});
