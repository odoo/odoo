/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    clickOnEditAndWaitEditMode,
    registerWebsitePreviewTour
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("generic_website_editor", {
    edition: true,
}, () => [{
    trigger: ':iframe body:not([data-hello="world"])',
    content: 'Check that the editor DOM matches its website-generic features',
}]);

// Good practice would have been to use `registerWebsitePreviewTour`
// for this tour with `edition: true` and remove the first step to enter edit
// mode. Unfortunately this breaks the page and therefore the test fails for
// unknown reason.
registry.category("web_tour.tours").add('specific_website_editor', {
    steps: () => [
    ...clickOnEditAndWaitEditMode(),
{
    trigger: ':iframe body[data-hello="world"]',
    content: 'Check that the editor DOM matches its website-specific features',
}]});
