/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { translatedTerms, _lt } from "@web/core/l10n/translation";
import { localizationService } from "@web/core/l10n/localization_service";
import { registry } from "@web/core/registry";
import { patch, unpatch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";

const { mount } = owl;

const terms = { Hello: "Bonjour" };
const serviceRegistry = registry.category("services");
class TestComponent extends owl.Component {}

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
    const defaultLocale = luxon.Settings.defaultLocale;
    registerCleanup(() => {
        luxon.Settings.defaultLocale = defaultLocale;
    });
    patchWithCleanup(session, {
        user_context: {...session.user_context, lang: "fr_BE"},
    });
    patchWithCleanup(browser, {
        fetch() {
            return {
                ok: true,
                json() {
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
            };
        },
    });
    serviceRegistry.add("localization", localizationService);

    await makeTestEnv();

    assert.strictEqual(luxon.DateTime.utc(2021, 12, 10).toFormat("MMMM"), "décembre");
});
