/* Copyright 2014 Therp BV (<http://therp.nl>)
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

// This file contains tweaks for viewerjs itself and is not meant to be run in
// OpenERP's context
(function (original_Viewer) {
    "use strict";
    // eslint-disable-next-line no-undef
    window.Viewer = function (plugin, parameters) {
        if (!plugin) {
            // eslint-disable-next-line no-undef, no-alert
            alert("Unsupported file type");
        }
        return original_Viewer(plugin, parameters);
    };
    // eslint-disable-next-line no-undef
})(window.Viewer);
