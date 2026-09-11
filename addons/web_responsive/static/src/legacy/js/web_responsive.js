/* Copyright 2018 Tecnativa - Jairo Llopis
 * Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */
odoo.define("web_responsive", function () {
    "use strict";
    // Fix for iOS Safari to set correct viewport height
    // https://github.com/Faisal-Manzer/postcss-viewport-height-correction
    function setViewportProperty(doc) {
        function handleResize() {
            requestAnimationFrame(function updateViewportHeight() {
                doc.style.setProperty("--vh100", doc.clientHeight + "px");
            });
        }
        handleResize();
        return handleResize;
    }
    window.addEventListener(
        "resize",
        _.debounce(setViewportProperty(document.documentElement), 100)
    );
});
