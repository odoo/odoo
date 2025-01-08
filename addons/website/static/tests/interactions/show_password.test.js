import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { pointerDown, pointerUp } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.show_password");

describe.current.tags("interaction_dev");

const template = `
    <div class="input-group">
        <input type="password" id="password" class="form-control" required="required" name="visibility_password" />
        <button class="btn btn-secondary" type="button" id="showPass">
            <i class="fa fa-eye"></i>
        </button>
    </div>
`;

test("show_password is started when there is a #showPass", async () => {
    const { core } = await startInteractions(template);
    expect(core.interactions).toHaveLength(1);
});

test("input type changes on pointerdown", async () => {
    const { el } = await startInteractions(template);
    const showEl = el.querySelector("#showPass");
    expect("input").toHaveAttribute("type", "password");
    await pointerDown(showEl);
    expect("input").toHaveAttribute("type", "text");
    await pointerUp(showEl.closest("div"));
    expect("input").toHaveAttribute("type", "password");
});
