import { Component, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
} from "@html_builder/core/utils";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { BuilderSelect } from "@html_builder/core/building_blocks/builder_select";
import { BuilderSelectItem } from "@html_builder/core/building_blocks/builder_select_item";

export class BuilderFontFamilyPicker extends Component {
    static template = "html_builder.BuilderFontFamilyPicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        valueParamName: String,
    };
    static components = {
        BuilderSelect,
        BuilderSelectItem,
    };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        useVisibilityObserver("content", useApplyVisibility("root"));
        this.fonts = [];
        onWillStart(async () => {
            const fontsData = await this.env.editor.shared.builderFont.getFontsData();
            this.fonts = fontsData._fonts.slice().sort((a, b) => a.string.localeCompare(b.string));
        });
    }
    forwardProps(fontValue) {
        const result = Object.assign({}, this.props, {
            [this.props.valueParamName]: fontValue.fontFamilyValue,
        });
        delete result.selectMethod;
        delete result.valueParamName;
        return result;
    }
    async onAddFontClick() {
        await this.env.editor.shared.websiteFont.addFont(this.props.actionParam);
    }
    async onDeleteFontClick(font) {
        const save = await new Promise((resolve) => {
            this.env.services.dialog.add(ConfirmationDialog, {
                body: _t(
                    "Deleting a font requires a reload of the page. This will save all your changes and reload the page, are you sure you want to proceed?"
                ),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        await this.env.editor.shared.websiteFont.deleteFont(font);
    }
}
