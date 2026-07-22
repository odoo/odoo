import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, KanbanMany2One } from "../many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    many2OneFieldProps,
} from "../many2one/many2one_field";

export class CardMany2OneAvatarField extends Component {
    static template = "web.CardMany2OneAvatarField";
    static components = { KanbanMany2One };
    props = useProps(many2OneFieldProps);

    get m2oProps() {
        return computeM2OProps(this.props);
    }
}

registry.category("fields").add("card.many2one_avatar", {
    ...buildM2OFieldDescription(CardMany2OneAvatarField),
    relatedFields: [{ name: "write_date", type: "datetime" }],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            readonly: dynamicInfo.readonly,
        };
    },
});
