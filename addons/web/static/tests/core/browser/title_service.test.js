/** @odoo-module */

import { makeMockEnv, getService } from "@web/../tests/web_test_helpers";
import { expect, test, beforeEach, afterEach } from "@odoo/hoot";

let titleService;
let title;

beforeEach(async () => {
    title = document.title;
    await makeMockEnv();
    titleService = await getService("title");
});

afterEach(() => {
    document.title = title;
});

test.tags("headless")("simple title", () => {
    titleService.setParts({ one: "Odoo" });
    expect(titleService.current).toBe("Odoo");
});

test.tags("headless")("add title part", () => {
    titleService.setParts({ one: "Odoo", two: null });
    expect(titleService.current).toBe("Odoo");
    titleService.setParts({ three: "Import" });
    expect(titleService.current).toBe("Odoo - Import");
});

test.tags("headless")("modify title part", () => {
    titleService.setParts({ one: "Odoo" });
    expect(titleService.current).toBe("Odoo");
    titleService.setParts({ one: "Zopenerp" });
    expect(titleService.current).toBe("Zopenerp");
});

test.tags("headless")("delete title part", () => {
    titleService.setParts({ one: "Odoo" });
    expect(titleService.current).toBe("Odoo");
    titleService.setParts({ one: null });
    expect(titleService.current).toBe("");
});

test.tags("headless")("all at once", () => {
    titleService.setParts({ one: "Odoo", two: "Import" });
    expect(titleService.current).toBe("Odoo - Import");
    titleService.setParts({ one: "Zopenerp", two: null, three: "Sauron" });
    expect(titleService.current).toBe("Zopenerp - Sauron");
});

test.tags("headless")("get title parts", () => {
    expect(titleService.current).toBe("");
    titleService.setParts({ one: "Odoo", two: "Import" });
    expect(titleService.current).toBe("Odoo - Import");
    const parts = titleService.getParts();
    expect(parts).toEqual({ one: "Odoo", two: "Import" });
    parts.action = "Export";
    expect(titleService.current).toBe("Odoo - Import"); // parts is a copy!
});
