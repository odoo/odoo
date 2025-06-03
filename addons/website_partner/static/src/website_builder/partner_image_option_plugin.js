import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

const PARTNER_IMAGE_OPTION_SELECTOR = "img.o_partner_image";

// TODO: dblclick to open media dialog

export class PartnerImageOptionPlugin extends Plugin {
    static id = "partnerImageOption";
    resources = {
        builder_options: [
            {
                template: "website_partner.PartnerImageOption",
                selector: PARTNER_IMAGE_OPTION_SELECTOR,
            },
        ],
        builder_actions: {
            /*
             * Removes the image in the back-end
             */
            RemovePartnerImageAction,
        },
        patch_builder_options: [
            {
                target_name: "replaceMediaOption",
                target_element: "exclude",
                method: "add",
                value: PARTNER_IMAGE_OPTION_SELECTOR,
            },
        ],
    };
}

/*
* Removes the image in the back-end
*/
export class RemovePartnerImageAction extends BuilderAction {
    static id = "removePartnerImage";
    setup() {
        this.reload = {};
    }
    async apply({ editingElement: el }) {
        await this.services.orm.write("res.partner", [
            parseInt(el.parentElement.dataset.oeId),
        ], {
            image_1920: false,
        });
        el.remove();
    }
}

registry.category("website-plugins").add(PartnerImageOptionPlugin.id, PartnerImageOptionPlugin);
