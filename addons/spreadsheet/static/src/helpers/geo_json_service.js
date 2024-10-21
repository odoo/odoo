import { useService } from "@web/core/utils/hooks";

export function useSpreadsheetGeoService() {
    const orm = useService("orm");
    return {
        getAvailableRegions: async function () {
            return [
                { id: "world", label: "World", defaultProjection: "mercator" },
                { id: "usa", label: "United States", defaultProjection: "albersUsa" },
                { id: "europe", label: "Europe", defaultProjection: "mercator" },
            ];
        },
        getTopoJson: async function (region) {
            return await fetchJsonFromServer(`/spreadsheet/static/topojson/${region}.topo.json`);
        },
        geoFeatureNameToId: async function (region, name) {
            name = normalizeFeatureName(name);
            const mapping = await getFeatureIdMapping(orm, region);
            return mapping?.[name];
        },
    };
}

const featureMappingCache = new Map();
let countriesMappingPromise = undefined;
let usStatesMappingPromise = undefined;

async function getFeatureIdMapping(orm, region) {
    if (featureMappingCache.has(region)) {
        return featureMappingCache.get(region);
    }

    if (region === "usa") {
        if (usStatesMappingPromise) {
            return usStatesMappingPromise;
        }
        usStatesMappingPromise = orm
            .searchRead("res.country.state", [["country_id.code", "=", "US"]], ["name", "code"])
            .then((usStates) => {
                const mapping = {};
                for (const state of usStates) {
                    mapping[normalizeFeatureName(state.name)] = state.code;
                }
                featureMappingCache.set(region, mapping);
                return featureMappingCache.get(region);
            })
            .catch((e) => {
                console.error(e);
                featureMappingCache.set(region, {});
            })
            .finally(() => {
                usStatesMappingPromise = undefined;
            });
        return usStatesMappingPromise;
    }

    if (countriesMappingPromise) {
        return countriesMappingPromise;
    }
    countriesMappingPromise = Promise.all([
        fetchJsonFromServer("/spreadsheet/static/topojson/world_country_iso_mapping.json"),
        orm.searchRead("res.country", [], ["name", "code"]),
    ])
        .then(([baseMapping, resCountries]) => {
            for (const country of resCountries) {
                baseMapping[country.code]?.push(country.name);
            }
            featureMappingCache.set(region, inverseMapping(baseMapping));
            return featureMappingCache.get(region);
        })
        .catch((e) => {
            console.error(e);
            featureMappingCache.set(region, {});
        })
        .finally(() => {
            countriesMappingPromise = undefined;
        });

    return countriesMappingPromise;
}

const diacriticalMarksRegex = /[\u0300-\u036f]/g;

/** Put the feature name in lowercase and remove the accents */
function normalizeFeatureName(name) {
    return name.normalize("NFD").replace(diacriticalMarksRegex, "").toLowerCase();
}

const currentPromises = new Map();
const cache = new Map();

async function fetchJsonFromServer(url) {
    if (cache.has(url)) {
        return cache.get(url);
    }
    if (currentPromises.has(url)) {
        return currentPromises.get(url);
    }

    const promise = fetch(url, { method: "GET" })
        .then((res) => res.json())
        .then((json) => {
            cache.set(url, json);
            return json;
        })
        .catch((e) => {
            cache.set(url, {});
            console.error(e);
        })
        .finally(() => {
            currentPromises.delete(url);
        });

    currentPromises.set(url, promise);
    return promise;
}

function inverseMapping(mapping) {
    const inverse = {};
    for (const key in mapping) {
        for (const value of mapping[key]) {
            inverse[normalizeFeatureName(value)] = key;
        }
    }
    return inverse;
}
