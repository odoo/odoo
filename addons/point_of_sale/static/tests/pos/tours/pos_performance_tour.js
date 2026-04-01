import { registry } from "@web/core/registry";

function logText(displayText) {
    console.log(
        "\n\n┏" + "━".repeat(displayText.length) + "┓",
        `\n┃${displayText}┃`,
        "\n┗" + "━".repeat(displayText.length) + "┛\n"
    );
}

registry.category("web_tour.tours").add("tourSessionOpenProductPerformance", {
    steps: () =>
        [
            {
                trigger: "body",
                timeout: 25000,
                async run({ waitFor }) {
                    await waitFor("body:not(:has(.pos-loader))", { timeout: 20000 });
                    const startTime = performance.timeOrigin;
                    const endTime = Date.now();
                    const loadingTimeSec = (endTime - startTime) / 1000;
                    logText(
                        ` POS loading time: ${loadingTimeSec.toFixed(2)} seconds for 20000 products`
                    );
                },
            },
        ].flat(),
});
