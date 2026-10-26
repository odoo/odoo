import { Component, t, useProps } from "@odoo/owl";

export class PublishPageMessage extends Component {
    static template = "website.PublishPageMessage";
    props = useProps({
        publishPage: t.function(),
    });
}
