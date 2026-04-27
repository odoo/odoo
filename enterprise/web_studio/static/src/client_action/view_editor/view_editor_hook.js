/** @odoo-module */
import {
    onWillDestroy,
    onWillStart,
    status,
    useComponent,
    useEnv,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { viewTypeToString } from "@web_studio/studio_service";
import {
    useEditorBreadcrumbs,
    useEditorMenuItem,
} from "@web_studio/client_action/editor/edition_flow";
import { ViewEditorModel } from "./view_editor_model";
import { ViewEditorSnackbar } from "./view_editor_snackbar";

export function useViewEditorModel(viewRef, { initialState }) {
    const env = useEnv();

    /* Services */
    const services = Object.fromEntries(
        ["orm", "ui", "notification"].map((sName) => {
            return [sName, useService(sName)];
        })
    );
    // Capture studio's state as a new Object. This is due to concurrency
    // issues because we are an action, and rendering may be caused by other things (reactives)
    services.studio = { ...env.services.studio };
    services.dialog = { add: useOwnedDialogs() };

    /* Coordination */
    // Communicates with editorMenu, provides standard server calls
    const editionFlow = useState(env.editionFlow);
    useEditorBreadcrumbs({ name: viewTypeToString(services.studio.editedViewType) });

    const viewEditorModel = new ViewEditorModel({
        env,
        services,
        editionFlow,
        viewRef,
        initialState,
    });
    useSubEnv({ viewEditorModel });

    const { _snackBar, _operations } = viewEditorModel;
    useEditorMenuItem({
        component: ViewEditorSnackbar,
        props: { operations: _operations, saveIndicator: _snackBar },
    });

    const component = useComponent();
    onWillStart(async () => {
        return new Promise((resolve, reject) => {
            viewEditorModel
                .load()
                .then(resolve)
                .catch((error) => {
                    if (status(component) !== "destroyed") {
                        reject(error);
                    }
                });
        });
    });

    onWillDestroy(() => {
        viewEditorModel.isInEdition = false;
    });
    return useState(viewEditorModel);
}

export function useSnackbarWrapper(fn) {
    const env = useEnv();
    return env.viewEditorModel._decorateFunction(fn);
}
