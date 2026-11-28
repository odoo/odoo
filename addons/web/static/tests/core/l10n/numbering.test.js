import { describe, expect, test } from "@odoo/hoot";
import { patchTranslations, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { localizeDigits, normalizeDigits } from "@web/core/l10n/numbering";
import { _t } from "@web/core/l10n/translation";

const { Settings } = luxon;

describe.current.tags("headless");

test("latin numbering system: values are unchanged", () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "latn" });
    expect(localizeDigits(1234.5)).toBe(1234.5);
    expect(localizeDigits("1,234.50")).toBe("1,234.50");
    expect(normalizeDigits("1,234.50")).toBe("1,234.50");
});

test("localizeDigits", () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
    expect(localizeDigits(1234.5)).toBe("١٢٣٤.٥");
    expect(localizeDigits("1,234.50 kB")).toBe("١,٢٣٤.٥٠ kB");
    expect(localizeDigits(0)).toBe("٠");
    // values which are neither numbers nor strings are returned unchanged
    expect(localizeDigits(null)).toBe(null);
    expect(localizeDigits(undefined)).toBe(undefined);
    expect(localizeDigits(false)).toBe(false);

    patchWithCleanup(Settings, { defaultNumberingSystem: "beng" });
    expect(localizeDigits(1234)).toBe("১২৩৪");
    patchWithCleanup(Settings, { defaultNumberingSystem: "tamldec" });
    expect(localizeDigits(1234)).toBe("௧௨௩௪");
});

test("normalizeDigits", () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
    expect(normalizeDigits("١,٢٣٤.٥٠")).toBe("1,234.50");
    // latin digits are kept, so that the user can type both
    expect(normalizeDigits("12 ١٢")).toBe("12 12");
    expect(normalizeDigits(null)).toBe(null);
});

test("numbers given to _t use the numbering system", () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
    patchTranslations();
    expect(_t("%s records", 12).toString()).toBe("١٢ records");
    expect(_t("%(count)s records", { count: 12 }).toString()).toBe("١٢ records");
    // strings are not changed, they may be codes or references
    expect(_t("Reference %s", "SO012").toString()).toBe("Reference SO012");
});
