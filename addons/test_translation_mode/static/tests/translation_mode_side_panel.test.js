import {
    afterEach,
    animationFrame,
    clear,
    click,
    describe,
    expect,
    fill,
    queryAll,
    test,
} from "@odoo/hoot";
import {
    defineModels,
    makeMockEnv,
    models,
    mountWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { encodeTranslation } from "../src/translation.patch";
import { urlParams } from "../src/translation_mode_service";

class IrConfigParameter extends models.ServerModel {
    _name = "ir.config_parameter";
    _records = [{ key: "test_translation_mode.translation_url", value: "www.example.com" }];

    /**
     * @param {string} key
     */
    get_str(key) {
        return this._filter([["key", "=", key]])[0]?.value ?? null;
    }
}

class ResLang extends models.ServerModel {
    _name = "res.lang";
    _records = [
        {
            code: "en_US",
            display_name: "English",
            flag_image_url: "",
        },
        {
            code: "fr_FR",
            display_name: "French",
            flag_image_url: "",
        },
    ];
}

defineModels({ IrConfigParameter, ResLang });
afterEach(() => {
    for (const key in urlParams) {
        delete urlParams[key];
    }
});
describe.current.tags("desktop");

/**
 * @param {string} source
 * @param {string} [translation]
 */
function mockEncodedTranslation(source, translation) {
    const metadata = ["web", source];
    if (translation) {
        metadata.push(translation);
    }
    return encodeTranslation(translation ? 1 : 0, metadata, translation || source);
}

test("side panel is not rendered by default", async () => {
    await mountWithCleanup(/* xml */ `
        <div class="sample-element">
            ${mockEncodedTranslation("Component")}
        </div>
    `);

    expect(".sample-element:only").toHaveText("Component");
    expect(".o-translate-side-panel").not.toHaveCount();
});

test("side panel with no translation", async () => {
    serverState.lang = "en_US";

    expect(document.body).not.toHaveClass("o-body-with-translate-side-panel");

    await makeMockEnv({ debug: "translate" });
    await mountWithCleanup(/* xml */ `
        <div class="sample-element">
            ${mockEncodedTranslation("Component", "Component")}
        </div>
    `);

    expect(document.body).toHaveClass("o-body-with-translate-side-panel");

    expect(".sample-element:only").toHaveText("Component");
    expect(".o-translate-side-panel:only").toHaveText(
        "Translation highlighting has been disabled for this language."
    );
    expect(".o-translate-side-panel .o-translate-card").not.toHaveCount();
});

test("side panel with translations", async () => {
    serverState.lang = "fr_FR";
    serverState.serverVersion = [3, 0, 0, "final", 0, ""];

    expect(document.body).not.toHaveClass("o-body-with-translate-side-panel");

    await makeMockEnv({ debug: "translate" });
    await mountWithCleanup(/* xml */ `
        <div class="sample-element">
            ${mockEncodedTranslation("Component", "Composant")}
        </div>
    `);

    expect(document.body).toHaveClass("o-body-with-translate-side-panel");

    expect(".sample-element:only").toHaveText("Composant");
    expect(".o-translate-side-panel:only .o-translate-card:only").toHaveText(
        ["Text", "Translate", "Component", "Composant"].join("\n")
    );
    expect(".o-translate-side-panel .o-translate-card a[href]").toHaveAttribute(
        "href",
        "www.example.com/translate/odoo-3/web/fr_FR/?checksum=25c3e74edddbe2ff"
    );
    expect(queryAll(".o-translation-pointer", { root: document.body })).not.toHaveCount();

    await click(".o-translate-card");

    expect(queryAll(".o-translation-pointer", { root: document.body })).toHaveCount(1);

    await click(".sample-element");

    expect(queryAll(".o-translation-pointer", { root: document.body })).not.toHaveCount();

    await click("[name='filter-translations']");
    await fill("aaaa");
    await animationFrame();

    expect(".o-translate-side-panel .o-translate-card").not.toHaveCount();

    await clear();
    await fill("comp");
    await animationFrame();

    expect(".o-translate-side-panel .o-translate-card").toHaveCount(1);
});
