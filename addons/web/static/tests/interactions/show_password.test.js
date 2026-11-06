import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("web.show_password");

describe.current.tags("interaction_dev");

const template = `
    <div class="input-group">
        <input type="password" id="password" class="form-control" required="required" name="visibility_password" />
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

test("the eye button is named after the action it performs", async () => {
    await startInteractions(template);
    const showEl = queryOne(".o_show_password");
    expect(showEl).toHaveAttribute("aria-label", "Show password");
    await click(showEl);
    expect(showEl).toHaveAttribute("aria-label", "Hide password");
    await click(showEl);
    expect(showEl).toHaveAttribute("aria-label", "Show password");
    expect(showEl).not.toHaveAttribute("aria-pressed");
});
