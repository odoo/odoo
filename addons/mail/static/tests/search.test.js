import { nearestGreaterThanOrEqual } from "@mail/utils/common/misc";
import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");

test("nearestGreaterThanOrEqual", () => {
    const list = [3, 5, 7, 9];
    expect(nearestGreaterThanOrEqual(list, 3)).toBe(3);
    expect(nearestGreaterThanOrEqual(list, 7)).toBe(7);
    expect(nearestGreaterThanOrEqual(list, 9)).toBe(9);
    expect(nearestGreaterThanOrEqual(list, 4)).toBe(5);
    expect(nearestGreaterThanOrEqual(list, 10)).toBe(null);
    expect(nearestGreaterThanOrEqual(list, 2)).toBe(3);
    const list2 = [{ id: 3 }, { id: 5 }, { id: 7 }, { id: 9 }];
    expect(nearestGreaterThanOrEqual(list2, 3, (e) => e.id)).toEqual({ id: 3 });
    expect(nearestGreaterThanOrEqual(list2, 7, (e) => e.id)).toEqual({ id: 7 });
    expect(nearestGreaterThanOrEqual(list2, 9, (e) => e.id)).toEqual({ id: 9 });
    expect(nearestGreaterThanOrEqual(list2, 4, (e) => e.id)).toEqual({ id: 5 });
    expect(nearestGreaterThanOrEqual(list2, 10, (e) => e.id)).toBe(null);
    expect(nearestGreaterThanOrEqual(list2, 2, (e) => e.id)).toEqual({ id: 3 });
});
