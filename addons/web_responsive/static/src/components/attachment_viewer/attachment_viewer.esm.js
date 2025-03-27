/** @odoo-module **/
/* Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {AttachmentViewer} from "@mail/components/attachment_viewer/attachment_viewer";
import {patch} from "web.utils";
import {registerPatch} from "@mail/model/model_core";
const {useState} = owl;

// Patch attachment viewer to add min/max buttons capability
patch(AttachmentViewer.prototype, "web_responsive.AttachmentViewer", {
    setup() {
        this._super();
        this.state = useState({
            maximized: false,
        });
    },
});

registerPatch({
    name: "Dialog",
    fields: {
        isCloseable: {
            compute() {
                if (this.attachmentViewer) {
                    /**
                     * Prevent closing the dialog when clicking on the mask when the user is
                     * currently dragging the image.
                     */
                    return false;
                }
                return this._super();
            },
        },
    },
});
