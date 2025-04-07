import { registry } from "@web/core/registry";
import { waitFor } from "@odoo/hoot-dom";

registry.category("web_tour.tours").add("tourSessionOpening", {
    steps: () =>
        [
            {
                trigger: "body",
                content: "Wait loading is finished if it is shown",
                timeout: 25000,
                async run() {
                    await waitFor("body:not(:has(.pos-loader))", { timeout: 20000 });
                    const endTime = Date.now();
                    const startTime = performance.timeOrigin;
                    const loadingTimeSec = (endTime - startTime) / 1000;
                    const displayText = ` POS loading time: ${loadingTimeSec} seconds `;
                    console.log(
                        "\n┏" + "━".repeat(displayText.length) + "┓",
                        `\n┃${displayText}┃`,
                        "\n┗" + "━".repeat(displayText.length) + "┛"
                    );
                },
            },
        ].flat(),
});
