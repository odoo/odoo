import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
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
        this.root = undefined;
        onWillStart(async () => {
            this.styleSheets = await this.props.styleSheetsPromise;
        });
        useEffect(
            () => {
                if (!this.root) {
                    this.setupShadowRoot();
                } else {
                    this.root.replaceChildren(this.renderBodyContent());
                }
            },
            () => [this.props.template]
        );
    }

    setupShadowRoot() {
        this.root = this.shadowRootRef.el.attachShadow({ mode: "open" });
        this.root.adoptedStyleSheets = [...this.root.adoptedStyleSheets, ...this.styleSheets];
        this.root.replaceChildren(this.renderBodyContent());
    }

    renderBodyContent() {
        return renderToFragment("mass_mailing.FavoritePreviewBody", {
            ...this.props.template,
            isRTL: this.isRTL,
        });
    }
}
