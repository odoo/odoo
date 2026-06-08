import { DIMENSIONS, useEmailHtmlConverter } from "@mail/convert_inline/hooks";
import { loadIframe, loadIframeBundles } from "@mail/convert_inline/iframe_utils";
import { useRef, useState } from "@web/owl2/utils";
import { Component, onMounted } from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { renderToElement, renderToFragment } from "@web/core/utils/render";

const { DESKTOP, MOBILE } = DIMENSIONS;

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
            height: DESKTOP.height,
            width: DESKTOP.width,
            displayWidth: DESKTOP.width,
        });
        const { updateLayoutDimensions, convertToEmailHtml } = useEmailHtmlConverter({
            Plugins: [
                ...registry.category("mail-html-conversion-core-plugins").getAll(),
                ...registry.category("mail-html-conversion-main-plugins").getAll(),
                ...registry.category("mass-mailing-html-conversion-plugins").getAll(),
            ],
            bundles: ["mass_mailing.assets_iframe_style"],
            services: this.env.services,
            targetRef: useRef("referenceIframe"),
            isVisible: true,
        });
        this.updateConverterLayoutDimensions = updateLayoutDimensions;

        onMounted(() => {
            const iframe = this.outputIframeRef.el;
            const promises = [
                loadIframe(iframe, () => {
                    iframe.contentDocument.head.append(
                        renderToFragment("mail.EmailHtmlConverterHead")
                    );
                    return loadIframeBundles(iframe, ["mass_mailing.assets_mail_clients"]);
                }),
            ];
            Promise.all(promises).then(async () => {
                const referenceElement = renderToElement("mail.EmailHtmlConverterReference");
                referenceElement.innerHTML = await convertToEmailHtml(this.props.fragment);
                iframe.contentDocument.body.append(referenceElement);
            });
        });
    }

    get stepRange() {
        return 5;
    }

    get minRange() {
        return MOBILE.width;
    }

    get maxRange() {
        return DESKTOP.width;
    }

    isBrowserSafari() {
        return isBrowserSafari();
    }

    onRangeChange(ev) {
        this.state.width = ev.target.value;
        this.updateConverterLayoutDimensions(this.state);
    }

    onRangeInput(ev) {
        this.state.displayWidth = ev.target.value;
    }

    updateLayoutDimensions(isMobile = false) {
        Object.assign(this.state, isMobile ? MOBILE : DESKTOP);
        this.updateConverterLayoutDimensions(isMobile ? MOBILE : DESKTOP);
        this.state.displayWidth = this.state.width;
        this.state.isMobile = isMobile;
    }
}
