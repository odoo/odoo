/** @odoo-module **/
/* Copyright 2015-2018,2021,2023 Ivan Yelizariev <https://twitter.com/yelizariev>
   Copyright 2015 igallyamov <https://github.com/igallyamov>
   Copyright 2017 Gabbasov Dinar <https://it-projects.info/team/GabbasovDinar>
   Copyright 2022 IT-Projects <https://it-projects.info/>
   License OPL-1 (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#odoo-apps). */

import "@web_debranding/js/base";
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

const component = { Dialog };

patch(component.Dialog.prototype, {
    setup() {
        const debranding_new_name = odoo.debranding_new_name;
        // // const debranding_new_website = odoo.debranding_new_website;

        // // options = this.constructor || {};

        if (this.constructor.title && this.constructor.title.replace) {
            var title = this.constructor.title.replace(/Odoo/gi, debranding_new_name);
            this.constructor.title = title;
        } else {
            this.constructor.title = debranding_new_name;
        }
        // Разобраться во что превратился $content
        /* if (options.$content) {
            if (!(options.$content instanceof $)) {
                options.$content = $(options.$content);
            }
            var content_html = options.$content.html();
            content_html = content_html.replace(
                /Odoo.com/gi,
                debranding_new_website
            );
            content_html = content_html.replace(/Odoo/gi, debranding_new_name);
            options.$content.html(content_html);
        }*/
        super.setup();
    },
});
