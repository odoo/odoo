import { Component, onMounted, onPatched, onWillStart, signal } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { renderToFragment } from "@web/core/utils/render";

export class FavoritePreview extends Component {
    static template = "mass_mailing.FavoritePreview";
    static props = {
        template: Object,
        styleSheetsPromise: Promise,
    };

    shadowRootRef = signal(null);

    setup() {
        this.isRTL = localization.direction === "rtl";
        this.styleSheets = [];
        this.root = undefined;
        onWillStart(async () => {
            this.styleSheets = await this.props.styleSheetsPromise;
        });
        let template;
        onMounted(() => {
            this.setupShadowRoot();
            template = this.props.template;
        });
        onPatched(() => {
            if (this.props.template !== template) {
                template = this.props.template;
                this.root.replaceChildren(this.renderBodyContent());
            }
        });
    }

    setupShadowRoot() {
        this.root = this.shadowRootRef().attachShadow({ mode: "open" });
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
