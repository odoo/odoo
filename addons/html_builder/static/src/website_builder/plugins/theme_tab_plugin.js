import { BuilderFontFamilyPicker } from "@html_builder/website_builder/builder_fontfamilypicker";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class ThemeTabPlugin extends Plugin {
    static id = "themeTab";
    resources = {
        builder_components: { BuilderFontFamilyPicker },
        theme_options: [
            withSequence(
                10,
                this.getThemeOptionBlock(
                    "theme-colors",
                    _t("Colors"),
                    "html_builder.ThemeColorsOption"
                )
            ),
            withSequence(
                20,
                this.getThemeOptionBlock(
                    "website-settings",
                    _t("Website"),
                    "html_builder.ThemeWebsiteSettingsOption"
                )
            ),
            withSequence(
                30,
                this.getThemeOptionBlock(
                    "theme-paragraph",
                    _t("Paragraph"),
                    "html_builder.ThemeParagraphOption"
                )
            ),
            withSequence(
                40,
                this.getThemeOptionBlock(
                    "theme-headings",
                    _t("Headings"),
                    "html_builder.ThemeHeadingsOption"
                )
            ),
            withSequence(
                50,
                this.getThemeOptionBlock(
                    "theme-button",
                    _t("Button"),
                    "html_builder.ThemeButtonOption"
                )
            ),
            withSequence(
                60,
                this.getThemeOptionBlock("theme-link", _t("Link"), "html_builder.ThemeLinkOption")
            ),
            withSequence(
                70,
                this.getThemeOptionBlock(
                    "theme-input",
                    _t("Input Fields"),
                    "html_builder.ThemeInputOption"
                )
            ),
            withSequence(
                80,
                this.getThemeOptionBlock(
                    "theme-advanced",
                    _t("Advanced"),
                    "html_builder.ThemeAdvancedOption"
                )
            ),
        ],
    };

    getThemeOptionBlock(id, name, template) {
        // TODO Have a specific kind of options container that takes the specific parameters like name, no element, no selector...
        const el = this.document.createElement("div");
        el.dataset.name = name;
        this.document.body.appendChild(el); // Currently editingElement needs to be isConnected

        return {
            id: id,
            element: el,
            hasOverlayOptions: false,
            headerMiddleButton: false,
            isClonable: false,
            isRemovable: false,
            options: [
                {
                    template: template,
                    selector: "*",
                },
            ],
            optionsContainerTopButtons: [],
            snippetModel: {},
        };
    }
}

registry.category("website-plugins").add(ThemeTabPlugin.id, ThemeTabPlugin);
