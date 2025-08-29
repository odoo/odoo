import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { renderToFragment } from "@web/core/utils/render";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, status, useState, useEffect, useRef } from "@odoo/owl";

export class MailingPreviewIframe extends Component {
    static template = "mass_mailing.MailingPreviewIframe";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState(this.env.displayState);
        this.ui = useService("ui");
        this.iframeRef = useRef("iframeRef");
        this.iframeLoaded = Promise.withResolvers();

        onMounted(() => {
            if (this.iframeRef.el.contentDocument?.readyState === "complete") {
                this.onIframeLoaded();
            } else {
                this.iframeRef.el.addEventListener("load", () => this.onIframeLoaded(), {
                    once: true,
                });
            }
        });

        useEffect(
            () => {
                this.iframeLoaded.promise.then(() => {
                    this.iframeRef.el?.contentDocument.body.replaceChildren(
                        this.renderBodyContent()
                    );
                });
            },
            () => [this.props.record.data.preview_record_ref]
        );

        useEffect(
            () => {
                this.iframeLoaded.promise.then(() => {
                    this.throttledResize();
                });
            },
            () => [this.state.isMobileMode]
        );

        useBus(this.ui.bus, "resize", () => {
            this.iframeLoaded.promise.then(() => {
                this.throttledResize();
            });
        });

        const updateIframeSize = () => {
            const iframe = this.iframeRef.el;
            if (this.state.isMobileMode) {
                // same styling for mobile as we have in 'mass_mailing_iframe'
                iframe.style.width = "367px";
                iframe.style.height = "668px";
                iframe.style.transform = "";
                iframe.contentDocument.body.scrollTop = 0;
            } else {
                iframe.style.width = "140%";
                iframe.style.height = "140%";
                iframe.style.transform = `scale(${10 / 14})`;
                iframe.style.transformOrigin = "top left"
            }
        };

        this.throttledResize = useThrottleForAnimation(() => {
            if (status(this) === "destroyed") {
                return;
            }
            updateIframeSize();
        });
    }

    renderHeadContent() {
        return renderToFragment("mass_mailing.IframeHead", this);
    }

    renderBodyContent() {
        return renderToFragment("mass_mailing.MailingPreviewIframeBody", this);
    }

    onIframeLoaded() {
        if (status(this) === "destroyed") {
            return;
        }
        this.iframeRef.el?.contentDocument.head.appendChild(this.renderHeadContent());
        this.iframeRef.el?.contentDocument.body.appendChild(this.renderBodyContent());
        this.iframeLoaded.resolve();
    }

    get isBrowserSafari() {
        return isBrowserSafari();
    }
}

export const mailingPreviewIframe = {
    component: MailingPreviewIframe,
    supportedTypes: ["html"],
};

/**
 * Note: This field does not support switching to another record (e.g. navigation in a standard form view).
 * It is designed for use in wizards where the record remains constant.
 */
registry.category("fields").add("mailing_preview_iframe", mailingPreviewIframe);
