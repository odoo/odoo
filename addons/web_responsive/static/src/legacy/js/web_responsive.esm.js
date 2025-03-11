/** @odoo-module **/

/* Copyright 2018 Tecnativa - Jairo Llopis
 * Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {debounce} from "@web/core/utils/timing";

// Fix for iOS Safari to set correct viewport height
// https://github.com/Faisal-Manzer/postcss-viewport-height-correction
export function setViewportProperty(doc) {
    function handleResize() {
        requestAnimationFrame(function () {
            doc.style.setProperty("--vh100", doc.clientHeight + "px");
        });
    }

    handleResize();
    return handleResize;
}

window.addEventListener(
    "resize",
    debounce(setViewportProperty(document.documentElement), 25)
);
