// @ts-check

import { after, describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, markup, xml } from "@odoo/owl";
import {
    defineParams,
    makeMockEnv,
    mountWithCleanup,
    onRpc,
    patchTranslations,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { localization } from "@web/core/l10n/localization";
import { luxon } from "@web/core/l10n/luxon";
import {
    _pl,
    _t as basic_t,
    TranslatedString,
    translatedTerms,
    translationLoaded,
} from "@web/core/translation";
import { isMarkup } from "@web/core/utils/dom/html";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { session } from "@web/session";
const { DateTime } = luxon;

/** @type {typeof basic_t} */
function _t(source, ...substitutions) {
    odoo.translationContext = "web";
    const translatedTerm = basic_t(source, ...substitutions);
    odoo.translationContext = null;
    return translatedTerm;
}

let id = 0;

const frenchTerms = { Hello: "Bonjour" };
class TestComponent extends Component {
    static get template() {
        return xml`${this._template}<div id="${id++}"/>`;
    }
    static _template = "";
    /** @type {ReturnType<typeof basic_t>} */
    static someLazyText;
    static props = ["*"];
}

/**
 * @param {string} lang
 * @returns {Promise<void>}
 */
async function mockLang(lang) {
    serverState.lang = lang;
    await makeMockEnv();
}

test.tags("headless");
test("lang is given by the user context", async () => {
    onRpc("/web/webclient/translations", (request) => {
        const urlParams = new URLSearchParams(new URL(request.url).search);
        expect.step(urlParams.get("lang"));
    });
    await mockLang("fr_FR");
    expect.verifySteps(["fr_FR"]);
});

test.tags("headless");
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

test.tags("headless");
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
        async read() {
            return undefined;
        },
        async write(table, key, value) {
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
        async read() {
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
    expect("#main").toHaveText("Bonjour");
    def.resolve();
    await animationFrame();
    expect.verifySteps(["hash: 30b70a0e"]);
});

test.tags("headless");
test("[preload] adopt the parse-time preloaded fetch on cold boot", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        async read() {
            return undefined;
        },
        async write() {},
    });
    onRpc("/web/webclient/translations", () => {
        expect.step("unexpected service fetch");
    });
    const preloadedResult = {
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
            web: { messages: [{ id: "Hello", string: "Bonjour (preloaded)" }] },
        },
        multi_lang: false,
        hash: "preload123",
    };
    /** @type {any} */ (odoo).loadTranslationsURL =
        "/web/webclient/translations?hash=&lang=en";
    /** @type {any} */ (odoo).loadTranslationsPromise = Promise.resolve(
        new Response(JSON.stringify(preloadedResult)),
    );
    await makeMockEnv();
    expect(/** @type {any} */ (odoo).loadTranslationsPromise).toBe(null);
    expect(/** @type {any} */ (odoo).loadTranslationsURL).toBe(null);
    expect(_t("Hello")).toBe("Bonjour (preloaded)");
    expect.verifySteps([]);
});

test.tags("headless");
test("[preload] discard the preload and revalidate by hash when the cache hits", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        async read() {
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
        async write() {},
    });
    onRpc("/web/webclient/translations", (request) => {
        expect.step(`hash: ${new URL(request.url).searchParams.get("hash")}`);
    });
    /** @type {any} */ (odoo).loadTranslationsURL =
        "/web/webclient/translations?hash=&lang=en";
    /** @type {any} */ (odoo).loadTranslationsPromise = Promise.resolve(
        new Response(JSON.stringify({})),
    );
    await makeMockEnv();
    expect(/** @type {any} */ (odoo).loadTranslationsPromise).toBe(null);
    expect.verifySteps(["hash: 30b70a0e"]);
});

test.tags("headless");
test("[preload] localStorage marker mirrors the IndexedDB cache state", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        async read() {
            return undefined;
        },
        async write() {},
    });
    defineParams({
        translations: frenchTerms,
    });
    await makeMockEnv();
    expect(browser.localStorage.getItem("webclient_translations_version")).toBe(
        `${session.registry_hash}/en`,
    );
});

test.tags("headless");
test("[cold boot] fetch failure falls back to usable localization defaults", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        async read() {
            return undefined;
        },
        async write() {
            expect.step("unexpected cache write");
        },
    });
    patchWithCleanup(console, {
        error: () => expect.step("console.error"),
    });
    onRpc("/web/webclient/translations", () => {
        expect.step("translations fetch");
        throw new Error("Connection refused");
    });
    await makeMockEnv();
    expect.verifySteps(["translations fetch", "console.error"]);
    expect(localization.dateFormat).toBe("MM/dd/yyyy");
    expect(localization.timeFormat).toBe("HH:mm:ss");
    expect(localization.dateTimeFormat).toBe("MM/dd/yyyy HH:mm:ss");
    expect(localization.decimalPoint).toBe(".");
    expect(localization.thousandsSep).toBe(",");
    expect(localization.grouping).toEqual([3, 0]);
    expect(localization.direction).toBe("ltr");
    expect(localization.weekStart).toBe(7);
    expect(translatedTerms[translationLoaded]).toBe(true);
    expect(_t("Hello")).toBe("Hello");
});

test("[cache] update the cache if hash are different - template", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        async read() {
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
                    web: { messages: [{ id: "Hello", string: "Different Bonjour" }] },
                },
                multi_lang: false,
                hash: "30b",
            };
        },
        async write(table, key, value) {
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
    expect("#main").toHaveText("Different Bonjour");
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
        modules: { web: { messages: [{ id: "Hello", string: "Bonjour" }] } },
        multi_lang: false,
        hash: "ab5379cf",
    };
    expect.verifySteps([
        "hash: 30b",
        "table: /web/webclient/translations",
        'key: {"lang":"en"}',
        `value: ${JSON.stringify(expectedValue)}`,
    ]);

    component.render();
    await animationFrame();
    expect("#main").toHaveText("Different Bonjour");
});

test("[cache] update the cache if hash are different - js", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        async read() {
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
        async write(table, key, value) {
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
        static template = xml`<div id="main" t-translation-context="web"><t t-out="otherText"/></div>`;
        static props = ["*"];

        get otherText() {
            return _t("Hi");
        }
    }

    defineParams({
        translations: { Hi: "Salut" },
    });
    const component = await mountWithCleanup(MyTestComponent);
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
        },
        multi_lang: false,
        hash: "5a528fc2",
    };
    expect.verifySteps([
        "hash: 30b",
        "table: /web/webclient/translations",
        'key: {"lang":"en"}',
        `value: ${JSON.stringify(expectedValue)}`,
    ]);

    component.render();
    await animationFrame();
    expect("#main").toHaveText("Salut");
});

test("can lazy translate", async () => {
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

test("a blank or non-string source is returned as a string before translations load", () => {
    translatedTerms[translationLoaded] = false;
    expect(basic_t("")).toBe("");
    expect(basic_t("  ")).toBe("  ");
    expect(basic_t(markup("<p>help</p>"))).toBe("<p>help</p>");
});

test.tags("headless");
test("luxon is configured in the correct lang", async () => {
    await mockLang("fr_BE");
    expect(DateTime.utc(2021, 12, 10).toFormat("MMMM")).toBe("décembre");
});

test.tags("headless");
test("arabic has the correct numbering system (generic)", async () => {
    await mockLang("ar_001");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "١٠/١٢/٢٠٢١ ١٢:٠٠:٠٠",
    );
});

test.tags("headless");
test("arabic has the correct numbering system (Algeria)", async () => {
    await mockLang("ar_DZ");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "10/12/2021 12:00:00",
    );
});

test.tags("headless");
test("arabic has the correct numbering system (Lybia)", async () => {
    await mockLang("ar_LY");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "10/12/2021 12:00:00",
    );
});

test.tags("headless");
test("arabic has the correct numbering system (Morocco)", async () => {
    await mockLang("ar_MA");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "10/12/2021 12:00:00",
    );
});

test.tags("headless");
test("arabic has the correct numbering system (Saudi Arabia)", async () => {
    await mockLang("ar_SA");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "١٠/١٢/٢٠٢١ ١٢:٠٠:٠٠",
    );
});

test.tags("headless");
test("arabic has the correct numbering system (Tunisia)", async () => {
    await mockLang("ar_TN");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "10/12/2021 12:00:00",
    );
});

test.tags("headless");
test("bengalese has the correct numbering system", async () => {
    await mockLang("bn");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "১০/১২/২০২১ ১২:০০:০০",
    );
});

test.tags("headless");
test("punjabi (gurmukhi) has the correct numbering system", async () => {
    await mockLang("pa_IN");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "੧੦/੧੨/੨੦੨੧ ੧੨:੦੦:੦੦",
    );
});

test.tags("headless");
test("tamil has the correct numbering system", async () => {
    await mockLang("ta");
    expect(DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss")).toBe(
        "௧௦/௧௨/௨௦௨௧ ௧௨:௦௦:௦௦",
    );
});

test.tags("headless");
test("_t fills the format specifiers in translated terms with its extra arguments", async () => {
    patchTranslations({
        web: {
            "Due in %s days": "Échéance dans %s jours",
        },
    });
    const translatedStr = _t("Due in %s days", 513);
    expect(translatedStr).toBe("Échéance dans 513 jours");
});

test.tags("headless");
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

test.tags("headless");
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

describe.tags("headless");
describe("_t with markups", () => {
    test("non-markup values are escaped", () => {
        translatedTerms[translationLoaded] = true;
        const maliciousUserInput =
            "<script>alert('This should've been escaped')</script>";
        const translatedStr = _t(
            "FREE %(blink_start)sROBUX%(blink_end)s, please contact %(email)s",
            {
                blink_start: markup`<blink>`,
                blink_end: markup`</blink>`,
                email: maliciousUserInput,
            },
        );
        expect(translatedStr).toBeInstanceOf(markup("").constructor);
        expect(translatedStr.valueOf()).toBe(
            "FREE <blink>ROBUX</blink>, please contact &lt;script&gt;alert(&#x27;This should&#x27;ve been escaped&#x27;)&lt;/script&gt;",
        );
    });
    test("translations are escaped", () => {
        translatedTerms[translationLoaded] = true;
        const maliciousTranslation =
            "<script>document.write('pizza hawai')</script> %s";
        patchTranslations({
            web: {
                "I love %s": maliciousTranslation,
            },
        });
        const translatedStr = _t("I love %s", markup`<blink>Mario Kart</blink>`);
        expect(translatedStr.valueOf()).toBe(
            "&lt;script&gt;document.write(&#x27;pizza hawai&#x27;)&lt;/script&gt; <blink>Mario Kart</blink>",
        );
    });
});

describe("_pl", () => {
    test("selects the plural category for the active locale", () => {
        patchWithCleanup(localization, { code: "en_US" });
        expect(_pl(1, { one: "1 record", other: "records" })).toBe("1 record");
        expect(_pl(3, { one: "1 record", other: "records" })).toBe("records");
    });

    test("does not throw for an XPG @modifier locale (sr@latin)", () => {
        patchWithCleanup(localization, { code: "sr@latin" });
        expect(() => _pl(2, { one: "a", few: "b", other: "c" })).not.toThrow();
        expect(_pl(1, { one: "a", few: "b", other: "c" })).toBe("a");
        expect(_pl(2, { one: "a", few: "b", other: "c" })).toBe("b");
    });

    test("falls back to `other` when the matched category form is absent", () => {
        patchWithCleanup(localization, { code: "en_US" });
        expect(_pl(5, { other: "fallback" })).toBe("fallback");
    });
});

describe("TranslatedString primitive conversion", () => {
    test("a markup substitution still converts to a primitive", () => {
        const ts = new TranslatedString("Hello %s", [markup`<b>x</b>`], "base");
        ts.lazy = false;
        expect(isMarkup(ts.translate())).toBe(true);
        expect(typeof ts.valueOf()).toBe("string");
        expect(typeof ts.toString()).toBe("string");
        expect(String(ts)).toBe("Hello <b>x</b>");
        expect(`${ts}`).toBe("Hello <b>x</b>");
        expect(ts + "").toBe("Hello <b>x</b>");
    });

    test("a plain substitution is unaffected", () => {
        const ts = new TranslatedString("Hello %s", ["world"], "base");
        ts.lazy = false;
        expect(isMarkup(ts.translate())).toBe(false);
        expect(ts.valueOf()).toBe("Hello world");
    });

    test("_t keeps returning Markup once translations are loaded", () => {
        const eager = basic_t("Could not save file %s", markup`<strong>a&b</strong>`);
        expect(isMarkup(eager)).toBe(true);
        expect(String(eager)).toBe("Could not save file <strong>a&b</strong>");
    });

    test("_t with a plain substitution stays a plain string", () => {
        const eager = basic_t("Could not save file %s", "a&b");
        expect(isMarkup(eager)).toBe(false);
        expect(String(eager)).toBe("Could not save file a&b");
    });
});
