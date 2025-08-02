import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class StoreLocatorOptionPlugin extends Plugin {
    static id = "storeLocatorOption";
    resources = {
        builder_options: [
            {
                template: "website.storeLocatorOption",
                selector: ".s_store_locator",
                editableOnly: false,
            },
        ],
        builder_actions: {
            storeLocatorDataAttributeTogglerAction,
            storeLocatorMapUpdateSrcAction,
        },
    };
}

export class storeLocatorDataAttributeTogglerAction extends BuilderAction {
    static id = "storeLocatorDataAttributeToggler";
    isApplied({ editingElement, params: { mainParam } }) {
        return editingElement.hasAttribute(mainParam)
            ? editingElement.attributes[mainParam].nodeValue === "true"
            : editingElement.setAttribute(mainParam, "false");
    }
    apply({ editingElement, params: { mainParam } }) {
        editingElement.attributes[mainParam].nodeValue = "true";
    }
    clean({ editingElement, params: { mainParam } }) {
        editingElement.attributes[mainParam].nodeValue = "false";
    }
}

export class storeLocatorMapUpdateSrcAction extends BuilderAction {
    static id = "storeLocatorMapUpdateSrc";
    async apply({ editingElement, params: { mainParam } }) {
        const selectedLocations = JSON.parse(
            editingElement.attributes["data-render-list-items"].nodeValue
        );
        if (selectedLocations) {
            await this.fetchGeoLoc(selectedLocations, mainParam === "force");
            await this.fetchOpeningTimes(selectedLocations);
            editingElement.setAttribute(
                "data-render-list-items",
                JSON.stringify(selectedLocations)
            );
        }
    }

    async fetchGeoLoc(locations, forceNew = false) {
        for (const location of locations) {
            if (forceNew || (!location["partner_latitude"] && !location["partner_longitude"])) {
                const addr = encodeURIComponent(
                    location["contact_address_complete"]
                        ? location["contact_address_complete"].replace(/[/,]/g, " ")
                        : [location["street"], location["city"], location["zip"]]
                              .join(" ")
                              .replace(/[/,]/g, " ")
                );
                const response = await this.services.http.get(
                    `https://nominatim.openstreetmap.org/search?q=${addr}&format=jsonv2`
                );
                if (response[0]) {
                    location["partner_latitude"] = parseFloat(response[0]["lat"]);
                    location["partner_longitude"] = parseFloat(response[0]["lon"]);
                    this.services.orm.write("res.partner", [location.id], {
                        partner_latitude: location["partner_latitude"],
                        partner_longitude: location["partner_longitude"],
                    });
                }
            }
        }
    }

    async fetchOpeningTimes(locations) {
        if (
            (
                await this.services.orm.search("ir.module.module", [
                    ["name", "=", "website_sale_collect"],
                    ["state", "=", "installed"],
                ])
            ).length > 0
        ) {
            var opening_hours_formats = [];
            const weekArrayStructure = {
                0: [],
                1: [],
                2: [],
                3: [],
                4: [],
                5: [],
                6: [],
            };
            await this.services.orm
                .searchRead(
                    "resource.calendar.attendance",
                    [["day_period", "!=", "lunch"]],
                    ["calendar_id", "dayofweek", "day_period", "hour_from", "hour_to"]
                )
                .then(function (values) {
                    for (
                        var i = 0;
                        i <=
                        values
                            .map(({ calendar_id }) => calendar_id[0])
                            .reduce((max, curr) => (curr > max ? curr : max), 0);
                        i++
                    ) {
                        opening_hours_formats.push(weekArrayStructure);
                    }
                    for (const value of values) {
                        var hoursFromConverter = new Date(0);
                        var hoursToConverter = new Date(0);
                        hoursFromConverter.setSeconds(value.hour_from * 3600);
                        hoursToConverter.setSeconds(value.hour_to * 3600);
                        opening_hours_formats[value.calendar_id[0]][value.dayofweek][
                            value.day_period == "morning" ? 0 : 1
                        ] =
                            hoursFromConverter.toISOString().substring(11, 16) +
                            " - " +
                            hoursToConverter.toISOString().substring(11, 16);
                    }
                });
            await this.services.orm
                .searchRead("stock.warehouse", [], ["partner_id", "opening_hours"])
                .then(function (values) {
                    for (const value of values) {
                        for (var location of locations) {
                            if (location.id == value.partner_id[0]) {
                                location.opening_hours =
                                    opening_hours_formats[value.opening_hours[0]];
                            }
                        }
                    }
                });
        }
    }
}

registry.category("website-plugins").add(StoreLocatorOptionPlugin.id, StoreLocatorOptionPlugin);
