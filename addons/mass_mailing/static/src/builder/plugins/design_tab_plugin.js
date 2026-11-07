import { HighlightThemeRowPlugin } from "@html_builder/sidebar/highlight_theme_row_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { FontFamilyPicker } from "../fontfamily_picker";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";

export const OPTION_POSITIONS = {
    BODY: 10,
    SETTINGS: 20,
    PARAGRAPH: 30,
    HEADINGS: 40,
    BUTTON: 50,
    LINK: 60,
    SEPARATORS: 70,
};

class DesignButtonOption extends BaseOptionComponent {
    setup() {
        super.setup();
        this.highlightThemeRow = usePlugin(HighlightThemeRowPlugin);
    }
}

export class DesignTabPlugin extends Plugin {
    static id = "mass_mailing.DesignTab";
    static dependencies = ["builderActions"];
    resources = {
        builder_components: {
            FontFamilyPicker,
        },
        design_options: [
            withSequence(
                OPTION_POSITIONS.BODY,
                this.getDesignOptionBlock("design-body", {
                    template: "mass_mailing.DesignBodyOption",
                    title: _t("Mailing"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.HEADINGS,
                this.getDesignOptionBlock("design-headings", {
                    template: "mass_mailing.DesignHeadingsOption",
                    title: _t("Heading"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.PARAGRAPH,
                this.getDesignOptionBlock("design-paragraph", {
                    template: "mass_mailing.DesignParagraphOption",
                    title: _t("Paragraph"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.BUTTON,
                this.getDesignOptionBlock("design-button", {
                    template: "mass_mailing.DesignButtonOption",
                    title: _t("Button"),
                    OptionClass: DesignButtonOption,
                })
            ),
            withSequence(
                OPTION_POSITIONS.LINK,
                this.getDesignOptionBlock("design-link", {
                    template: "mass_mailing.DesignLinkOption",
                    title: _t("Link"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.SEPARATORS,
                this.getDesignOptionBlock("design-separators", {
                    template: "mass_mailing.DesignSeparatorOption",
                    title: _t("Separator"),
                })
            ),
        ],
    };

    getDesignOptionBlock(id, { OptionClass = BaseOptionComponent, ...options }) {
        const Option = class extends OptionClass {
            static selector = "*";
        };
        Object.assign(Option, options);

        return {
            id: id,
            element: this.editable,
            hasOverlayOptions: false,
            headerMiddleButton: false,
            isClonable: false,
            isRemovable: false,
            options: [Option],
            optionsContainerTopButtons: [],
        };
    }
}

registry.category("mass_mailing-plugins").add(DesignTabPlugin.id, DesignTabPlugin);
