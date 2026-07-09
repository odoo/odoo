import { Component, markup, onMounted, signal, usePlugin, useScope } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { renderToFragment } from "@web/core/utils/render";
import { StylesheetsPlugin } from "../../views/mailing_template_kanban_view/stylesheets_plugin";
import { convertCSSColorToRgba } from "@web/core/utils/colors";

/**
 * A widget to display the mailing template's HTML content
 * inside an isolated shadowRoot, with its own stylesheets.
 */
export class MailingTemplateKanbanCard extends Component {
    static template = "mass_mailing.MailingTemplateKanbanCard";

    shadowRootRef = signal.ref();
    rootWrapperRef = signal.ref();

    setup() {
        this.scope = useScope();
        this.isRTL = localization.direction === "rtl";
        this.allStyleSheets = [];
        const stylesheets = usePlugin(StylesheetsPlugin);
        onMounted(() => {
            Promise.all([stylesheets.iframePromise, stylesheets.cardPromise]).then(
                ([iframeStyleSheets, cardStyleSheets]) => {
                    if (this.scope.isDestroyed()) {
                        return;
                    }
                    this.allStyleSheets = [...iframeStyleSheets, ...cardStyleSheets];
                    this.setupShadowRoot();
                }
            );
        });
    }

    /**
     * Set the background color of the card to be the same as the mailing's layout color.
     *
     * If the layout has no background color (opacity = 0), the card should take the mailing color.
     *
     * @param {HTMLElement} root the root element, in which the mailing body is rendered
     * @param {HTMLElement} wrapperEl the root's wrapper element
     */
    setupBackgroundColor(root, wrapperEl) {
        const layoutNode = root.querySelector(".o_layout");
        const computedBgColor = getComputedStyle(layoutNode).backgroundColor;
        const layoutBgColor = layoutNode?.style.backgroundColor || computedBgColor;
        if (layoutBgColor) {
            const opacity = convertCSSColorToRgba(layoutBgColor)?.opacity;
            if (opacity === 0) {
                wrapperEl.style.backgroundColor = "#FFFFFF";
            }
        }
    }

    setupShadowRoot() {
        const root = this.shadowRootRef().attachShadow({ mode: "open" });
        const win = this.shadowRootRef().ownerDocument.defaultView;
        this.customStyleSheet = new win.CSSStyleSheet();
        root.adoptedStyleSheets = [...root.adoptedStyleSheets, ...this.allStyleSheets];
        root.replaceChildren(this.renderBodyContent());
        this.setupBackgroundColor(root, this.rootWrapperRef());
    }

    renderBodyContent() {
        return renderToFragment("mass_mailing.TemplateKanbanCardPreviewBody", {
            bodyArch: markup(this.props.record.data.body_arch),
            isRTL: this.isRTL,
        });
    }
}

export const mailingTemplateKanban = {
    component: MailingTemplateKanbanCard,
};

registry.category("fields").add("mailing_template_kanban_card", mailingTemplateKanban);
