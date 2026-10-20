import { Component, props, types as t } from "@odoo/owl";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";

export class EmbeddedWhiteboardComponent extends Component {
    static template = "html_editor.EmbeddedWhiteboard";
    props = props({
        host: t.object(),
        url: t.string(),
        type: t.string(),
        previewUrl: t.string().optional(),
        embedUrl: t.string().optional(),
        error: t.boolean().optional(),
    });
}

export const whiteboardEmbedding = {
    name: "whiteboard",
    Component: EmbeddedWhiteboardComponent,
    getProps: (host) => {
        const props = { host, ...getEmbeddedProps(host) };
        const urlProps = Object.keys(props).filter((key) => key.toLowerCase().includes("url"));
        if (urlProps.some((url) => !/^https?:/.test(props[url]))) {
            for (const urlProp of urlProps) {
                props[urlProp] = "#";
            }
        }
        return props;
    },
};
