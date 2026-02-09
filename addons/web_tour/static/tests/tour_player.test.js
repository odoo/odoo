import { test, expect } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup, contains } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

const tourRegistry = registry.category("web_tour.tours");

test("Tour Player", async () => {
    tourRegistry.add("tour_player", {
        steps: () => [
            {
                trigger: ".o_button",
                run: "click",
            },
            {
                trigger: ".o_input",
                run: "edit plop",
            },
            {
                trigger: ".o_input",
                run: "edit plop 2",
            },
            {
                trigger: ".o_input",
                run: "edit plop 3",
            },
            {
                trigger: ".o_input",
                run: "edit plop 4",
            },
            {
                trigger: ".o_input",
                run: "edit plop 5",
            },
        ],
    });
    await mountWithCleanup(
        `<div>
            <button class="o_button">Click me</button>
            <input type="text" class="o_input"/>
        </div>`
    );

    await odoo.startTour("tour_player", { mode: "auto", debug: true });
    await waitFor(".o_tour_player");
    await waitFor(".o_tour_overlay");
    expect(".o_tour_pointer_content").toHaveText("run: click");

    await contains(".o_tour_player_play").click();

    expect(".o_tour_player").toHaveCount(1);
    expect(".o_tour_pointer").toHaveCount(1);
    expect(".o_tour_pointer_content").toHaveText("run: edit plop");

    await contains(".o_button_steps").click();
    await contains("tr[data-key='4'] .btn.fa-forward").click();

    expect(".o_input").toHaveValue("plop 3");
    expect(".o_tour_player").toHaveCount(1);
    expect(".o_tour_pointer").toHaveCount(1);

    await contains(".o_tour_player_forward").click();

    expect(".o_input").toHaveValue("plop 5");
    expect(".o_tour_player").toHaveCount(0);
    expect(".o_tour_pointer").toHaveCount(0);
});
