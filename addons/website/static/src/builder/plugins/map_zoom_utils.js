import { _t } from "@web/core/l10n/translation";
import { formatFloat } from "@web/core/utils/numbers";

const FEET_PER_MILE = 5280;

// Approximate distances shown for each map zoom level. Google Maps and
// OpenStreetMap share the same zoom scale, so both map snippets use them.
export const MAP_ZOOM_LEVELS = [
    { value: "21", km: 0.03, mi: 100 / FEET_PER_MILE },
    { value: "20", km: 0.075, mi: 200 / FEET_PER_MILE },
    { value: "19", km: 0.15, mi: 500 / FEET_PER_MILE },
    { value: "18", km: 0.3, mi: 0.25 },
    { value: "17", km: 0.5, mi: 0.5 },
    { value: "16", km: 1, mi: 1 },
    { value: "15", km: 2, mi: 1.5 },
    { value: "14", km: 5, mi: 3 },
    { value: "13", km: 10, mi: 5 },
    { value: "12", km: 20, mi: 10 },
    { value: "11", km: 40, mi: 25 },
    { value: "10", km: 75, mi: 50 },
    { value: "9", km: 150, mi: 100 },
    { value: "8", km: 300, mi: 200 },
    { value: "7", km: 500, mi: 500 },
    { value: "6", km: 1000, mi: 1000 },
    { value: "5", km: 2500, mi: 1500 },
    { value: "4", km: 5000, mi: 3000 },
    { value: "3", km: 10000, mi: 5000 },
    { value: "2", km: 20000, mi: 10000 },
];

function formatDistance(distance, unit) {
    return `${formatFloat(distance, { trailingZeros: false })} ${unit}`;
}

function formatMetricDistance(km) {
    return km < 1 ? formatDistance(km * 1000, _t("m")) : formatDistance(km, _t("km"));
}

function formatImperialDistance(mi) {
    return mi < 0.25
        ? formatDistance(Math.round(mi * FEET_PER_MILE), _t("ft"))
        : formatDistance(mi, _t("mi"));
}

/**
 * @param {string} distanceUnit "km" or "mi"
 * @param {number} [maxZoom] the highest zoom level the map provider supports
 * @returns {Array<{ value: string, label: string }>}
 */
export function getMapZoomLevels(distanceUnit, maxZoom = 21) {
    return MAP_ZOOM_LEVELS.filter((zoomLevel) => parseInt(zoomLevel.value) <= maxZoom).map(
        (zoomLevel) => ({
            value: zoomLevel.value,
            label:
                distanceUnit === "mi"
                    ? formatImperialDistance(zoomLevel.mi)
                    : formatMetricDistance(zoomLevel.km),
        })
    );
}
