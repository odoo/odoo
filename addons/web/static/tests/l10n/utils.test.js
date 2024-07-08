import { describe, expect, test } from "@odoo/hoot";

import { pyToJsLocale } from "@web/core/l10n/utils";

describe.current.tags("headless");

describe("pyToJsLocale", () => {
    test("base case", () => expect(pyToJsLocale("fr_BE")).toBe("fr-BE"));
    test("3-letter language", () => expect(pyToJsLocale("kab")).toBe("kab"));
    test("locale with numbers", () => expect(pyToJsLocale("es_419")).toBe("es-419"));
    test("locale with script modifier", () => expect(pyToJsLocale("sr@latin")).toBe("sr-Latn"));
    test("locale with country and script modifier", () =>
        expect(pyToJsLocale("sr_RS@latin")).toBe("sr-Latn-RS"));
    test("already converted locale", () => expect(pyToJsLocale("en-US")).toBe("en-US"));
    test("undefined locale", () => expect(pyToJsLocale(undefined)).toBe(""));
});
