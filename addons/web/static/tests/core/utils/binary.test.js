import { describe, expect, test } from "@odoo/hoot";
import { patchTranslations } from "@web/../tests/web_test_helpers";

import { humanSize } from "@web/core/utils/binary";

describe.current.tags("headless");

test("humanSize", () => {
    patchTranslations();
    expect(humanSize(0)).toBe("0.00 Bytes");
    expect(humanSize(3)).toBe("3.00 Bytes");
    expect(humanSize(2048)).toBe("2.00 Kb");
    expect(humanSize(2645000)).toBe("2.52 Mb");
});
