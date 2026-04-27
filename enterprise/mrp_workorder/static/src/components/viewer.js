/** @odoo-module **/

import { getGoogleSlideUrl } from "@mrp/views/fields/google_slides_viewer";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { fileTypeMagicWordMap } from "@web/views/fields/image/image_field";
import { Component, useEffect, useRef } from "@odoo/owl";

class DocumentViewer extends Component {
    static template = "mrp_workorder.DocumentViewer";
    static props = ["resField", "resModel", "resId", "value", "page"];

    setup() {
        this.notification = useService("notification");
        this.magicNumbers = {
            'JVBER': 'pdf',
            ...fileTypeMagicWordMap,
        };
        this.pdfIFrame = useRef('pdf_viewer');
        this.slideIFrame = useRef('slide_viewer');
        useEffect(() => {
            this.updatePdf();
        });
    }

    updatePdf() {
        if (this.pdfIFrame.el) {
            const iframe = this.pdfIFrame.el.firstElementChild;
            iframe.removeAttribute('style');
            // Once the PDF viewer is loaded, hides everything except the page.
            iframe.addEventListener("load", () => {
                iframe.contentDocument.querySelector("body").style.background = "none";
                iframe.contentDocument.querySelector("#viewerContainer").style.boxShadow = "none";
            });
        }
    }

    onLoadFailed() {
        this.notification.add(_t("Could not display the selected %s", this.type), {
            type: "danger",
        });
    }

    get type() {
        if (!this.props || !this.props.value) {
            return false;
        }
        if (this.props.resField === "worksheet_url" || this.props.resField === "worksheet_google_slide") {
            return "google_slide";
        }
        for (const [magicNumber, type] of Object.entries(this.magicNumbers)) {
            if (this.props.value.startsWith(magicNumber)) {
                return type;
            }
        }
        return false;
    }

    get urlPdf() {
        const page = this.props.page || 1;
        const file = encodeURIComponent(
            url("/web/content", {
                model: this.props.resModel,
                field: this.props.resField,
                id: this.props.resId,
            })
        );
        return `/web/static/lib/pdfjs/web/viewer.html?file=${file}#page=${page}`;
    }

    get urlSlide() {
        return getGoogleSlideUrl(this.props.value, this.props.page);
    }

    get urlImage() {
        return url("/web/image", {
            model: this.props.resModel,
            id: this.props.resId,
            field: this.props.resField,
        });
    }
}

export default DocumentViewer;
