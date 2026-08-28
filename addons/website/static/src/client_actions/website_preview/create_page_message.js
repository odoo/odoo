import { Component, useProps, t } from "@odoo/owl";

export class CreatePageMessage extends Component {
    static template = "website.CreatePageMessage";
    props = useProps({
        createPage: t.function(),
    });
}
