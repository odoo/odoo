/** @odoo-module */
import { Component, useRef, useState } from "@odoo/owl";
import { getCssFromPaperFormat } from "@web_studio/client_action/report_editor/utils";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { ErrorDisplay } from "@web_studio/client_action/report_editor/error_display";

export class ReportEditorIframe extends Component {
    static components = { ErrorDisplay };
    static template = "web_studio.ReportEditor.Iframe";
    static props = {
        iframeKey: String,
        iframeSource: String,
        onIframeLoaded: Function,
    };

    setup() {
        this.reportEditorModel = useState(this.env.reportEditorModel);
        this.iframeRef = useRef("iframeRef");
        this.onContainerScroll = useThrottleForAnimation(() => {
            if (this.iframeRef.el?.contentDocument) {
                this.iframeRef.el.contentDocument.dispatchEvent(new Event("scroll"));
            }
        });
    }

    get paperFormatStyle() {
        const {
            margin_top,
            margin_left,
            margin_right,
            print_page_height,
            print_page_width,
            header_spacing,
        } = this.reportEditorModel.paperFormat;
        const marginTop = Math.max(0, (margin_top || 0) - (header_spacing || 0));
        return getCssFromPaperFormat({
            margin_top: marginTop,
            margin_left,
            margin_right,
            print_page_height,
            print_page_width,
        });
    }
    get iframeStyle() {
        const { print_page_height } = this.reportEditorModel.paperFormat;
        return getCssFromPaperFormat({ print_page_height });
    }

    get iframeSource() {
        return this.props.iframeSource;
    }

    get iframeKey() {
        return this.reportEditorModel.renderKey + "_" + (this.props.iframeKey || "");
    }

    async onIframeLoaded() {
        await this.resizeIframeContent({ iframeRef: this.iframeRef });
        this.props.onIframeLoaded({ iframeRef: this.iframeRef });
    }

    async resizeIframeContent({ iframeRef }) {
        const paperFormat = this.reportEditorModel.paperFormat;
        const iframeEl = iframeRef.el;
        const iframeContent = iframeEl.contentDocument;

        // zoom content from 96 (default browser DPI) to paperformat DPI
        const zoom = 96 / paperFormat.dpi;
        Array.from(iframeContent.querySelector("main")?.children || []).forEach((el) => {
            let sectionZoom = zoom;
            if (!paperFormat.disable_shrinking) {
                const { width } = el.getBoundingClientRect();
                sectionZoom = Math.min(zoom, width / el.scrollWidth);
            }
            el.setAttribute("oe-origin-style", el.getAttribute("style") || "");
            el.style.setProperty("zoom", sectionZoom);
        });
        // WHY --> so that after the load of the iframe, if there are images,
        // the iframe height is recomputed to the height of the content images included
        const computeIframeHeight = () =>
            (iframeEl.style.height = iframeContent.body.scrollHeight + "px");
        //computeIframeHeight();

        // TODO: it seems that the paperformat doesn't exactly do that
        // this.$content.find('.header').css({
        //     'margin-bottom': (this.paperFormat.header_spacing || 0) + 'mm',
        // });
        // TODO: won't be pretty if the content is larger than the format

        const footer = iframeContent.querySelector(".footer");
        const footerStyle = footer?.style;
        if (footerStyle) {
            const { width } = iframeContent.querySelector(".page")?.getBoundingClientRect() || {};
            if (!footer.hasAttribute("oe-origin-style")) {
                footer.setAttribute("oe-origin-style", footer.getAttribute("style") || "");
            }
            if (width) {
                footerStyle.setProperty("width", `${width}px`);
            }
        }

        iframeContent.querySelector("html").style.overflow = "hidden";

        // set the size of the iframe
        const proms = [];
        Array.from(iframeContent.querySelectorAll("img[src]") || []).forEach((img) => {
            if (img.complete) {
                return;
            }
            const prom = new Promise((resolve) => {
                img.onload = resolve;
            });
            proms.push(prom);
        });
        await Promise.all(proms);
        computeIframeHeight();
    }
}
