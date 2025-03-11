/** @odoo-module **/
/* Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {onMounted, onWillStart, useExternalListener, useRef} from "@odoo/owl";
import {FileViewer} from "@web/core/file_viewer/file_viewer";
import {patch} from "@web/core/utils/patch";

const formChatterClassName = ".o-mail-Form-chatter";
const formViewSheetClassName = ".o_form_view_container .o_form_sheet_bg";

export function useFileViewerContainerSize(ref) {
    function updateActualFormChatterSize() {
        /** @type {HTMLDivElement}*/
        const chatterElement = document.querySelector(formChatterClassName);
        /** @type {HTMLDivElement}*/
        const formSheetElement = document.querySelector(formViewSheetClassName);
        if (chatterElement && formSheetElement && ref.el) {
            /** @type {CSSStyleDeclaration}*/
            const elStyle = ref.el.style;
            const width = `${chatterElement.clientWidth}px`;
            const height = `${chatterElement.clientHeight}px`;
            const left = `${formSheetElement.clientWidth}px`;
            elStyle.setProperty("--o-FileViewerContainer-width", width);
            elStyle.setProperty("--o-FileViewerContainer-height", height);
            elStyle.setProperty("--o-FileViewerContainer-left", left);
        }
    }

    useExternalListener(window, "resize", () => {
        requestAnimationFrame(updateActualFormChatterSize);
    });
    onMounted(() => {
        requestAnimationFrame(updateActualFormChatterSize);
    });
}

export const unpatchFileViewer = patch(FileViewer.prototype, {
    setup() {
        super.setup();
        this.root = useRef("root");
        Object.assign(this.state, {
            allowMinimize: false,
            maximized: true,
        });
        useFileViewerContainerSize(this.root);
        onWillStart(this.setDefaultMaximizeState);
    },

    get rootClass() {
        return {
            modal: this.props.modal,
            "o-FileViewerContainer__maximized": this.state.maximized,
            "o-FileViewerContainer__minimized": !this.state.maximized,
        };
    },

    setDefaultMaximizeState() {
        this.state.allowMinimize = Boolean(
            document.querySelector(`${formChatterClassName}.o-aside`)
        );
        this.state.maximized = !this.state.allowMinimize;
    },

    /**
     * @param {Boolean} value
     */
    setMaximized(value) {
        this.state.maximized = value;
    },
});
