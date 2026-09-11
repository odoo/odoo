import { delay } from "@web/core/utils/concurrency";
import {
    changeOptionInPopover,
    clickOnElement,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const animatedColumnSelector = ":iframe .s_three_columns .row > :first-child";

function getIframeWindow() {
    return document.querySelector("iframe:not(.o_ignore_in_tour)").contentWindow;
}

function setupAnimationCounter() {
    return {
        content: "Start tracking animation restarts on the first column",
        trigger: animatedColumnSelector,
        run() {
            const iframeWindow = getIframeWindow();
            iframeWindow.__wanimHoverPreviewTest = { count: 0 };
            this.anchor.addEventListener("animationstart", () => {
                iframeWindow.__wanimHoverPreviewTest.count++;
            });
        },
    };
}

function checkAnimationRestartCount(expectedCount) {
    return {
        content: `Check that the animation restarted ${expectedCount} time(s)`,
        trigger: animatedColumnSelector,
        async run() {
            const iframeWindow = getIframeWindow();
            await delay(1000);
            if (iframeWindow.__wanimHoverPreviewTest.count !== expectedCount) {
                throw new Error(
                    `Expected ${expectedCount} animation restart(s), got ${iframeWindow.__wanimHoverPreviewTest.count}.`
                );
            }
        },
    };
}

function hoverSnippetOptionAndAssertNoRestart(expectedCount) {
    return [
        {
            content: "Hover the snippet Content Width option",
            trigger:
                ".hb-row[data-label='Content Width'] .o-hb-btn[data-action-param='o_container_small']",
            run: "hover",
        },
        {
            content: "Stop hovering the snippet option",
            trigger: ":iframe .s_three_columns .row > :nth-child(2)",
            run: "hover",
        },
        {
            content: "Check that stopping the snippet option preview did not restart the animation",
            trigger: animatedColumnSelector,
            async run() {
                const iframeWindow = getIframeWindow();
                await new Promise((resolve) => setTimeout(resolve, 500));
                if (iframeWindow.__wanimHoverPreviewTest.count !== expectedCount) {
                    throw new Error(
                        `The animation restarted while previewing a parent option. Expected ${expectedCount}, got ${iframeWindow.__wanimHoverPreviewTest.count}.`
                    );
                }
            },
        },
    ];
}

registerWebsitePreviewTour(
    "animate_option_preview_hover",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_three_columns",
            name: "Columns",
            groupName: "Columns",
        }),
        clickOnElement("First Card", animatedColumnSelector),
        setupAnimationCounter(),
        ...changeOptionInPopover("Card", "Animation", "[data-action-value='onAppearance']"),
        checkAnimationRestartCount(1),
        ...hoverSnippetOptionAndAssertNoRestart(1),
        ...changeOptionInPopover("Card", "Effect", "[data-action-value='o_anim_slide_in']"),
        checkAnimationRestartCount(2),
        {
            content: "Set the animation intensity to 100",
            trigger: ".hb-row[data-label='Intensity'] input",
            run: "range 100",
        },
        checkAnimationRestartCount(3),
        ...hoverSnippetOptionAndAssertNoRestart(3),
        {
            content: "Click on the 'undo' button",
            trigger: ".o-snippets-top-actions button.fa-undo",
            run: "click",
        },
        checkAnimationRestartCount(4),
        {
            content: "Click on the 'redo' button",
            trigger: ".o-snippets-top-actions button.fa-repeat",
            run: "click",
        },
        checkAnimationRestartCount(5),
    ]
);
