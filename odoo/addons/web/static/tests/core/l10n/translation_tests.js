/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { localizationService } from "@web/core/l10n/localization_service";
import { translatedTerms, translationLoaded, _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

import { Component, xml } from "@odoo/owl";
const { DateTime, Settings } = luxon;

const terms = { Hello: "Bonjour" };
const serviceRegistry = registry.category("services");
class TestComponent extends Component {}

function patchFetch() {
    patchWithCleanup(browser, {
        fetch: async () => ({
            ok: true,
            json: async () => ({
                modules: {},
                lang_parameters: {
                    direction: "ltr",
                    date_format: "%d/%m/%Y",
                    time_format: "%H:%M:%S",
                    grouping: "[3,0]",
                    decimal_point: ",",
                    thousands_sep: ".",
                    week_start: 1,
                },
            }),
        }),
    });
}

/**
 * Patches the 'lang' of the user session and context.
 *
 * @param {string} lang
 * @returns {Promise<void>}
 */
async function patchLang(lang) {
    const { defaultLocale, defaultNumberingSystem } = Settings;
    registerCleanup(() => {
        Settings.defaultLocale = defaultLocale;
        Settings.defaultNumberingSystem = defaultNumberingSystem;
    });
    patchWithCleanup(session.user_context, { lang });
    patchFetch();
    serviceRegistry.add("localization", localizationService);
    await makeTestEnv();
}

QUnit.module("Translations");

QUnit.test("lang is given by the user context", async (assert) => {
    patchWithCleanup(session.user_context, { lang: "fr_FR" });
    patchWithCleanup(session, {
        cache_hashes: { translations: 1 },
    })
    patchFetch();
    patchWithCleanup(browser, {
        fetch(url) {
            assert.strictEqual(url, "/web/webclient/translations/1?lang=fr_FR");
            return super.fetch(...arguments);
        },
    });
    serviceRegistry.add("localization", localizationService);
    await makeTestEnv();
});

QUnit.test("lang is given by an attribute on the DOM root node", async (assert) => {
    patchWithCleanup(session.user_context, { lang: null });
    document.documentElement.setAttribute("lang", "fr-FR");
    registerCleanup(() => {
        document.documentElement.removeAttribute("lang");
    });
    patchWithCleanup(session, {
        cache_hashes: { translations: 1 },
    })
    patchFetch();
    patchWithCleanup(browser, {
        fetch(url) {
            assert.strictEqual(url, "/web/webclient/translations/1?lang=fr_FR");
            return super.fetch(...arguments);
        },
    });
    serviceRegistry.add("localization", localizationService);
    await makeTestEnv();
});

QUnit.test("url is given by the session", async (assert) => {
    patchWithCleanup(session, {
        translationURL: "/get_translations",
        cache_hashes: { translations: 1 },
    })
    patchFetch();
    patchWithCleanup(browser, {
        fetch(url) {
            assert.strictEqual(url, "/get_translations/1?lang=en");
            return super.fetch(...arguments);
        },
    });
    serviceRegistry.add("localization", localizationService);
    await makeTestEnv();
});

QUnit.test("can translate a text node", async (assert) => {
    assert.expect(1);
    TestComponent.template = xml`<div>Hello</div>`;
    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv();
    patchWithCleanup(translatedTerms, { ...terms });
    const target = getFixture();
    await mount(TestComponent, target, { env });
    assert.strictEqual(target.innerText, "Bonjour");
});

QUnit.test("can lazy translate", async (assert) => {
    // Can't use patchWithCleanup cause it doesn't support Symbol
    translatedTerms[translationLoaded] = false;
    assert.expect(3);
    TestComponent.template = xml`<div><t t-esc="constructor.someLazyText" /></div>`;
    TestComponent.someLazyText = _t("Hello");
    assert.throws(() => TestComponent.someLazyText.toString());
    assert.throws(() => TestComponent.someLazyText.valueOf());

    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv();
    patchWithCleanup(translatedTerms, { ...terms });
    translatedTerms[translationLoaded] = true;
    const target = getFixture();
    await mount(TestComponent, target, { env });
    assert.strictEqual(target.innerText, "Bonjour");
});

QUnit.test("luxon is configured in the correct lang", async (assert) => {
    await patchLang("fr_BE");
    assert.strictEqual(DateTime.utc(2021, 12, 10).toFormat("MMMM"), "décembre");
});

QUnit.module("Numbering system");

QUnit.test("arabic has the correct numbering system (generic)", async (assert) => {
    await patchLang("ar_001");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "١٠/١٢/٢٠٢١ ١٢:٠٠:٠٠"
    );
});

QUnit.test("arabic has the correct numbering system (Algeria)", async (assert) => {
    await patchLang("ar_DZ");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "10/12/2021 12:00:00"
    );
});

QUnit.test("arabic has the correct numbering system (Lybia)", async (assert) => {
    await patchLang("ar_LY");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "10/12/2021 12:00:00"
    );
});

QUnit.test("arabic has the correct numbering system (Morocco)", async (assert) => {
    await patchLang("ar_MA");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "10/12/2021 12:00:00"
    );
});

QUnit.test("arabic has the correct numbering system (Saudi Arabia)", async (assert) => {
    await patchLang("ar_SA");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "١٠/١٢/٢٠٢١ ١٢:٠٠:٠٠"
    );
});

QUnit.test("arabic has the correct numbering system (Tunisia)", async (assert) => {
    await patchLang("ar_TN");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "10/12/2021 12:00:00"
    );
});

QUnit.test("bengalese has the correct numbering system", async (assert) => {
    await patchLang("bn");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "১০/১২/২০২১ ১২:০০:০০"
    );
});

QUnit.test("punjabi (gurmukhi) has the correct numbering system", async (assert) => {
    await patchLang("pa_in");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "੧੦/੧੨/੨੦੨੧ ੧੨:੦੦:੦੦"
    );
});

QUnit.test("tamil has the correct numbering system", async (assert) => {
    await patchLang("ta");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd/MM/yyyy hh:mm:ss"),
        "௧௦/௧௨/௨௦௨௧ ௧௨:௦௦:௦௦"
    );
});

QUnit.test(
    "_t fills the format specifiers in translated terms with its extra arguments",
    async (assert) => {
        patchWithCleanup(translatedTerms, { "Due in %s days": "Échéance dans %s jours" });
        const translatedStr = _t("Due in %s days", 513);
        assert.strictEqual(translatedStr, "Échéance dans 513 jours");
    }
);

QUnit.test(
    "_t fills the format specifiers in lazy translated terms with its extra arguments",
    async (assert) => {
        translatedTerms[translationLoaded] = false;
        const translatedStr = _t("Due in %s days", 513);
        patchWithCleanup(translatedTerms, { "Due in %s days": "Échéance dans %s jours" });
        translatedTerms[translationLoaded] = true;
        assert.equal(translatedStr, "Échéance dans 513 jours");
    }
);
