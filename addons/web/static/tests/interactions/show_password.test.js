import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { pointerDown, pointerUp, queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("web.show_password");

describe.current.tags("interaction_dev");

const template = `
    <div class="input-group">
        <input type="password" id="password" class="form-control" required="required" name="visibility_password" />
        <button class="btn btn-secondary show-password" type="button">
            <i class="fa fa-eye"></i>
        </button>
    </div>
`;

test("show_password is started when there is a .show-password", async () => {
    const { core } = await startInteractions(template);
    expect(core.interactions).toHaveLength(1);
});

test("input type changes on pointerdown", async () => {
    await startInteractions(template);
    const showEl = queryOne(".show-password");
    expect("input").toHaveAttribute("type", "password");
    await pointerDown(showEl);
    expect("input").toHaveAttribute("type", "text");
    await pointerUp(showEl.closest("div"));
    expect("input").toHaveAttribute("type", "password");
});
