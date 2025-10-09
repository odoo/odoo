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
    let title = $(titleSelector).find("h1, h2").first();
    if (!title.length) {
        titleSelector = titleSelector.replace("section:first-child", "section:nth-child(2)");
        title = $(titleSelector).find("h1, h2").first();
    }

    const isTitleTextImage = $(titleSelector).hasClass("s_text_image");
    titleSelector = titleSelector.concat(` ${title.is("h1") ? "h1" : "h2"}`);

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
    if ($(shapeSelector).first().length) {
        if (!$(backgroundSelector).is($(shapeSelector))) {
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
