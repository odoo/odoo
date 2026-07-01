/** @odoo-module */
/* Copyright 2024 Akretion
/* Copyright 2024 Tecnativa
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {getVisibleElements, isVisible} from "@web/core/utils/ui";
import {FormController} from "@web/views/form/form_controller";
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {ListController} from "@web/views/list/list_controller";
import {isAllowedBarcodeModel} from "../utils/barcodes_models_utils.esm";
import {patch} from "@web/core/utils/patch";
import {useEffect} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

let barcodeOverlaysVisible = false;

// This is necessary because the hotkey service does not make its API public for
// some reasons
export function barcodeRemoveHotkeyOverlays() {
    for (const overlay of document.querySelectorAll(".o_barcode_web_hotkey_overlay")) {
        overlay.remove();
    }
    barcodeOverlaysVisible = false;
}

// This is necessary because the hotkey service does not make its API public for
// some reasons
export function barcodeAddHotkeyOverlays(activeElement) {
    for (const el of getVisibleElements(
        activeElement,
        "[data-hotkey]:not(:disabled)"
    )) {
        const hotkey = el.dataset.hotkey;
        const overlay = document.createElement("div");
        overlay.classList.add(
            "o_barcode_web_hotkey_overlay",
            "position-absolute",
            "top-0",
            "bottom-0",
            "start-0",
            "end-0",
            "d-flex",
            "justify-content-center",
            "align-items-center",
            "m-0",
            "bg-black-50",
            "h6"
        );
        const overlayKbd = document.createElement("kbd");
        overlayKbd.className = "small";
        overlayKbd.appendChild(document.createTextNode(hotkey.toUpperCase()));
        overlay.appendChild(overlayKbd);

        let overlayParent = null;
        if (el.tagName.toUpperCase() === "INPUT") {
            // Special case for the search input that has an access key
            // defined. We cannot set the overlay on the input itself,
            // only on its parent.
            overlayParent = el.parentElement;
        } else {
            overlayParent = el;
        }

        if (overlayParent.style.position !== "absolute") {
            overlayParent.style.position = "relative";
        }
        overlayParent.appendChild(overlay);
    }
    barcodeOverlaysVisible = true;
}

function setupView() {
    const actionService = useService("action");
    const uiService = useService("ui");
    const busService = useService("bus_service");
    const notification = useService("notification");

    const handleKeys = async (ev) => {
        if (ev.keyCode === 113) {
            // F2
            const {activeElement} = uiService;

            if (barcodeOverlaysVisible) {
                barcodeRemoveHotkeyOverlays();
            } else {
                barcodeAddHotkeyOverlays(activeElement);
            }
        } else if (ev.keyCode === 120) {
            // F9
            const button = document.querySelector("button[name='action_clean_values']");
            if (isVisible(button)) {
                button.click();
            }
        } else if (ev.keyCode === 123 || ev.keyCode === 115) {
            // F12 or F4
            await actionService.doAction(
                "stock_barcodes.action_stock_barcodes_action",
                {
                    name: "Barcode wizard menu",
                    res_model: "wiz.stock.barcodes.read.picking",
                    type: "ir.actions.act_window",
                }
            );
        }
    };

    const handleNotification = ({detail: notifications}) => {
        if (notifications && notifications.length > 0) {
            notifications.forEach((notif) => {
                const {payload, type} = notif;
                if (
                    (this.model.root.resModel == payload.res_model) &
                    (this.model.root.resId == payload.res_id)
                ) {
                    if (type === "stock_barcodes_sound") {
                        this.$sound_ok[0].play();
                    }
                    if (type === "stock_barcodes_focus") {
                        requestIdleCallback(() => {
                            const input = document.querySelector(
                                `[name=${payload.field_name}] input`
                            );
                            if (input) {
                                input.focus();
                            }
                        });
                    }
                    if (type === "stock_barcodes_notify") {
                        notification.add(notif.payload.message, {
                            title: notif.payload.title,
                            type: notif.payload.type,
                            sticky: notif.payload.sticky,
                        });
                    }
                }
            });
        }
    };

    useEffect(() => {
        document.body.addEventListener("keydown", handleKeys);

        this.$sound_ok = $("<audio>", {
            src: "/stock_barcodes/static/src/sounds/bell.wav",
            preload: "auto",
        });
        this.$sound_ok.appendTo("body");
        this.$sound_ko = $("<audio>", {
            src: "/stock_barcodes/static/src/sounds/error.wav",
            preload: "auto",
        });
        this.$sound_ko.appendTo("body");

        busService.addChannel("stock_barcodes_scan");

        busService.addEventListener("notification", handleNotification);

        return () => {
            this.$sound_ok.remove();
            this.$sound_ko.remove();
            document.body.removeEventListener("keydown", handleKeys);
            busService.deleteChannel("stock_barcodes_scan");
            busService.removeEventListener("notification", handleNotification);
        };
    });
}

patch(KanbanController.prototype, "add hotkeys to kanban", {
    setup() {
        this._super(...arguments);
        if (isAllowedBarcodeModel(this.props.resModel)) {
            setupView.call(this);
        }
    },
});

patch(FormController.prototype, "add hotkeys to form", {
    setup() {
        this._super(...arguments);
        if (isAllowedBarcodeModel(this.props.resModel)) {
            setupView.call(this);
        }
    },
});

patch(ListController.prototype, "add hotkeys to list", {
    setup() {
        this._super(...arguments);
        if (isAllowedBarcodeModel(this.props.resModel)) {
            setupView.call(this);
        }
    },
});
