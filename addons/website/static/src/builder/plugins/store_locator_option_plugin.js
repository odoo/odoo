import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { STORE_LOCATOR_PARTNER_FIELDS } from "./store_locator_option";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { getEnabledOptionalFields, locationBatchUtils } from "./store_locator_utils";

class StoreLocatorOptionPlugin extends Plugin {
    static id = "storeLocatorOption";
    resources = {
        builder_actions: {
            AddLocationToStoreLocatorAction,
            HideLocationsOffscreenAction,
            RefreshStoreLocatorAction,
            StoreLocatorOptionalFieldAction,
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
        await locationBatchUtils.readFields(
            this.services.orm,
            locationsMap,
            newLocationsId,
            getEnabledOptionalFields(editingElement)
        );

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

export class RefreshStoreLocatorAction extends BuilderAction {
    static id = "refreshStoreLocator";

    async apply({ editingElement }) {
        // Query the database and compare the current locations data with the
        // data saved in this.el.dataset. If an address changed, re-geolocalize
        // it. Update opening hours when existing. If a location does not exist
        // anymore in the database, remove it. Finally, save the new location
        // list in this.el.dataset.
        const locationsList = JSON.parse(editingElement.dataset.locationsList || "[]");
        const locationsId = locationsList.map((entry) => entry.id);
        if (locationsId.length === 0) {
            return;
        }
        const locationsUpToDate = await this.services.orm.read("res.partner", locationsId, [
            ...STORE_LOCATOR_PARTNER_FIELDS,
            ...getEnabledOptionalFields(editingElement),
        ]);
        const locationsUpToDateMap = new Map(locationsUpToDate.map((loc) => [loc.id, loc]));

        // Update geolocations only if address has changed.
        const locationsToGeolocalize = [];
        locationsList.forEach((location) => {
            const locationUpToDate = locationsUpToDateMap.get(location.id);
            if (
                locationUpToDate &&
                location.contact_address_inline !== locationUpToDate.contact_address_inline
            ) {
                locationsToGeolocalize.push(location.id);
            }
        });
        if (locationsToGeolocalize.length) {
            await locationBatchUtils.geolocalize(
                this.services.orm,
                locationsUpToDateMap,
                locationsToGeolocalize
            );
        }

        // Update opening hours
        await locationBatchUtils.updateCalendar(
            this.services.orm,
            locationsUpToDateMap,
            Array.from(locationsUpToDateMap.keys())
        );
        const newLocationsList = Array.from(locationsUpToDateMap.values());
        editingElement.dataset.locationsList = JSON.stringify(newLocationsList);
    }
}

// Optional field (see `STORE_LOCATOR_OPTIONAL_FIELDS`) are encoded into the
// page only when the user activates them. In this way:
// 1. The page does not show sensitive data (e.g. the phone number) if the
//    user does not select it.
// 2. The page does not become larger with unused data, mostly base64 images.
export class StoreLocatorOptionalFieldAction extends BuilderAction {
    static id = "storeLocatorOptionalField";

    async load({ editingElement, params: { mainParam: field } }) {
        const locationsList = JSON.parse(editingElement.dataset.locationsList || "[]");
        const locationsMap = new Map(locationsList.map((l) => [l.id, l]));
        await locationBatchUtils.readFields(
            this.services.orm,
            locationsMap,
            Array.from(locationsMap.keys()),
            [field]
        );
        return Array.from(locationsMap.values());
    }

    apply({ editingElement, loadResult }) {
        editingElement.dataset.locationsList = JSON.stringify(loadResult);
    }

    clean({ editingElement, params: { mainParam: field } }) {
        const locationsList = JSON.parse(editingElement.dataset.locationsList || "[]");
        locationsList.forEach((location) => {
            delete location[field];
        });
        editingElement.dataset.locationsList = JSON.stringify(locationsList);
    }
}

registry.category("website-plugins").add(StoreLocatorOptionPlugin.id, StoreLocatorOptionPlugin);
