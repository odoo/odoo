import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("web.show_password");

describe.current.tags("interaction_dev");

const template = `
    <div class="input-group">
        <input type="password" id="password" class="form-control" required="required" name="visibility_password" />
        <div class="visually-hidden" aria-live="polite"></div>
        <button class="btn border border-start-0 o_show_password" type="button">
            <i class="oi" data-icon="visibility"></i>
        </button>
    </div>
`;

test("show_password is started when there is a .o_show_password", async () => {
    const { core } = await startInteractions(template);
    expect(core.interactions).toHaveLength(1);
});

test("input type changes on clicking the eye icon", async () => {
    await startInteractions(template);
    const showEl = queryOne(".o_show_password");
    expect("input").toHaveAttribute("type", "password");
    await click(showEl);
    expect("input").toHaveAttribute("type", "text");
    await click(showEl);
    expect("input").toHaveAttribute("type", "password");
});

test("show_password updates its pressed state and announces when shown", async () => {
    await startInteractions(template);
    const showEl = queryOne(".o_show_password");
    const liveRegion = queryOne('[aria-live="polite"]');

    expect(showEl).toHaveAttribute("aria-pressed", "false");
    await click(showEl);
    expect(showEl).toHaveAttribute("aria-pressed", "true");
    expect(liveRegion).toHaveText("Your password is shown.");

    await click(showEl);
    expect(showEl).toHaveAttribute("aria-pressed", "false");
    expect(liveRegion).toHaveText("");
});
