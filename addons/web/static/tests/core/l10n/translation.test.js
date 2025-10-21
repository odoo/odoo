import { after, describe, expect, test } from "@odoo/hoot";
import {
    defineParams,
    makeMockEnv,
    mountWithCleanup,
    onRpc,
    patchTranslations,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { _t, translatedTerms, translationLoaded } from "@web/core/l10n/translation";
import { session } from "@web/session";

import { Component, markup, xml } from "@odoo/owl";
const { DateTime } = luxon;

const frenchTerms = { Hello: "Bonjour" };
class TestComponent extends Component {
    static template = "";
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
    onRpc("/web/webclient/translations/*", (request) => {
        const urlParams = new URLSearchParams(new URL(request.url).search);
        expect.step(urlParams.get("lang"));
    });
    await mockLang("fr_FR");
    expect.verifySteps(["fr_FR"]);
});

test("lang is given by an attribute on the DOM root node", async () => {
    serverState.lang = null;
    onRpc("/web/webclient/translations/*", (request) => {
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
    expect.assertions(1);
    patchWithCleanup(session, {
        translationURL: "/get_translations",
    });
    onRpc("/get_translations/*", function (request) {
        expect(request.url).toInclude("/get_translations/");
        return this.loadTranslations();
    });
    await makeMockEnv();
});

test("can translate a text node", async () => {
    TestComponent.template = xml`<div id="main">Hello</div>`;
    defineParams({
        translations: frenchTerms,
    });
    await mountWithCleanup(TestComponent);
    expect("#main").toHaveText("Bonjour");
});

test("can lazy translate", async () => {
    // Can't use patchWithCleanup cause it doesn't support Symbol
    translatedTerms[translationLoaded] = false;
    TestComponent.template = xml`<div id="main"><t t-esc="constructor.someLazyText" /></div>`;
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
        "Due in %s days": "Échéance dans %s jours",
    });
    const translatedStr = _t("Due in %s days", 513);
    expect(translatedStr).toBe("Échéance dans 513 jours");
});

test("_t fills the format specifiers in lazy translated terms with its extra arguments", async () => {
    translatedTerms[translationLoaded] = false;
    const translatedStr = _t("Due in %s days", 513);
    patchTranslations({
        "Due in %s days": "Échéance dans %s jours",
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
                blink_start: markup("<blink>"),
                blink_end: markup("</blink>"),
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
        patchTranslations({ "I love %s": maliciousTranslation });
        const translatedStr = _t("I love %s", markup("<blink>Mario Kart</blink>"));
        expect(translatedStr.valueOf()).toBe(
            "&lt;script&gt;document.write(&#x27;pizza hawai&#x27;)&lt;/script&gt; <blink>Mario Kart</blink>"
        );
    });
});
