import {
    Component,
    onMounted,
    signal,
    t,
    useOnChange,
    usePlugin,
    useProps,
    useScope,
} from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { renderToFragment } from "@web/core/utils/render";
import { StyleSheetPlugin } from "../../views/mailing_template_kanban_view/stylesheets_plugin";
import { registry } from "@web/core/registry";

/**
 * A widget to display the mailing template's HTML content
 * inside an isolated shadowRoot, with its own stylesheets.
 */
export class TemplatePreviewField extends Component {
    static template = "mass_mailing.TemplatePreviewField";

    props = useProps({ record: t.object().optional(), template: t.object().optional() });
    shadowRootRef = signal.ref();
    rootWrapperRef = signal.ref();

    setup() {
        const styleSheetsPlugin = usePlugin(StyleSheetPlugin);
        const scope = useScope();
        onMounted(() => {
            Promise.all(styleSheetsPlugin.promises).then((styleSheetsArray) => {
                if (scope.isDestroyed()) {
                    return;
                }
                this.setupShadowRoot(styleSheetsArray.flat());
            });
        });
        useOnChange(
            () => [this.props.template?.bodyArch, this.props.record?.data.body_arch],
            (templateArch, recordArch) => {
                if (!this.root) {
                    return;
                }
                const source = this.props.template ? "template" : "record";
                const bodyArch = (this.props.template ? templateArch : recordArch) ?? "";
                this.root.replaceChildren(this.renderBodyContent({ source, bodyArch }));
            }
        );
    }

    setupShadowRoot(styleSheets) {
        this.root = this.shadowRootRef().attachShadow({ mode: "open" });
        this.root.adoptedStyleSheets = [...this.root.adoptedStyleSheets, ...styleSheets];
        const source = this.props.template ? "template" : "record";
        const bodyArch =
            (this.props.template
                ? this.props.template.bodyArch
                : this.props.record?.data.body_arch) ?? "";
        this.root.replaceChildren(this.renderBodyContent({ source, bodyArch }));
    }

    renderBodyContent({ source, bodyArch }) {
        return renderToFragment("mass_mailing.TemplatePreviewBody", {
            bodyArch,
            isRTL: localization.direction === "rtl",
            source,
        });
    }
}

export const templatePreviewField = {
    component: TemplatePreviewField,
};

registry.category("fields").add("mailing_template_preview_field", templatePreviewField);
