import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import {
    measureText,
    TEXT_DEFAULT_FONT_SIZE,
    TEXT_MIN_WIDTH,
} from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/utils/text";
import { STATIC_IMG_BASE_URL } from "@pos_restaurant/app/services/floor_plan/utils/utils";

const WALL_HEIGHT = 6;

export class AddDecorPopup extends Component {
    static template = "pos_restaurant.floor_editor.add_decor_popup";
    static components = { Dialog };

    static props = {
        addDecor: { type: Function },
        close: { optional: false },
    };

    setup() {
        this.dialog = useService("dialog");
    }

    addImage(data) {
        this.props.addDecor("image", data);
        this.props.close();
    }

    addImageAsset(name) {
        this.addImage({ name: name });
    }

    getAssetUrl(name) {
        return STATIC_IMG_BASE_URL + "/" + name;
    }

    addText() {
        this.props.close();

        this.dialog.add(TextInputPopup, {
            title: _t("Enter your text"),
            rows: 4,
            size: "md",

            getPayload: async (value) => {
                this.doAddText(value);
            },
        });
    }

    addLine(style) {
        this.props.addDecor("line", {
            height: 5,
            width: 250,
            borderStyle: style || "solid",
        });
        this.props.close();
    }

    addSquare() {
        this.props.addDecor("rect", {
            height: 200,
            width: 200,
            borderWidth: 3,
        });
        this.props.close();
    }

    addRect() {
        this.props.addDecor("rect", {
            height: 150,
            width: 200,
            borderWidth: 3,
        });
        this.props.close();
    }

    addCircle() {
        this.props.addDecor("circle", {
            height: 200,
            width: 200,
            borderWidth: 3,
        });
        this.props.close();
    }

    addOval() {
        this.props.addDecor("oval", {
            height: 150,
            width: 200,
            borderWidth: 3,
        });
        this.props.close();
    }

    addDoor(type) {
        switch (type) {
            case "v":
                this.addDoorDecor(90);
                break;
            case "h":
                this.addDoorDecor();
                break;
            case "-45":
                this.addDoorDecor(-45);
                break;

            case "45":
                this.addDoorDecor(45);
                break;
        }

        this.props.close();
    }
    addDoorDecor(rotation) {
        this.props.addDecor("line", {
            height: 10,
            width: 120,
            type: "double",
            group: "ld",
            rotation,
        });
    }

    addWall(style) {
        switch (style) {
            case "v":
                this.props.addDecor("line", {
                    height: WALL_HEIGHT,
                    width: 250,
                    rotation: 90,
                    group: "lw",
                });
                break;
            case "h":
                this.props.addDecor("line", {
                    height: WALL_HEIGHT,
                    width: 250,
                    group: "lw",
                });
                break;
            case "top-left":
                this.addWallBorder("top left");
                break;
            case "top-right":
                this.addWallBorder("top right");
                break;
            case "bottom-left":
                this.addWallBorder("bottom left");
                break;
            case "bottom-right":
                this.addWallBorder("bottom right");
                break;
            case "top-left-right":
                this.addWallBorder("top left right");
                break;
            case "full":
                this.addWallBorder("");
                break;

            default:
        }
        this.props.close();
    }

    addWallBorder(visibleBorders) {
        this.props.addDecor("rect", {
            onlyBorder: true,
            height: 250,
            width: 250,
            borderWidth: WALL_HEIGHT,
            visibleBorders: visibleBorders,
            group: "lw",
        });
    }

    doAddText(text) {
        if (!text.trim().length) {
            return;
        }
        const fontSize = TEXT_DEFAULT_FONT_SIZE;
        const size = measureText(
            text,
            {
                "font-size": fontSize + "px",
            },
            "o_fp_text_content"
        );

        this.props.addDecor("text", {
            text: text,
            width: Math.max(size.width, TEXT_MIN_WIDTH),
            height: size.height,
            fontSize,
        });
    }
}
