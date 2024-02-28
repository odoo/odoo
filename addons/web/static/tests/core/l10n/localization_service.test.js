import { describe, expect, test } from "@odoo/hoot";

import { browser } from "@web/core/browser/browser";
import { localizationService } from "@web/core/l10n/localization_service";
import { translatedTerms, translationLoaded } from "@web/core/l10n/translation";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

const patchFetch = (modules = {}) => {
    patchWithCleanup(browser, {
        fetch: async () => ({
            ok: true,
            json: async () => ({
                modules,
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
        })
    });
}

describe("localization service", () => {
    test("loads simple translations correctly", async () => {
        patchFetch({
            module_a: {
                messages: [
                    { id: "disabled", string: "désactivé" },
                ]
            },
        });
        await localizationService.start();
        // toEqual doesn't seem to support Symbol keys yet
        expect(translatedTerms[translationLoaded]).toBe(true);
        expect(translatedTerms).toEqual({
            disabled: "désactivé",
        });
    });

    test("loads context translations correctly", async () => {
        patchFetch({
            module_a: {
                messages: [
                    { id: ["software_feature", "disabled"], string: "désactivé" },
                    { id: ["health", "disabled"], string: "handicapé" },
                ]
            },
            module_b: {
                messages: [
                    { id: "disabled", string: "désactivé/handicapé" },
                ],
            },
        });
        await localizationService.start();
        // toEqual doesn't seem to support Symbol keys yet
        expect(translatedTerms[translationLoaded]).toBe(true);
        expect(translatedTerms).toEqual({
            disabled: {
                "": "désactivé/handicapé",
                software_feature: "désactivé",
                health: "handicapé",
            },
        });
    });
});
