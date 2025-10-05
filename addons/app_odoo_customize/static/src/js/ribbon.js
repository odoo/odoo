/** @odoo-module **/
/* Copyright 2015 Sylvain Calador <sylvain.calador@akretion.com>
   Copyright 2015 Javi Melendez <javi.melendez@algios.com>
   Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
   Copyright 2017 Thomas Binsfeld <thomas.binsfeld@acsone.eu>
   Copyright 2017 Xavier Jiménez <xavier.jimenez@qubiq.es>
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */



import {Component, xml} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";

export class WebEnvironmentRibbon extends Component {
    setup() {
        this.orm = useService("orm");
        useBus(this.env.bus, "WEB_CLIENT_READY", this.showRibbon.bind(this));
    }

    // Code from: http://jsfiddle.net/WK_of_Angmar/xgA5C/
    validStrColour(strToTest) {
        if (strToTest === "") {
            return false;
        }
        if (strToTest === "inherit") {
            return true;
        }
        if (strToTest === "transparent") {
            return true;
        }
        const image = document.createElement("img");
        image.style.color = "rgb(0, 0, 0)";
        image.style.color = strToTest;
        if (image.style.color !== "rgb(0, 0, 0)") {
            return true;
        }
        image.style.color = "rgb(255, 255, 255)";
        image.style.color = strToTest;
        return image.style.color !== "rgb(255, 255, 255)";
    }

    showRibbon() {
        const ribbon = document.querySelector('.test-ribbon');
        const self = this;
        ribbon.classList.add('o_hidden');
        // Get ribbon data from backend
        self.orm
            .call("web.environment.ribbon.backend", "get_environment_ribbon")
            .then(function (ribbon_data) {
                // Ribbon name
                if (ribbon_data.name && ribbon_data.name !== "False" && ribbon_data.name !== "0") {
                    ribbon.classList.remove('o_hidden');
                    ribbon.innerHTML = ribbon_data.name;
                }
                // Ribbon color
                if (ribbon_data.color && self.validStrColour(ribbon_data.color)) {
                    ribbon.style.color = ribbon_data.color;
                }
                // Ribbon background color
                if (
                    ribbon_data.background_color &&
                    self.validStrColour(ribbon_data.background_color)
                ) {
                    ribbon.style.backgroundColor = ribbon_data.background_color;
                }
            });
    }
}

WebEnvironmentRibbon.props = {};
WebEnvironmentRibbon.template = xml`<div class="test-ribbon" />`;

registry.category("main_components").add("WebEnvironmentRibbon", {
    Component: WebEnvironmentRibbon,
});
