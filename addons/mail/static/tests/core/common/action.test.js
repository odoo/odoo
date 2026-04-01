import { Action } from "@mail/core/common/action";

import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");

test("store is correctly set on actions", async () => {
    const storeSym = Symbol("STORE");
    const ownerSym = Symbol("COMPONENT");
    const action = new Action({
        owner: ownerSym,
        id: "test",
        definition: {},
        store: storeSym,
    });
    expect(action.store).toBe(storeSym);
});
