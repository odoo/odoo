import {
    changeBackground,
    changeBackgroundColor,
    changeImage,
    changeOption,
    changePaddingSize,
    clickOnSnippet,
    clickOnText,
    selectNested,
    registerThemeHomepageTour,
} from "@website/js/tours/tour_utils";
import { _t } from "@web/core/l10n/translation";

registerThemeHomepageTour("configurator_tour", () => {
    let titleSelector = "#wrap > section:first-child";
    let titleContainer = document.querySelector(titleSelector);
    let title = titleContainer?.querySelector("h1, h2");
    if (!title) {
        titleSelector = titleSelector.replace("section:first-child", "section:nth-child(2)");
        titleContainer = document.querySelector(titleSelector);
        title = titleContainer?.querySelector("h1, h2");
    }

    const isTitleTextImage = titleContainer?.classList.contains("s_text_image");
    titleSelector = titleSelector + ` ${title?.tagName === "H1" ? "h1" : "h2"}`;

    const shapeSelector = "#wrap > section[data-oe-shape-data]";
    const backgroundSelector = "#wrap > section:nth-child(2)";

    const imageStep = isTitleTextImage
        ? changeImage(titleSelector.replace("h2", "img"))
        : changeBackground();

    const backgroundColorStep = [changeBackgroundColor()];
    if (!isTitleTextImage) {
        backgroundColorStep.unshift(...clickOnSnippet(backgroundSelector));
    }

    const shapeStep = [];
    const shapeEl = document.querySelector(shapeSelector);
    if (shapeEl) {
        if (document.querySelector(backgroundSelector) !== shapeEl) {
            shapeStep.push(...clickOnSnippet(shapeSelector));
        }
        shapeStep.push(changeOption("BackgroundShape", "we-toggler", _t("Background Shape")));
        shapeStep.push(
            selectNested(
                "we-select-page",
                "BackgroundShape",
                ":not(.o_we_pager_controls)",
                _t("Background Shape")
            )
        );
    }

    return [
        ...clickOnText(titleSelector),
        ...imageStep,
        ...backgroundColorStep,
        ...shapeStep,
        changePaddingSize("top"),
    ];
});
