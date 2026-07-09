import { Component, onMounted, onPatched, onWillStart, signal } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { convertCSSColorToRgba } from "@web/core/utils/colors";
import { renderToFragment } from "@web/core/utils/render";

export class TemplatePreview extends Component {
    static template = "mass_mailing.TemplatePreview";
    static props = {
        template: Object,
        styleSheetsPromise: Promise,
    };

    shadowRootRef = signal.ref();
    rootWrapperRef = signal.ref();

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
            this.setupBackgroundColor();
        });
    }

    /**
     * Set the background color of the preview to be
     * the same as the mailing's background color.
     */
    setupBackgroundColor() {
        const layoutNode = this.root.querySelector(".o_layout");
        const computedBgColor = getComputedStyle(layoutNode).backgroundColor;
        const layoutBgColor = layoutNode.style.backgroundColor || computedBgColor;
        if (layoutBgColor) {
            const opacity = convertCSSColorToRgba(layoutBgColor)?.opacity;
            if (opacity === 0) {
                this.rootWrapperRef().style.backgroundColor = "#FFFFFF";
            } else {
                this.rootWrapperRef().style.backgroundColor = layoutBgColor;
            }
        }
    }

    setupShadowRoot() {
        this.root = this.shadowRootRef().attachShadow({ mode: "open" });
        this.root.adoptedStyleSheets = [...this.root.adoptedStyleSheets, ...this.styleSheets];
        this.root.replaceChildren(this.renderBodyContent());
        this.setupBackgroundColor();
    }

    renderBodyContent() {
        return renderToFragment("mass_mailing.TemplatePreviewBody", {
            ...this.props.template,
            isRTL: this.isRTL,
        });
    }
}
