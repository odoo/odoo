/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Progress } from "@odx_owl/components/progress/progress";

test("indeterminate progress omits aria-valuenow and exposes loading text", async () => {
    await mountWithCleanup(Progress, {
        props: {
            ariaLabel: "Deployment progress",
            ariaValueText: "Synchronizing assets",
            indeterminate: true,
        },
    });

    expect(`[role="progressbar"]`).toHaveAttribute("data-state", "indeterminate");
    expect(`[role="progressbar"]`).not.toHaveAttribute("aria-valuenow");
    expect(`[role="progressbar"]`).toHaveAttribute("aria-valuetext", "Synchronizing assets");
    expect(`.odx-progress__indicator`).toHaveAttribute("data-state", "indeterminate");
});

test("determinate progress clamps value to max and marks completion", async () => {
    await mountWithCleanup(Progress, {
        props: {
            max: 150,
            value: 200,
        },
    });

    expect(`[role="progressbar"]`).toHaveAttribute("aria-valuemax", "150");
    expect(`[role="progressbar"]`).toHaveAttribute("aria-valuenow", "150");
    expect(`[role="progressbar"]`).toHaveAttribute("data-state", "complete");
    expect(`.odx-progress__indicator`).toHaveAttribute("data-state", "complete");
});
