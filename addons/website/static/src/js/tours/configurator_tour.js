/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";
import { _t } from "@web/core/l10n/translation";

wTourUtils.registerThemeHomepageTour('configurator_tour', () => {

    let titleSelector = '#wrap > section:first-child';
    let title = $(titleSelector).find('h1, h2').first();
    if (!title.length) {
        titleSelector = titleSelector.replace('section:first-child', 'section:nth-child(2)');
        title = $(titleSelector).find('h1, h2').first();
    }
    let isTitleTextImage = $(titleSelector).hasClass('s_text_image');
    titleSelector = titleSelector.concat(` ${title.is('h1') ? 'h1' : 'h2'}`);

    const shapeSelector = '#wrap > section[data-oe-shape-data]';
    const backgroundSelector = '#wrap > section:nth-child(2)';

    const imageStep = isTitleTextImage ?
        wTourUtils.changeImage(titleSelector.replace('h2', 'img')) : wTourUtils.changeBackground();

    const backgroundColorStep = [wTourUtils.changeBackgroundColor()];
    if (!isTitleTextImage) {
        backgroundColorStep.unshift(wTourUtils.clickOnSnippet(backgroundSelector));
    }

    const shapeStep = [];
    if ($(shapeSelector).first().length) {
        if (!$(backgroundSelector).is($(shapeSelector))) {
            shapeStep.push(wTourUtils.clickOnSnippet(shapeSelector));
        }
        shapeStep.push(wTourUtils.changeOption('BackgroundShape', 'we-toggler', _t('Background Shape')));
        shapeStep.push(wTourUtils.selectNested('we-select-page', 'BackgroundShape', ':not(.o_we_pager_controls)', _t('Background Shape')));
    }

    return [
        wTourUtils.clickOnText(titleSelector),
        imageStep,
        ...backgroundColorStep,
        ...shapeStep,
        wTourUtils.changePaddingSize('top'),
    ];
});
