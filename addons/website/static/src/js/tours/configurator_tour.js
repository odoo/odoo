/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";
import { _t } from "@web/core/l10n/translation";

wTourUtils.registerThemeHomepageTour('configurator_tour', () => {
    const iframeDocument = document.querySelector(".o_iframe").contentDocument;
    let titleSelector = "#wrap > section:first-child";
    let title = iframeDocument.querySelector(titleSelector).querySelector("h1, h2");
    if (!(title instanceof Node)) {
        titleSelector = titleSelector.replace("section:first-child", "section:nth-child(2)");
        title = iframeDocument.querySelector(titleSelector).querySelector("h1, h2");
    }
    const isTitleTextImage = iframeDocument
        .querySelector(titleSelector)
        .classList.contains("s_text_image");
    titleSelector = titleSelector.concat(` ${title.matches('h1') ? 'h1' : 'h2'}`);

    const shapeSelector = '#wrap > section[data-oe-shape-data]';
    const backgroundSelector = '#wrap > section:nth-child(2)';

    const imageStep = isTitleTextImage ?
        wTourUtils.changeImage(titleSelector.replace('h2', 'img')) : wTourUtils.changeBackground();

    const backgroundColorStep = [wTourUtils.changeBackgroundColor()];
    if (!isTitleTextImage) {
        backgroundColorStep.unshift(...wTourUtils.clickOnSnippet(backgroundSelector));
    }

    const shapeStep = [];
    if (iframeDocument.querySelector(shapeSelector)) {
        if (!$(backgroundSelector).is($(shapeSelector))) {
            shapeStep.push(...wTourUtils.clickOnSnippet(shapeSelector));
        }
        shapeStep.push(wTourUtils.changeOption('BackgroundShape', 'we-toggler', _t('Background Shape')));
        shapeStep.push(wTourUtils.selectNested('we-select-page', 'BackgroundShape', ':not(.o_we_pager_controls)', _t('Background Shape')));
    }

    return [
        ...wTourUtils.clickOnText(titleSelector),
        ...imageStep,
        ...backgroundColorStep,
        ...shapeStep,
        wTourUtils.changePaddingSize('top'),
    ];
});
