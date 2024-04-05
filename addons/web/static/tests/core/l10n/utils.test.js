import { describe, expect, test } from "@odoo/hoot";

import { formatList } from "@web/core/l10n/utils";
import { user } from "@web/core/user";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

describe("formatList", () => {
    test("defaults to the current user's locale", () => {
        patchWithCleanup(user, { lang: "es_ES" });
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
