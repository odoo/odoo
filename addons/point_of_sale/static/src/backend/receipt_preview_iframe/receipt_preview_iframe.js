import { App, Component, useEffect, useRef, xml } from "@odoo/owl";
import { LazyComponent } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { getTemplate } from "@web/core/templates";
import { _t } from "@web/core/l10n/translation";

/**
 * This component renders a preview of the receipt in the configuration wizard.
 * On the first render, it injects the HTML content into the iframe and ensures all required assets are properly loaded.
 * On subsequent updates, it re-mounts the receipt component with the latest props whenever they change.
 */
export class ReceiptPreview extends Component {
    static template = xml`
        <div class="o_receipt_preview_iframe_wrapper">
            <iframe t-ref="iframeRef" sandbox="allow-scripts allow-same-origin" style="width: 360px; height: 650px"/>
        </div>
    `;

    setup() {
        this.iframeRef = useRef("iframeRef");
        this.isLoading = false;
        useEffect(
            (value) => {
                if (!this.wrapwrapEl) {
                    this._loadHtmlIntoIframe(value);
                } else if (!this.props.record.data["write_date"]) {
                    this._mountReceiptComponent(value);
                }
            },
            () => [this.props.record.data[this.props.name]]
        );
    }

    get wrapwrapEl() {
        return this.iframeRef.el.contentDocument.getElementById("wrapwrap");
    }

    _loadHtmlIntoIframe(value) {
        const iframeDoc = this.iframeRef.el.contentDocument;

        // Initialize iframe with HTML content only once
        iframeDoc.open();
        iframeDoc.write(value);
        iframeDoc.close();

        // Load the receipt component once the iframe finishes loading html
        this.iframeRef.el.addEventListener("load", () => {
            this._mountReceiptComponent(value, true);
        });
    }

    _mountReceiptComponent(value, isFirstMount = false) {
        if (!this.wrapwrapEl || this.isLoading) {
            return;
        }
        this.isLoading = true;

        // Extract component props from the raw HTML content.
        const el = new DOMParser()
            .parseFromString(value, "text/html")
            .querySelector("receipt-component");
        const props = JSON.parse(el?.getAttribute("props") || "{}");

        // Mount the LazyComponent, which will lazily load the OrderReceipt component.
        // Using LazyComponent prevents loading all OrderReceipt component assets in the `assets_backend` bundle upfront.
        const app = new App(LazyComponent, {
            getTemplate,
            props: {
                bundle: "point_of_sale.receipt_assets_lazy",
                Component: "OrderReceipt",
                props: props,
            },
            translateFn: _t,
        });
        this.wrapwrapEl.innerHTML = "";
        app.mount(this.wrapwrapEl);
        app.root.mounted.push(() => {
            this.isLoading = false;
            if (isFirstMount) {
                // Hide the loader once the component has been mounted
                document.querySelector(".receipt_preview_spinner")?.classList.add("d-none");
            }
        });
    }
}

export const receiptPreview = {
    component: ReceiptPreview,
    displayName: "POS Receipt Preview",
    supportedTypes: ["text", "html"],
};

registry.category("fields").add("receipt_preview_iframe", receiptPreview);
