import { PagerIndicator } from "@web/core/pager/pager_indicator";
import { mountWithCleanup, patchWithCleanup } from "../../web_test_helpers";
import { config as transitionConfig } from "@web/core/transition";
import { expect, test } from "@odoo/hoot";
import { PAGER_UPDATED_EVENT, pagerBus } from "@web/core/pager/pager";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";

test("displays the pager indicator", async () => {
    patchWithCleanup(transitionConfig, { disabled: true });
    await mountWithCleanup(PagerIndicator, { noMainContainer: true });
    expect(".o_pager_indicator").toHaveCount(0, {
        message: "the pager indicator should not be displayed",
    });
    pagerBus.trigger(PAGER_UPDATED_EVENT, { value: "1-4", total: 10 });
    await animationFrame();
    expect(".o_pager_indicator").toHaveCount(1, {
        message: "the pager indicator should be displayed",
    });
    expect(".o_pager_indicator").toHaveText("1-4 / 10");
    await runAllTimers();
    await animationFrame();
    expect(".o_pager_indicator").toHaveCount(0, {
        message: "the pager indicator should not be displayed",
    });
});
