/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getGoogleSlideUrl, googleSlideViewer, GoogleSlideViewer } from "@web/views/fields/google_slide_viewer/google_slide_viewer";

export { getGoogleSlideUrl };

export class SlidesViewer extends GoogleSlideViewer {
    static template = "mrp.SlidesViewer";
}

export const slidesViewer = {
    ...googleSlideViewer,
    component: SlidesViewer,
    additionalClasses: ["o_field_google_slide_viewer"],
}

registry.category("fields").add("embed_viewer", slidesViewer, { force: true });
