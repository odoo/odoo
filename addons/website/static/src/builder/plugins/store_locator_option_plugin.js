import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { StoreLocatorOption, STORE_LOCATOR_PARTNER_FIELDS } from "./store_locator_option";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { formatOpeningHours } from "@website/components/location_selector/utils";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";

class StoreLocatorOptionPlugin extends Plugin {
    static id = "storeLocatorOption";
    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC_END, StoreLocatorOption)],
        builder_actions: {
            AddLocationToStoreLocatorAction,
            HideLocationsOffscreenAction,
            RefreshStoreLocatorAction,
        },
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    cleanForSave({ root }) {
        // Remove store_locator snippets without entries
        const storeLocatorSnippets = root.querySelectorAll(".s_store_locator");
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
    // locations could appear or hide and the list would change height). The
    // user can still undo this choice by acting on the "Height" option.
    apply({ editingElement }) {
        const classes = editingElement.classList;
        if (
            !classes.contains("o_half_screen_height") &&
            !classes.contains("o_full_screen_height")
        ) {
            this.previousHeightState = "auto";
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

export class AddLocationToStoreLocatorAction extends BuilderAction {
    static id = "addLocationToStoreLocator";

    async load({ editingElement, value }) {
        const newLocationsList = JSON.parse(value);
        const oldLocationsList = JSON.parse(editingElement.dataset.locationsList || "[]");
        if (oldLocationsList.length < newLocationsList.length) {
            // We are adding a location (could be called when removing an item too)
            const newLocation = newLocationsList.at(-1);
            if (!newLocation.partner_latitude && !newLocation.partner_longitude) {
                // If the new entry does not have geolocation yet, we geolocalize it now
                // (the geolocation data may have been added already by other modules)
                await this.services.orm.call("res.partner", "geo_localize", [newLocation.id]);
                const newLocationCoordinates = await this.services.orm.read(
                    "res.partner",
                    [newLocation.id],
                    ["partner_latitude", "partner_longitude"]
                );
                newLocation.partner_latitude = newLocationCoordinates[0].partner_latitude;
                newLocation.partner_longitude = newLocationCoordinates[0].partner_longitude;
            }
            let calendarId;
            try {
                calendarId = await this.services.orm.searchRead(
                    "stock.warehouse",
                    [["partner_id", "=", newLocation.id]],
                    ["opening_hours"]
                );
            } catch (error) {
                // If website_sale_collect is not installed, the model does not exist
                if (!(error instanceof RPCError)) {
                    throw error;
                }
            }
            if (calendarId?.length) {
                const newLocationCalendar = await this.services.orm.searchRead(
                    "resource.calendar.attendance",
                    [
                        ["day_period", "!=", "lunch"],
                        ["calendar_id", "=", calendarId[0].opening_hours[0]],
                    ],
                    ["calendar_id", "dayofweek", "day_period", "hour_from", "hour_to"]
                );
                if (newLocationCalendar.length) {
                    newLocation.opening_hours = formatOpeningHours(newLocationCalendar);
                }
            }
        }
        return { oldLocationsList, newLocationsList };
    }

    apply({ editingElement, loadResult }) {
        const { oldLocationsList, newLocationsList } = loadResult;
        if (oldLocationsList.length < newLocationsList.length) {
            const newLocation = newLocationsList.at(-1);
            if (!newLocation.partner_latitude && !newLocation.partner_longitude) {
                // If geolocation failed, we display an error message and do not add the entry
                this.services.dialog.add(ConfirmationDialog, {
                    title: _t("Geolocation Failed"),
                    body: _t(
                        "This location could not be geolocalized. Please make sure that the address is complete and correct."
                    ),
                });
                return;
            }
        }
        editingElement.dataset.locationsList = JSON.stringify(newLocationsList);
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
        const locationsUpToDateMap = new Map(
            locationsUpToDate.map((location) => [location.id, location])
        );

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
            await this.services.orm.call("res.partner", "geo_localize", locationsToGeolocalize);
            const coordinatesData = await this.services.orm.read(
                "res.partner",
                locationsToGeolocalize,
                ["partner_latitude", "partner_longitude"]
            );
            coordinatesData.forEach((location) => {
                const loc = locationsUpToDateMap.get(location.id);
                loc.partner_latitude = location.partner_latitude;
                loc.partner_longitude = location.partner_longitude;
            });
        }

        // Update opening hours
        const updateCalendarsProms = [];
        let calendars;
        try {
            calendars = await this.services.orm.searchRead(
                "stock.warehouse",
                [["partner_id", "in", locationsId]],
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
                    this.services.orm
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
                                const location = locationsUpToDateMap.get(partner_id);
                                location.opening_hours = formatOpeningHours(opening_hours);
                            }
                        })
                );
            });
            await Promise.all(updateCalendarsProms);
        }
        const newLocationsList = Array.from(locationsUpToDateMap.values());
        editingElement.dataset.locationsList = JSON.stringify(newLocationsList);
    }
}

registry.category("website-plugins").add(StoreLocatorOptionPlugin.id, StoreLocatorOptionPlugin);
