/** @odoo-module **/
import { COLORS, BG_COLORS, ICONS } from "@web_studio/utils";
import { FileInput } from "@web/core/file_input/file_input";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillUpdateProps, useRef, useState } from "@odoo/owl";

const DEFAULT_ICON = {
    backgroundColor: BG_COLORS[5],
    color: COLORS[4],
    iconClass: ICONS[0],
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
        this.COLORS = COLORS;
        this.BG_COLORS = BG_COLORS;
        this.ICONS = ICONS;

        this.iconRef = useRef("app-icon");

        this.orm = useService("orm");
        this.rpc = useService("rpc");
        const user = useService("user");

        this.FileInput = FileInput;
        this.fileInputProps = {
            acceptedFileExtensions: "image/png",
            resModel: "res.users",
            resId: user.userId,
        };

        this.state = useState({ iconClass: this.props.iconClass });
        this.show = useState({
            backgroundColor: false,
            color: false,
            iconClass: false,
        });

        onWillUpdateProps((nextProps) => {
            if (
                this.constructor.enableTransitions &&
                nextProps.iconClass !== this.props.iconClass
            ) {
                this.applyIconTransition(nextProps.iconClass);
            } else {
                this.state.iconClass = nextProps.iconClass;
            }
        });
    }

    applyIconTransition(nextIconClass) {
        const iconEl = this.iconRef.el;
        if (!iconEl) {
            return;
        }

        iconEl.classList.remove("o-fading-in");
        iconEl.classList.remove("o-fading-out");

        iconEl.onanimationend = () => {
            this.state.iconClass = nextIconClass;
            iconEl.onanimationend = () => {
                iconEl.onanimationend = null;
                iconEl.classList.remove("o-fading-in");
            };
            iconEl.classList.remove("o-fading-out");
            iconEl.classList.add("o-fading-in");
        };
        iconEl.classList.add("o-fading-out");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onDesignIconClick() {
        this.props.onIconChange({
            type: "custom_icon",
            ...DEFAULT_ICON,
        });
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

    /**
     * @param {string} palette
     */
    onTogglePalette(palette) {
        for (const pal in this.show) {
            if (pal === palette) {
                this.show[pal] = !this.show[pal];
            } else if (this.show[pal]) {
                this.show[pal] = false;
            }
        }
    }
}

IconCreator.defaultProps = DEFAULT_ICON;
IconCreator.props = {
    backgroundColor: { type: String, optional: 1 },
    color: { type: String, optional: 1 },
    editable: { type: Boolean, optional: 1 },
    iconClass: { type: String, optional: 1 },
    type: { validate: (t) => ["base64", "custom_icon"].includes(t) },
    uploaded_attachment_id: { type: Number, optional: 1 },
    webIconData: { type: String, optional: 1 },
    onIconChange: Function,
};
IconCreator.template = "web_studio.IconCreator";
IconCreator.enableTransitions = true;
