import { describe, expect, test } from "@odoo/hoot";

import { formatList, jsToPyLocale, pyToJsLocale } from "@web/core/l10n/utils";
import { user } from "@web/core/user";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

describe("formatList", () => {
    test("defaults to the current user's locale", () => {
        patchWithCleanup(user, { lang: "es-ES" });
        const list = ["A", "B", "C"];
        expect(formatList(list)).toBe("A, B y C");
    });

    test("defaults to English if the user's locale can't be retrieved", () => {
        patchWithCleanup(user, { lang: "" });
        const list = ["A", "B", "C"];
        expect(formatList(list)).toBe("A, B, and C");
    });

    test("takes style into account", () => {
        const list = ["A", "B", "C"];
        expect(formatList(list, { style: "or" })).toBe("A, B, or C");
    });

    test("uses the specified locale", () => {
        const list = ["A", "B", "C"];
        expect(formatList(list, { localeCode: "fr-FR" })).toBe("A, B et C");
    });
});

describe("jsToPyLocale", () => {
    test("2-letter ISO 639 code", () => expect(jsToPyLocale("tg")).toBe("tg"));
    test("3-letter ISO 639 code", () => expect(jsToPyLocale("kab")).toBe("kab"));
    test("language with region", () => expect(jsToPyLocale("fr-BE")).toBe("fr_BE"));
    test("language with region (UN M49 code)", () => expect(jsToPyLocale("es-419")).toBe("es_419"));
    test("language with Latin script", () => expect(jsToPyLocale("sr-Latn")).toBe("sr@latin"));
    test("language with Cyrillic script", () => expect(jsToPyLocale("sr-Cyrl")).toBe("sr@Cyrl"));
    test("language with region and script", () =>
        expect(jsToPyLocale("sr-Latn-RS")).toBe("sr_RS@latin"));
    test("already converted locale", () => expect(jsToPyLocale("fr_TG")).toBe("fr_TG"));
    test("already converted locale with script", () =>
        expect(jsToPyLocale("sr@latin")).toBe("sr@latin"));
    test("undefined locale", () => expect(jsToPyLocale(undefined)).toBe(""));
    test("Tagalog", () => expect(jsToPyLocale("tl-PH")).toBe("tl_PH"));
    test("Filipino", () => expect(jsToPyLocale("fil-PH")).toBe("tl_PH"));
});

describe("pyToJsLocale", () => {
    test("2-letter ISO 639 code", () => expect(pyToJsLocale("tg")).toBe("tg"));
    test("3-letter ISO 639 code", () => expect(pyToJsLocale("kab")).toBe("kab"));
    test("language with region", () => expect(pyToJsLocale("fr_BE")).toBe("fr-BE"));
    test("language with region (UN M49 code)", () => expect(pyToJsLocale("es_419")).toBe("es-419"));
    test("language with Latin script", () => expect(pyToJsLocale("sr@latin")).toBe("sr-Latn"));
    test("language with Cyrillic script", () => expect(pyToJsLocale("sr@Cyrl")).toBe("sr-Cyrl"));
    test("language with region and script", () =>
        expect(pyToJsLocale("sr_RS@latin")).toBe("sr-Latn-RS"));
    test("already converted locale", () => expect(pyToJsLocale("fr-TG")).toBe("fr-TG"));
    test("already converted locale with script", () =>
        expect(pyToJsLocale("sr-Latn")).toBe("sr-Latn"));
    test("undefined locale", () => expect(pyToJsLocale(undefined)).toBe(""));
});
