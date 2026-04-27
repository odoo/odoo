/** @odoo-module **/

import { COLORS, BG_COLORS } from "@web_studio/utils";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { FileInput } from "@web/core/file_input/file_input";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { FontAwesomeIconSelector } from "@web_studio/client_action/components/font_awesome_icon_selector/font_awesome_icon_selector";

import { Component } from "@odoo/owl";
import { resizeBlobImg } from "@web/core/utils/files";

export const DEFAULT_ICON = {
    backgroundColor: BG_COLORS[0],
    color: COLORS[10],
    iconClass: "fa fa-home",
    type: "custom_icon",
};

/**
 * Icon creator
 *
 * Component which purpose is to design an app icon. It can be an uploaded image
 * which will be displayed as is, or an icon customized with the help of presets
 * of colors and icon symbols (@see web_studio/static/src/utils for the full list of colors
 * and icon classes).
 * @extends Component
 */
export class IconCreator extends Component {
    static components = {
        Dropdown,
        FileInput,
        FontAwesomeIconSelector,
        SelectMenu,
    };
    static defaultProps = DEFAULT_ICON;
    static props = {
        backgroundColor: { type: String, optional: 1 },
        color: { type: String, optional: 1 },
        editable: { type: Boolean, optional: 1 },
        iconClass: { type: String, optional: 1 },
        type: { validate: (t) => ["base64", "custom_icon"].includes(t), optional: 1 },
        uploaded_attachment_id: { type: Number, optional: 1 },
        webIconData: { type: String, optional: 1 },
        onIconChange: Function,
    };
    static template = "web_studio.IconCreator";

    /**
     * @param {Object} [props]
     * @param {string} [props.backgroundColor] Background color of the custom
     *      icon.
     * @param {string} [props.color] Color of the custom icon.
     * @param {boolean} props.editable
     * @param {string} [props.iconClass] Font Awesome class of the custom icon.
     * @param {string} props.type 'base64' (if an actual image) or 'custom_icon'.
     * @param {number} [props.uploaded_attachment_id] Databse ID of an uploaded
     *      attachment
     * @param {string} [props.webIconData] Base64-encoded string representing
     *      the icon image.
     */
    setup() {
        this.orm = useService("orm");

        const onWillUploadFiles = async (fileList) =>
            Promise.all(
                fileList.map(async (file) => {
                    const blob = await resizeBlobImg(file, { height: 64, width: 64 });
                    return new File([blob], file.name);
                })
            );
        this.fileInputProps = {
            acceptedFileExtensions: "image/png",
            resModel: "res.users",
            resId: user.userId,
            onWillUploadFiles,
        };
    }

    get backgroundColorChoices() {
        return this.getChoices(BG_COLORS);
    }

    get colorChoices() {
        return this.getChoices(COLORS);
    }

    getChoices(object) {
        return object.map((color) => {
            return {
                label: color,
                value: color,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onDesignIconClick() {
        this.props.onIconChange(DEFAULT_ICON);
    }

    /**
     * @param {Object[]} files
     */
    async onFileUploaded([file]) {
        if (!file) {
            // Happens when cancelling upload
            return;
        }
        const res = await this.orm.read("ir.attachment", [file.id], ["datas"]);

        this.props.onIconChange({
            type: "base64",
            uploaded_attachment_id: file.id,
            webIconData: "data:image/png;base64," + res[0].datas.replace(/\s/g, ""),
        });
    }

    /**
     * @param {string} palette
     * @param {string} value
     */
    onPaletteItemClick(palette, value) {
        if (this.props[palette] === value) {
            return; // same value
        }
        this.props.onIconChange({
            backgroundColor: this.props.backgroundColor,
            color: this.props.color,
            iconClass: this.props.iconClass,
            type: "custom_icon",
            [palette]: value,
        });
    }
}
