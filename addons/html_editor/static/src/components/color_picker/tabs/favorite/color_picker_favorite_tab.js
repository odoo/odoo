import { Component, proxy, signal, t, usePlugin, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba, convertRgbaToCSSColor } from "@web/core/utils/colors";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { CustomColorPicker, DEFAULT_COLOR } from "../../custom_color_picker/custom_color_picker";
import { FavoriteColorsPlugin } from "../../favorite_colors_plugin";

/**
 * Sub panel of the favorite colors tab, to select a new favorite color.
 */
export class FavoriteColorAdder extends Component {
    static template = "html_editor.FavoriteColorAdder";
    static components = { CustomColorPicker };
    props = useProps({
        initialColor: t.string(),
        onAdd: t.function(),
        defaultOpacity: t.number().optional(),
        noTransparency: t.boolean().optional(),
    });

    setup() {
        this.state = proxy({ color: this.props.initialColor });
    }

    /**
     * @param {Object} colorComponents
     * @param {string} colorComponents.hex
     */
    onColorChange({ hex }) {
        this.state.color = hex;
    }
}

export class ColorPickerFavoriteTab extends Component {
    static template = "html_editor.ColorPickerFavoriteTab";
    props = useProps({
        onColorClick: t.function(),
        onColorPointerOver: t.function(),
        onColorPointerOut: t.function(),
        onFocusin: t.function(),
        onFocusout: t.function(),
        openSubPanel: t.function(),
        closeSubPanel: t.function(),
        selectedColor: t.string().optional(),
        defaultOpacity: t.number().optional(),
        noTransparency: t.boolean().optional(),
    });
    addButtonRef = signal.ref();

    setup() {
        this.favoriteColors = usePlugin(FavoriteColorsPlugin);
        this.notification = usePlugin(NotificationPlugin);
    }

    onAddButtonClick() {
        // Start from the current color, as it is likely the one to keep.
        const rgba = convertCSSColorToRgba(this.props.selectedColor);
        const initialColor = rgba
            ? convertRgbaToCSSColor(rgba.red, rgba.green, rgba.blue, rgba.opacity)
            : DEFAULT_COLOR;
        this.props.openSubPanel(
            FavoriteColorAdder,
            {
                initialColor,
                onAdd: this.addColor.bind(this),
                defaultOpacity: this.props.defaultOpacity,
                noTransparency: this.props.noTransparency,
            },
            _t("Add a favorite color")
        );
    }

    /**
     * @param {string} color
     */
    async addColor(color) {
        color = color.toUpperCase();
        if (this.favoriteColors.getColors().includes(color)) {
            this.notification.add(_t("This color is already in the favorite colors."), {
                type: "warning",
            });
            return;
        }
        this.props.closeSubPanel();
        await this.favoriteColors.add(color);
    }

    /**
     * Moves the focus to the add button before removing the focused element,
     * as losing the focus would close the color picker in the editor.
     */
    focusAddButton() {
        this.addButtonRef()?.focus();
    }

    /**
     * @param {string} color
     */
    async onRemoveClick(color) {
        this.focusAddButton();
        await this.favoriteColors.remove(color);
    }
}

registry.category("color_picker_tabs").add(
    "html_editor.favorite",
    {
        id: "favorite",
        name: _t("Company favorite colors"),
        icon: "favorite",
        component: ColorPickerFavoriteTab,
        // Without favorite colors, the tab is only useful to define them.
        isAvailable: () => {
            const favoriteColors = usePlugin(FavoriteColorsPlugin);
            return favoriteColors.canEdit() || favoriteColors.getColors().length > 0;
        },
    },
    { sequence: 100 }
);
