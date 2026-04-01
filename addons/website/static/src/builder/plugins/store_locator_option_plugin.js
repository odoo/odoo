import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { STORE_LOCATOR_PARTNER_FIELDS } from "./store_locator_option";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { formatOpeningHours } from "@website/components/location_selector/utils";

class StoreLocatorOptionPlugin extends Plugin {
    static id = "storeLocatorOption";
    resources = {
        builder_actions: {
            AddLocationToStoreLocatorAction,
            HideLocationsOffscreenAction,
            RefreshStoreLocatorAction,
        },
        clean_for_save_processors: this.cleanForSave.bind(this),
    };

    cleanForSave(rootEl) {
        // Remove store_locator snippets without entries
        const storeLocatorSnippets = rootEl.querySelectorAll(".s_store_locator");
        storeLocatorSnippets.forEach((snippet) => {
            const locationList = JSON.parse(snippet.dataset.locationsList || "[]");
            if (locationList.length == 0) {
                snippet.remove();
            }
        });
    }
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

    clean() {}
}

async function batchGeolocalize(orm, locationsMap, IDsToUpdate) {
    // Calls geo_localize to update the coordinates of the partners
    await orm.call("res.partner", "geo_localize", [IDsToUpdate]);
    // Reads the new coordinates and copies them to the locations, replacing
    // the old coordinates
    const coordinatesData = await orm.read("res.partner", IDsToUpdate, [
        "partner_latitude",
        "partner_longitude",
    ]);
    coordinatesData.forEach((location) => {
        const loc = locationsMap.get(location.id);
        loc.partner_latitude = location.partner_latitude;
        loc.partner_longitude = location.partner_longitude;
    });
}

async function batchUpdateCalendar(orm, locationsMap, IDsToUpdate) {
    const updateCalendarsProms = [];
    // Tries to retrieve the opening hours for IDsToUpdate
    let calendars;
    try {
        calendars = await orm.searchRead(
            "stock.warehouse",
            [["partner_id", "in", IDsToUpdate]],
            ["partner_id", "opening_hours"]
        );
    } catch (error) {
        // If website_sale_collect is not installed, the model does not exist
        if (!(error instanceof RPCError)) {
            throw error;
        }
    }
    if (calendars) {
        calendars.forEach((entry) => {
            const partner_id = entry.partner_id[0];
            const calendar_id = entry.opening_hours[0];
            updateCalendarsProms.push(
                orm
                    .searchRead(
                        "resource.calendar.attendance",
                        [
                            ["day_period", "!=", "lunch"],
                            ["calendar_id", "=", calendar_id],
                        ],
                        ["calendar_id", "dayofweek", "day_period", "hour_from", "hour_to"]
                    )
                    .then((opening_hours) => {
                        if (opening_hours.length) {
                            const loc = locationsMap.get(partner_id);
                            loc.opening_hours = formatOpeningHours(opening_hours);
                        }
                    })
            );
        });
    }
    await Promise.all(updateCalendarsProms);
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
        await batchGeolocalize(this.services.orm, locationsMap, newLocationsId);
        await batchUpdateCalendar(this.services.orm, locationsMap, newLocationsId);

        let newLocationsList = Array.from(locationsMap.values());
        const lenghtBeforeFiltering = newLocationsList.length;
        newLocationsList = newLocationsList.filter(
            (l) => l.partner_latitude && l.partner_longitude
        );
        const lengthAfterFiltering = newLocationsList.length;
        if (lenghtBeforeFiltering > lengthAfterFiltering) {
            this.services.dialog.add(ConfirmationDialog, {
                title: _t("Geolocation Failed"),
                body: _t(
                    "One or more selected locations could not be geolocalized and have not been added. Please make sure that the addresses are complete and correct."
                ),
            });
        }
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
        // it. Update opening hours when existing. Finally, save the new
        // data in this.el.dataset.
        const locationsList = JSON.parse(editingElement.dataset.locationsList || "[]");
        const locationsId = locationsList.map((entry) => entry.id);
        if (locationsId.length === 0) {
            return;
        }
        const locationsUpToDate = await this.services.orm.read(
            "res.partner",
            locationsId,
            STORE_LOCATOR_PARTNER_FIELDS
        );
        const locationsUpToDateMap = new Map(locationsUpToDate.map((loc) => [loc.id, loc]));

        // Update geolocations only if address has changed.
        const locationsToGeolocalize = [];
        locationsList.forEach((location) => {
            if (
                location.contact_address_inline !=
                locationsUpToDateMap.get(location.id).contact_address_inline
            ) {
                locationsToGeolocalize.push(location.id);
            }
        });
        if (locationsToGeolocalize.length) {
            await batchGeolocalize(this.services.orm, locationsUpToDateMap, locationsToGeolocalize);
        }

        // Update opening hours
        await batchUpdateCalendar(
            this.services.orm,
            locationsUpToDateMap,
            Array.from(locationsUpToDateMap.keys())
        );
        const newLocationsList = Array.from(locationsUpToDateMap.values());
        editingElement.dataset.locationsList = JSON.stringify(newLocationsList);
    }
}

registry.category("website-plugins").add(StoreLocatorOptionPlugin.id, StoreLocatorOptionPlugin);
