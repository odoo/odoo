/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { localizationService } from "@web/core/l10n/localization_service";
import { translatedTerms, _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch, unpatch } from "@web/core/utils/patch";
import { session } from "@web/session";

import { Component, xml } from "@odoo/owl";
const { DateTime, Settings } = luxon;

const terms = { Hello: "Bonjour" };
const serviceRegistry = registry.category("services");
class TestComponent extends Component {}

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
    serviceRegistry.add("localization", localizationService);
    await makeTestEnv();
}

QUnit.module("Translations");

QUnit.test("can translate a text node", async (assert) => {
    assert.expect(1);
    TestComponent.template = xml`<div>Hello</div>`;
    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv();
    patch(translatedTerms, "add translations", terms);
    const target = getFixture();
    await mount(TestComponent, target, { env });
    assert.strictEqual(target.innerText, "Bonjour");
    unpatch(translatedTerms, "add translations");
});

QUnit.test("can lazy translate", async (assert) => {
    assert.expect(3);

    TestComponent.template = xml`<div><t t-esc="constructor.someLazyText" /></div>`;
    TestComponent.someLazyText = _lt("Hello");
    assert.strictEqual(TestComponent.someLazyText.toString(), "Hello");
    assert.strictEqual(TestComponent.someLazyText.valueOf(), "Hello");

    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv();
    patch(translatedTerms, "add translations", terms);
    const target = getFixture();
    await mount(TestComponent, target, { env });
    assert.strictEqual(target.innerText, "Bonjour");
    unpatch(translatedTerms, "add translations");
});

QUnit.test("_t is in env", async (assert) => {
    assert.expect(1);
    TestComponent.template = xml`<div><t t-esc="env._t('Hello')"/></div>`;
    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv();
    patch(translatedTerms, "add translations", terms);
    const target = getFixture();
    await mount(TestComponent, target, { env });
    assert.strictEqual(target.innerText, "Bonjour");
    unpatch(translatedTerms, "add translations");
});

QUnit.test("luxon is configured in the correct lang", async (assert) => {
    await patchLang("fr_BE");
    assert.strictEqual(DateTime.utc(2021, 12, 10).toFormat("MMMM"), "décembre");
});

QUnit.test("Mismatched locale sr_RS is correctly converted", async (assert) => {
    patchLang("sr_RS");
    await makeTestEnv();
    assert.strictEqual(DateTime.local().loc.locale, "sr-cyrl");
});

QUnit.test("Mismatched locale sr@latin is correctly converted", async (assert) => {
    patchLang("sr@latin");
    await makeTestEnv();
    assert.strictEqual(DateTime.local().loc.locale, "sr-Latn-RS");
});

QUnit.test("lang is given by an attribute on the DOM root node", async (assert) => {
    assert.expect(1);
    patchWithCleanup(session.user_context, { lang: null });
    document.documentElement.setAttribute("lang", "fr-FR");
    registerCleanup(() => {
        document.documentElement.removeAttribute("lang");
    });
    patchWithCleanup(session, {
        cache_hashes: { translations: 1 },
    })
    serviceRegistry.add("localization", localizationService);
    await makeTestEnv({
        mockRPC(route, params) {
            assert.strictEqual(route, "/web/webclient/translations/1?lang=fr_FR");
            return {
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
            };
        },
    });
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
