import { expect, test, waitFor } from "@odoo/hoot";
import { signal } from "@odoo/owl";
import {
    mountWithCleanup,
    onRpc,
    installLanguages,
    contains,
} from "@web/../tests/web_test_helpers";
import { TranslationButton } from "@web/views/fields/translation/translation_button";

test("translation in xml mode correctly renders value of attributes", async () => {
    installLanguages({
        en_US: "English",
        fr_BE: "Français",
        es_ES: "Español",
    });
    onRpc("/web/translations/get_translation_for_field", () => ({
        languages: {
            en_US: { name: "English (US)", direction: "ltr", code: "en_US", is_base: true },
        },
        target_lang: "en_US",
        translation_mode: "xml",
        xml_values: {
            en_US: `<div string="&lt;span class=&quot;o_delay_translation&quot; data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;239&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;translated&quot; data-oe-translation-source-sha=&quot;1133&quot;&gt;start  &quot; '  &amp; 100 &gt; 90&lt; end&lt;/span&gt;" />`,
        },
    }));
    await mountWithCleanup(TranslationButton, {
        props: {
            fieldName: "xml",
            resModel: "dummy",
            resId: 1,
            classes: signal({
                "position-relative": true,
            }),
        },
    });

    await contains(".o-translate-button").click();
    await waitFor(".o_translation_dialog .o-translate-full-xml");
    expect(".o-translate--translatable-block").toHaveValue(`start  " '  & 100 > 90< end`);
});
