import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.multirange_input");

describe.current.tags("interaction_dev");

test("multirange_input lib gets initialised", async () => {
    document.querySelector("html").setAttribute("lang", "en_US");
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <input type="range" multiple="multiple"
                class="form-range range-with-input"
                data-currency="EUR" data-currency-position="before"
                step="'1'" min="50" max="4000" value="500,1000"/>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    expect(queryAll("input[type=range]")).toHaveLength(2);
});
