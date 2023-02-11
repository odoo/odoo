/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { localizationService } from "@web/core/l10n/localization_service";
import { translatedTerms, _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch, unpatch } from "@web/core/utils/patch";
import { session } from "@web/session";

const { mount } = owl;
const { DateTime, Settings } = luxon;

const terms = { Hello: "Bonjour" };
const serviceRegistry = registry.category("services");
class TestComponent extends owl.Component {}

/**
 * Patches the 'lang' of the user session and context.
 *
 * @param {string} lang
 * @returns {Promise<void>}
 */
const patchLang = async (lang) => {
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
};

QUnit.module("Translations");

QUnit.test("can translate a text node", async (assert) => {
    assert.expect(1);
    TestComponent.template = owl.tags.xml`<div>Hello</div>`;
    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv();
    patch(translatedTerms, "add translations", terms);
    const target = getFixture();
    await mount(TestComponent, { env, target });
    assert.strictEqual(target.innerText, "Bonjour");
    unpatch(translatedTerms, "add translations");
});

QUnit.test("can lazy translate", async (assert) => {
    assert.expect(3);

    TestComponent.template = owl.tags.xml`<div><t t-esc="constructor.someLazyText" /></div>`;
    TestComponent.someLazyText = _lt("Hello");
    assert.strictEqual(TestComponent.someLazyText.toString(), "Hello");
    assert.strictEqual(TestComponent.someLazyText.valueOf(), "Hello");

    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv();
    patch(translatedTerms, "add translations", terms);
    const target = getFixture();
    await mount(TestComponent, { env, target });
    assert.strictEqual(target.innerText, "Bonjour");
    unpatch(translatedTerms, "add translations");
});

QUnit.test("_t is in env", async (assert) => {
    assert.expect(1);
    TestComponent.template = owl.tags.xml`<div><t t-esc="env._t('Hello')"/></div>`;
    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv();
    patch(translatedTerms, "add translations", terms);
    const target = getFixture();
    await mount(TestComponent, { env, target });
    assert.strictEqual(target.innerText, "Bonjour");
    unpatch(translatedTerms, "add translations");
});

QUnit.test("luxon is configured in the correct lang", async (assert) => {
    await patchLang("fr_BE");
    assert.strictEqual(DateTime.utc(2021, 12, 10).toFormat("MMMM"), "décembre");
});

QUnit.module("Numbering system");

QUnit.test("arabic has the correct numbering system (generic)", async (assert) => {
    await patchLang("ar_001");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "١٠ ديسمبر, ٢٠٢١ ١٢:٠٠:٠٠"
    );
});

QUnit.test("arabic has the correct numbering system (Algeria)", async (assert) => {
    await patchLang("ar_DZ");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "10 ديسمبر, 2021 12:00:00"
    );
});

QUnit.test("arabic has the correct numbering system (Lybia)", async (assert) => {
    await patchLang("ar_LY");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "10 ديسمبر, 2021 12:00:00"
    );
});

QUnit.test("arabic has the correct numbering system (Morocco)", async (assert) => {
    await patchLang("ar_MA");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "10 دجنبر, 2021 12:00:00"
    );
});

QUnit.test("arabic has the correct numbering system (Saudi Arabia)", async (assert) => {
    await patchLang("ar_SA");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "١٠ جمادى الأولى, ٢٠٢١ ١٢:٠٠:٠٠"
    );
});

QUnit.test("arabic has the correct numbering system (Tunisia)", async (assert) => {
    await patchLang("ar_TN");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "10 ديسمبر, 2021 12:00:00"
    );
});

QUnit.test("bengalese has the correct numbering system", async (assert) => {
    await patchLang("bn");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "১০ ডিসেম্বর, ২০২১ ১২:০০:০০"
    );
});

QUnit.test("punjabi (gurmukhi) has the correct numbering system", async (assert) => {
    await patchLang("pa_in");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "੧੦ M12, ੨੦੨੧ ੧੨:੦੦:੦੦"
    );
});

QUnit.test("tamil has the correct numbering system", async (assert) => {
    await patchLang("ta");
    assert.strictEqual(
        DateTime.utc(2021, 12, 10).toFormat("dd MMM, yyyy hh:mm:ss"),
        "௧௦ டிச., ௨௦௨௧ ௧௨:௦௦:௦௦"
    );
});
