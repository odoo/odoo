import {
    EMAIL_MOBILE_DIMENSIONS,
    EMAIL_DESKTOP_DIMENSIONS,
    useEmailHtmlConverter,
} from "@mail/convert_inline/hooks";
import { loadIframe, loadIframeBundles } from "@mail/convert_inline/iframe_utils";
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/core/dialog/dialog";
import { renderToFragment } from "@web/core/utils/render";

export class DebugConvertInlineDialog extends Component {
    static template = "test_convert_inline.DebugConvertInlineDialog";
    static props = {
        fragment: { type: DocumentFragment },
        close: Function,
    };
    static components = {
        Dialog,
    };

    setup() {
        this.outputIframeRef = useRef("outputIframe");
        this.state = useState({
            isMobile: false,
            height: EMAIL_DESKTOP_DIMENSIONS.height,
            width: EMAIL_DESKTOP_DIMENSIONS.width,
        });
        const { updateLayoutDimensions, convertToEmailHtml } = useEmailHtmlConverter({
            bundles: [
                "mass_mailing.assets_iframe_style",
                "mass_mailing.assets_email_html_conversion",
            ],
            targetRef: useRef("referenceIframe"),
            isVisible: true,
        });
        this.updateConverterLayoutDimensions = updateLayoutDimensions;

        onMounted(() => {
            const iframe = this.outputIframeRef.el;
            const promises = [
                loadIframeBundles(iframe, ["mass_mailing.assets_email_html_conversion"]),
                loadIframe(iframe, () => {
                    iframe.contentDocument.head.append(
                        renderToFragment("mail.EmailHtmlConverterHead")
                    );
                }),
            ];
            Promise.all(promises).then(async () => {
                iframe.contentDocument.body.innerHTML = await convertToEmailHtml(
                    this.props.fragment
                );
            });
        });
    }

    isBrowserSafari() {
        return isBrowserSafari();
    }

    updateLayoutDimensions(isMobile = false) {
        Object.assign(this.state, isMobile ? EMAIL_MOBILE_DIMENSIONS : EMAIL_DESKTOP_DIMENSIONS);
        this.updateConverterLayoutDimensions(
            isMobile ? EMAIL_MOBILE_DIMENSIONS : EMAIL_DESKTOP_DIMENSIONS
        );
        this.state.isMobile = isMobile;
    }
}
