import { Component, onMounted, onWillStart, useRef } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { renderToFragment } from "@web/core/utils/render";

export class FavoritePreview extends Component {
    static template = "mass_mailing.FavoritePreview";
    static props = {
        template: Object,
        styleSheetsPromise: Promise,
    };

    setup() {
        this.isRTL = localization.direction === "rtl";
        this.shadowRootRef = useRef("shadowRoot");
        this.styleSheets = [];
        onWillStart(async () => {
            this.styleSheets = await this.props.styleSheetsPromise;
        });
        onMounted(() => {
            this.setupShadowRoot();
        });
    }

    setupShadowRoot() {
        const root = this.shadowRootRef.el.attachShadow({ mode: "open" });
        root.adoptedStyleSheets = [...root.adoptedStyleSheets, ...this.styleSheets];
        root.replaceChildren(this.renderBodyContent());
    }

    renderBodyContent() {
        return renderToFragment("mass_mailing.FavoritePreviewBody", {
            ...this.props.template,
            isRTL: this.isRTL,
        });
    }
}
