import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { locationBatchUtils } from "./store_locator_utils";

class StoreLocatorOptionPlugin extends Plugin {
    static id = "storeLocatorOption";
    resources = {
        builder_actions: {
            AddLocationToStoreLocatorAction,
            HideLocationsOffscreenAction,
        },
    };
}

export class HideLocationsOffscreenAction extends BuilderAction {
    static id = "hideLocationsOffscreen";
    static dependencies = ["builderActions"];
    // If the snippet does not have a fixed height (represented by the classes
    // `o_half_screen_height` or `o_full_screen_height`), we force it to have
    // height fixed to 50% of viewport (`o_half_screen_height`). This is done
    // to prevent the unpleasant effect of the snippet changing height based
    // on how the user moves / zooms the map (because when the view changes,
    // locations could appear or hide and the list would change height).
    apply({ editingElement }) {
        const classes = editingElement.classList;
        if (
            !classes.contains("o_half_screen_height") &&
            !classes.contains("o_full_screen_height")
        ) {
            this.dependencies.builderActions.getAction("scrollButtonSectionHeightClass").apply({
                editingElement,
                params: {
                    mainParam: "o_half_screen_height",
                },
            });
        }
    }
}

export class AddLocationToStoreLocatorAction extends BuilderAction {
    static id = "addLocationToStoreLocator";

    // When adding locations, load fetches opening hours from the database and
    // calls the geolocalization method if necessary. Note that multiple
    // locations could be added per time by the BuilderList component.
    async load({ editingElement, value }) {
        const newList = JSON.parse(value);
        const oldList = JSON.parse(editingElement.dataset.locationsList || "[]");

        // Early return if there are no new locations to process
        if (oldList.length >= newList.length) {
            return newList;
        }

        const oldLocationsIDs = new Set(oldList.map((l) => l.id));
        const locationsMap = new Map(newList.map((l) => [l.id, l]));
        const newLocationsId = Array.from(
            locationsMap.keys().filter((id) => !oldLocationsIDs.has(id))
        );
        await locationBatchUtils.geolocalize(this.services.orm, locationsMap, newLocationsId);
        await locationBatchUtils.updateCalendar(this.services.orm, locationsMap, newLocationsId);

        let newLocationsList = Array.from(locationsMap.values());
        const lengthBeforeFiltering = newLocationsList.length;
        newLocationsList = newLocationsList.filter(
            (l) => l.partner_latitude && l.partner_longitude
        );
        const lengthAfterFiltering = newLocationsList.length;
        if (lengthBeforeFiltering > lengthAfterFiltering) {
            this.services.dialog.add(ConfirmationDialog, {
                title: _t("Geolocation Failed"),
                body: _t(
                    "One or more selected locations could not be geolocalized and have not been added. Please make sure that the addresses are complete and correct."
                ),
            });
        }

        newLocationsList.forEach((location) => {
            delete location._id;
        });
        return newLocationsList;
    }

    apply({ editingElement, loadResult }) {
        editingElement.dataset.locationsList = JSON.stringify(loadResult);
    }

    getValue({ editingElement }) {
        return editingElement.dataset.locationsList;
    }
}

registry.category("website-plugins").add(StoreLocatorOptionPlugin.id, StoreLocatorOptionPlugin);
