/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { CodeEditor } from "@web/core/code_editor/code_editor";

/**
 * A dialog that let the user edit the code that will be injected in the <head>
 * and before the </body> of every page of the website. This is a stable and
 * upgrade proof alternative to directly editing the website xml.
 */
export class EditHeadBodyDialog extends Component {
    static template = "website.EditHeadBodyDialog";
    static components = { CodeEditor, Dialog };
    static props = {
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.website = useService("website");

        this.state = useState({
            head: "",
            body: "",
        });

        onWillStart(async () => {
            const websites = await this.orm.read("website",
                [this.website.currentWebsite.id],
                ["custom_code_head", "custom_code_footer"],
            );
            const website = websites[0];
            this.state.head = website.custom_code_head || "";
            this.state.body = website.custom_code_footer || "";
        });
    }

    async onSave() {
        await this.orm.write("website", [this.website.currentWebsite.id], {
            custom_code_head: this.state.head,
            custom_code_footer: this.state.body,
        });
        this.props.close();
    }
}
