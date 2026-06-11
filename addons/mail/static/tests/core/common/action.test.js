import { Action } from "@mail/core/common/action";

import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");

test("store is correctly set on actions", async () => {
    const storeSym = Symbol("STORE");
    const action = new Action({
        id: "test",
        definition: {},
        store: storeSym,
    });
    expect(action.store).toBe(storeSym);
});
