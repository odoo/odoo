/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";

const { Component, useState, useEffect } = owl;

class TopActionsEditorSystray extends Component {
    setup() {
        this.websiteService = useService("website");
        this.websiteContext = useState(this.websiteService.context);

        this.state = useState({
            isEditorOpen: true,
            historyCanUndo: false,
            historyCanRedo: false,
            disabled: false,
        });

        useBus(this.websiteService.bus, "HISTORY-CAN-UNDO", (ev) => {
            this.state.historyCanUndo = ev.detail.historyCanUndo;
        });
        useBus(this.websiteService.bus, "HISTORY-CAN-REDO", (ev) => {
            this.state.historyCanRedo = ev.detail.historyCanRedo;
        });

        useEffect((isPublicRootReady) => {
            this.state.isSaveLoading = !isPublicRootReady && !this.notSaveButtonClicked;
            this.state.disabled = !isPublicRootReady;
        }, () => [this.websiteContext.isPublicRootReady]);

        useEffect((snippetsLoaded) => {
            this.state.isEditorOpen = snippetsLoaded;
        }, () => [this.websiteContext.snippetsLoaded]);
    }

    undo() {
        this.websiteService.bus.trigger("UNDO");
    }
    redo() {
        this.websiteService.bus.trigger("REDO");
    }
    cancel() {
        this.buttonClick((after) => {
            this.websiteService.bus.trigger("CANCEL", { data: {onDiscard: after, onReject: after} });
        });
    }
    save() {
        this.buttonClick((after) => {
            this.websiteService.bus.trigger("SAVE", { data: {
                onSuccess: () => {
                    this.websiteService.bus.trigger("LEAVE-EDIT-MODE",
                        { forceLeave: true, onLeave: after }
                    );
                },
                onFailure: after,
            } });
        }, true);
    }

    /***
     * Disables the buttons after the 1st click. Removes the loading effect on the save button if
     * this was not the button clicked. Passes an argument to reallow the loading effect to the
     * function to execute.
     *
     * @param action {Function} The action to execute
     * @param clickedOnSave {boolean}
     * @returns {Promise<void>}
     */
    async buttonClick(action, clickedOnSave = false) {
        if (this.state.disabled) {
            return;
        }
        let after = () => null;
        if (!clickedOnSave) {
            this.notSaveButtonClicked = true;
            after = () => {
                delete this.notSaveButtonClicked;
            };
        }
        await action(after);
    }
}
TopActionsEditorSystray.template = "website.TopActionsEditorSystray";

export const systrayItem = {
    Component: TopActionsEditorSystray,
    isDisplayed: (env) => env.services.website.currentWebsite.metadata.editable,
};

registry.category("website_systray").add("TopActionsEditor", systrayItem, { sequence: 1 });
