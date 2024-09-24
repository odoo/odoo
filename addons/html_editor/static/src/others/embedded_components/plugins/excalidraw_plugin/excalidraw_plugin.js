import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { ExcalidrawDialog } from "@html_editor/others/embedded_components/plugins/excalidraw_plugin/excalidraw_dialog/excalidraw_dialog";

export class ExcalidrawPlugin extends Plugin {
    static name = "excalidraw";
    static dependencies = ["embedded_components", "dom", "selection", "link"];
    resources = {
        powerboxItems: [
            {
                category: "navigation",
                name: _t("Drawing Board"),
                priority: 70,
                description: _t("Insert an Excalidraw Board"),
                fontawesome: "fa-pencil-square-o",
                action: () => {
                    this.insertDrawingBoard();
                },
            },
        ],
    };

    insertDrawingBoard() {
        const selection = this.shared.getEditableSelection();
        let restoreSelection = () => {
            this.shared.setSelection(selection);
        };
        this.services.dialog.add(
            ExcalidrawDialog,
            {
                saveLink: (href) => {
                    const templateBlock = renderToElement(
                        "html_editor.EmbeddedExcalidrawBlueprint",
                        {
                            embeddedProps: JSON.stringify({ source: href }),
                        }
                    );
                    this.shared.domInsert(templateBlock);

                    this.dispatch("ADD_STEP");

                    restoreSelection = () => {};
                },
            },
            { onClose: () => restoreSelection() }
        );
    }
}
