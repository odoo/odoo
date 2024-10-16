import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const diacriticalMarksRegex = /[\u0300-\u036f]/g;

/** Put the feature name in lowercase and remove the accents */
function normalizeFeatureName(name) {
    return name.normalize("NFD").replace(diacriticalMarksRegex, "").toLowerCase();
}

export const geoJsonService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const geoJsonPromises = new Map();
        const geoJsonCache = new Map();

        let usaStatesMapping = undefined;
        let countriesMapping = undefined;

        let countriesMappingPromise = undefined;
        let usStatesMappingPromise = undefined;

        async function getRegionAndFetchMapping(region) {
            const featurePromise = fetchJsonFromServer(
                `/spreadsheet/static/topojson/${region}.topo.json`
            );
            const mappingPromise = region === "usa" ? getUsaStatesMapping() : getCountriesMapping();
            return Promise.all([featurePromise, mappingPromise]);
        }

        async function getUsaStatesMapping() {
            if (usaStatesMapping) {
                return usaStatesMapping;
            }
            if (usStatesMappingPromise) {
                return usStatesMappingPromise;
            }
            usStatesMappingPromise = orm
                .searchRead("res.country.state", [["country_id.code", "=", "US"]], ["name", "code"])
                .then((usStates) => {
                    const mapping = {};
                    for (const state of usStates) {
                        mapping[normalizeFeatureName(state.name)] = state.code;
                        mapping[normalizeFeatureName(state.code)] = state.code;
                    }
                    usaStatesMapping = mapping;
                    usStatesMappingPromise = undefined;
                    return mapping;
                })
                .catch((e) => {
                    console.error(e);
                    usaStatesMapping = {};
                    usStatesMappingPromise = undefined;
                    return {};
                });
            return usStatesMappingPromise;
        }

        async function getCountriesMapping() {
            if (countriesMapping) {
                return countriesMapping;
            }
            if (countriesMappingPromise) {
                return countriesMappingPromise;
            }
            countriesMappingPromise = orm
                .searchRead("res.country", [], ["name", "code"])
                .then((resCountries) => {
                    const mapping = {};
                    for (const country of resCountries) {
                        mapping[normalizeFeatureName(country.name)] = country.code;
                        mapping[normalizeFeatureName(country.code)] = country.code;
                    }
                    countriesMapping = mapping;
                    countriesMappingPromise = undefined;
                    return mapping;
                })
                .catch((e) => {
                    console.error(e);
                    countriesMapping = {};
                    countriesMappingPromise = undefined;
                    return {};
                });

            return countriesMappingPromise;
        }

        async function fetchJsonFromServer(url) {
            if (geoJsonCache.has(url)) {
                return geoJsonCache.get(url);
            }
            if (geoJsonPromises.has(url)) {
                return geoJsonPromises.get(url);
            }

            const promise = fetch(url, { method: "GET" })
                .then((res) => res.json())
                .then((geoJson) => {
                    geoJsonCache.set(url, geoJson);
                    geoJsonPromises.delete(url);
                    return geoJson;
                })
                .catch((e) => {
                    console.error(e);
                    geoJsonCache.set(url, { type: "FeatureCollection", features: [] });
                    geoJsonPromises.delete(url);
                    return geoJsonCache.get(url);
                });

            geoJsonPromises.set(url, promise);
            return promise;
        }

        const stateNameRegex = /(.*?)(\(.*\))?$/;

        return {
            getAvailableRegions: () => [
                { id: "world", label: _t("World"), defaultProjection: "mercator" },
                { id: "africa", label: _t("Africa"), defaultProjection: "mercator" },
                { id: "asia", label: _t("Asia"), defaultProjection: "mercator" },
                { id: "europe", label: _t("Europe"), defaultProjection: "mercator" },
                {
                    id: "north_america",
                    label: _t("North America"),
                    defaultProjection: "conicConformal",
                },
                { id: "usa", label: _t("United States"), defaultProjection: "albersUsa" },
                { id: "south_america", label: _t("South America"), defaultProjection: "mercator" },
            ],
            getTopoJson: async function (region) {
                const [topoJson] = await getRegionAndFetchMapping(region);
                return topoJson;
            },
            geoFeatureNameToId: function (region, name) {
                if (region === "usa") {
                    // State display names are appended with the country in odoo (e.g. "California (US)").
                    const match = name.match(stateNameRegex);
                    if (match) {
                        name = match[1].trim();
                    }
                }
                name = normalizeFeatureName(name);
                const mapping = region === "usa" ? usaStatesMapping : countriesMapping;
                return mapping?.[name];
            },
        };
    },
};

registry.category("services").add("geo_json_service", geoJsonService);
