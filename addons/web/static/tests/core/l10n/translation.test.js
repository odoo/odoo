import { describe, expect, test } from "@odoo/hoot";

import { _ct, _t } from "@web/core/l10n/translation";
import { patchTranslations } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

describe("translation functions", () => {
    test("_t returns the correct translation", () => {
        patchTranslations({
            disabled: "désactivé",
        });
        expect(_t("disabled")).toBe("désactivé");
    });

    test("_t returns the correct translation with placeholders", () => {
        patchTranslations({
            "%s is disabled": "%s est désactivé", // Translator has no clue
            "%s has been disabled since %s": "%s est handicapé depuis %s", // Translator has no clue
            "%(user)s is disabled": "%(user)s est handicapé",
            "%(feature)s has been disabled since %(date)s": "%(feature)s est désactivé depuis %(date)s",
        });
        expect(_t("%s is disabled", "John Doe")).toBe("John Doe est désactivé");
        expect(_t("%s has been disabled since %s", "UBL 1.0", "2008-01-01")).toBe("UBL 1.0 est handicapé depuis 2008-01-01");
        expect(_t("%(user)s is disabled", { user: "John Doe" })).toBe("John Doe est handicapé");
        expect(_t("%(feature)s has been disabled since %(date)s", { feature: "UBL 1.0", date: "2008-01-01" })).toBe(
            "UBL 1.0 est désactivé depuis 2008-01-01"
        );
    });

    test("_t returns the original term if there is no translation", () => {
        patchTranslations();
        expect(_t("disabled")).toBe("disabled");
    });

    test("_t returns the correct translation inside context translations", () => {
        patchTranslations({
            disabled: {
                "": "désactivé",
                "health": "handicapé",
            },
        });
        expect(_t("disabled")).toBe("désactivé");
    });

    test("_ct returns the correct context translation", () => {
        patchTranslations({
            disabled: {
                software_feature: "désactivé",
                health: "handicapé",
            },
        });
        expect(_ct("software_feature", "disabled")).toBe("désactivé");
        expect(_ct("health", "disabled")).toBe("handicapé");
    });

    test("_ct returns the correct context translation with empty string context", () => {
        patchTranslations({
            disabled: {
                "": "désactivé",
            },
        });
        expect(_ct("", "disabled")).toBe("désactivé");
    });

    test("_ct returns the correct context translation with placeholders", () => {
        patchTranslations({
            "%s is disabled": {
                software_feature: "%s est désactivé",
                health: "%s est handicapé",
            },
            "%s has been disabled since %s": {
                software_feature: "%s est désactivé depuis %s",
                health: "%s est handicapé depuis %s",
            },
            "%(object)s is disabled": {
                software_feature: "%(object)s est désactivé",
                health: "%(object)s est handicapé",
            },
            "%(object)s has been disabled since %(date)s": {
                software_feature: "%(object)s est désactivé depuis %(date)s",
                health: "%(object)s est handicapé depuis %(date)s",
            },
        });
        expect(_ct("software_feature", "%s is disabled", "UBL 1.0")).toBe("UBL 1.0 est désactivé");
        expect(_ct("health", "%s is disabled", "John Doe")).toBe("John Doe est handicapé");
        expect(_ct("software_feature", "%s has been disabled since %s", "UBL 1.0", "2008-01-01")).toBe(
            "UBL 1.0 est désactivé depuis 2008-01-01"
        );
        expect(_ct("health", "%s has been disabled since %s", "John Doe", "2002-06-01")).toBe(
            "John Doe est handicapé depuis 2002-06-01"
        );
        expect(_ct("software_feature", "%(object)s is disabled", { object: "UBL 1.0" })).toBe("UBL 1.0 est désactivé");
        expect(_ct("health", "%(object)s is disabled", { object: "John Doe" })).toBe("John Doe est handicapé");
        expect(_ct(
            "software_feature", "%(object)s has been disabled since %(date)s",
            { object: "UBL 1.0", date: "2008-01-01" }
        )).toBe("UBL 1.0 est désactivé depuis 2008-01-01");
        expect(
            _ct("health", "%(object)s has been disabled since %(date)s", { object: "John Doe", date: "2002-06-01" })
        ).toBe("John Doe est handicapé depuis 2002-06-01");
    });

    test("_ct returns the original term if there is no context translation", () => {
        patchTranslations({
            disabled: {
                "": "désactivé",
                health: "handicapé",
            },
        });
        expect(_ct("software_feature", "disabled")).toBe("disabled");
    });
});
