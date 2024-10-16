import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { ExcalidrawDialog } from "@html_editor/others/embedded_components/plugins/excalidraw_plugin/excalidraw_dialog/excalidraw_dialog";
import { ReadonlyEmbeddedExcalidrawComponent } from "@html_editor/others/embedded_components/core/excalidraw/readonly_excalidraw";
import { useService } from "@web/core/utils/hooks";

export class EmbeddedExcalidrawComponent extends ReadonlyEmbeddedExcalidrawComponent {
    static props = {
        ...ReadonlyEmbeddedExcalidrawComponent.props,
        host: { type: Object },
    };
    static template = "html_editor.EmbeddedExcalidraw";

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.embeddedState = useEmbeddedState(this.props.host);
    }

    get templateState() {
        if (this.displayState.isResizing) {
            return this.state;
        } else {
            return this.embeddedState;
        }
    }

    onMouseDown() {
        this.state.width = this.embeddedState.width;
        this.state.height = this.embeddedState.height;
        super.onMouseDown(...arguments);
    }

    onMouseUp() {
        super.onMouseUp(...arguments);
        this.embeddedState.width = this.state.width;
        this.embeddedState.height = this.state.height;
    }

    openUpdateSource() {
        this.dialog.add(ExcalidrawDialog, {
            saveLink: (url) => {
                this.displayState.hasError = false;
                this.state.source = url;
                this.embeddedState.source = url;
            },
        });
    }

    setURL(url) {
        super.setURL(...arguments);
        this.embeddedState.source = url;
    }
}

export const excalidrawEmbedding = {
    name: "draw",
    Component: EmbeddedExcalidrawComponent,
    getProps: (host) => {
        return { host, ...getEmbeddedProps(host) };
    },
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                getEmbeddedState: (host) => {
                    const props = getEmbeddedProps(host);
                    return {
                        ...props,
                        height: props.height || "400px",
                        width: props.width || "100%",
                    };
                },
            })
        ),
};
