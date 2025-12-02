import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { getService, makeMockEnv } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

let titleService;

beforeEach(async () => {
    await makeMockEnv();
    titleService = getService("title");
});

test("simple title", () => {
    titleService.setParts({ one: "MyOdoo" });
    expect(titleService.current).toBe("MyOdoo");
});

test("add title part", () => {
    titleService.setParts({ one: "MyOdoo", two: null });
    expect(titleService.current).toBe("MyOdoo");
    titleService.setParts({ three: "Import" });
    expect(titleService.current).toBe("MyOdoo - Import");
});

test("modify title part", () => {
    titleService.setParts({ one: "MyOdoo" });
    expect(titleService.current).toBe("MyOdoo");
    titleService.setParts({ one: "Zopenerp" });
    expect(titleService.current).toBe("Zopenerp");
});

test("delete title part", () => {
    titleService.setParts({ one: "MyOdoo" });
    expect(titleService.current).toBe("MyOdoo");
    titleService.setParts({ one: null });
    expect(titleService.current).toBe("Odoo");
});

test("all at once", () => {
    titleService.setParts({ one: "MyOdoo", two: "Import" });
    expect(titleService.current).toBe("MyOdoo - Import");
    titleService.setParts({ one: "Zopenerp", two: null, three: "Sauron" });
    expect(titleService.current).toBe("Zopenerp - Sauron");
});

test("get title parts", () => {
    expect(titleService.current).toBe("");
    titleService.setParts({ one: "MyOdoo", two: "Import" });
    expect(titleService.current).toBe("MyOdoo - Import");
    const parts = titleService.getParts();
    expect(parts).toEqual({ one: "MyOdoo", two: "Import" });
    parts.action = "Export";
    expect(titleService.current).toBe("MyOdoo - Import"); // parts is a copy!
});
