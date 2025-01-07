import { registry } from "@web/core/registry";
import { getTemplate } from "@web/core/templates";
import { App, Component, useEffect, useRef, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

/**
 * This component renders a preview of the receipt in the configuration wizard.
 * On the first render, it injects the HTML content into the iframe and ensures all required assets are properly loaded.
 * On subsequent updates, it re-mounts the receipt component with the latest props whenever they change.
 */
export class ReceiptPreview extends Component {
    static template = xml`
        <div class="o_receipt_preview_iframe_wrapper">
            <iframe t-ref="iframeRef" sandbox="allow-scripts allow-same-origin" style="width: 350px; height: 650px"/>
        </div>
    `;

    setup() {
        this.iframeRef = useRef("iframeRef");
        this.isLoading = false;
        useEffect(
            (value) => {
                const iframeDoc = this.iframeRef.el.contentDocument;
                const wrapwrap = iframeDoc.getElementById("wrapwrap");
                if (!wrapwrap) {
                    // Initialize iframe with HTML content only once
                    iframeDoc.open();
                    iframeDoc.write(value);
                    iframeDoc.close();

                    // Load the receipt component once the iframe finishes loading html
                    this.iframeRef.el.addEventListener("load", () => {
                        this.mountReceiptComponent(value, iframeDoc.getElementById("wrapwrap"));
                        // Hide the loader once the component has been mounted
                        document.querySelector(".receipt_preview_spinner")?.classList.add("d-none");
                    });
                } else if (!this.props.record.data["write_date"]) {
                    this.mountReceiptComponent(value, wrapwrap);
                }
            },
            () => [this.props.record.data[this.props.name]]
        );
    }

    getComponentProps(value) {
        // Extract component props from the raw HTML content.
        const el = new DOMParser()
            .parseFromString(value, "text/html")
            .querySelector("receipt-component");
        return JSON.parse(el?.getAttribute("props") || "{}");
    }

    mountReceiptComponent(value, wrapwrapEl) {
        if (!wrapwrapEl || this.isLoading) {
            return;
        }
        this.isLoading = true;

        // Mount OrderReceipt component in element
        const app = new App(OrderReceipt, {
            getTemplate,
            props: this.getComponentProps(value),
            translateFn: _t,
        });
        wrapwrapEl.innerHTML = "";
        app.mount(wrapwrapEl);
        app.root.mounted.push(() => {
            this.isLoading = false;
        });
    }
}

export const receiptPreview = {
    component: ReceiptPreview,
    displayName: _t("Wrap raw html within an iframe"),
    supportedTypes: ["text", "html"],
};

registry.category("fields").add("receipt_preview_iframe", receiptPreview);
