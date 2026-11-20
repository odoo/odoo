import { Component, proxy, signal, t, usePlugin, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba, convertRgbaToCSSColor } from "@web/core/utils/colors";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { CustomColorPicker, DEFAULT_COLOR } from "../../custom_color_picker/custom_color_picker";
import { FavoriteColorsPlugin } from "../../favorite_colors_plugin";

export class ColorPickerFavoriteTab extends Component {
    static template = "html_editor.ColorPickerFavoriteTab";
    static components = { CustomColorPicker };
    props = useProps({
        onColorClick: t.function(),
        onColorPointerOver: t.function(),
        onColorPointerOut: t.function(),
        onFocusin: t.function(),
        onFocusout: t.function(),
        selectedColor: t.string().optional(),
        defaultOpacity: t.number().optional(),
        noTransparency: t.boolean().optional(),
    });
    addButtonRef = signal.ref();

    setup() {
        this.favoriteColors = usePlugin(FavoriteColorsPlugin);
        this.notification = usePlugin(NotificationPlugin);
        this.state = proxy({
            isAdding: false,
            newColor: undefined,
        });
    }

    toggleColorPicker() {
        this.state.isAdding = !this.state.isAdding;
        if (this.state.isAdding) {
            // Start from the current color, as it is likely the one to keep.
            const rgba = convertCSSColorToRgba(this.props.selectedColor);
            this.state.newColor = rgba
                ? convertRgbaToCSSColor(rgba.red, rgba.green, rgba.blue, rgba.opacity)
                : DEFAULT_COLOR;
        }
    }

    /**
     * @param {Object} colorComponents
     * @param {string} colorComponents.hex
     */
    onNewColorChange({ hex }) {
        this.state.newColor = hex;
    }

    /**
     * Moves the focus to the add button before removing the focused element,
     * as losing the focus would close the color picker in the editor.
     */
    focusAddButton() {
        this.addButtonRef()?.focus();
    }

    async onSaveClick() {
        const newColor = this.state.newColor.toUpperCase();
        if (this.favoriteColors.getColors().includes(newColor)) {
            this.notification.add(_t("This color is already in the favorite colors."), {
                type: "warning",
            });
            return;
        }
        this.focusAddButton();
        this.state.isAdding = false;
        await this.favoriteColors.add(newColor);
    }

    onDiscardClick() {
        this.focusAddButton();
        this.state.isAdding = false;
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
