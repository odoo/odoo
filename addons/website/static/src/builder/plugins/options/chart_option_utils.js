import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { isCSSColor } from "@web/core/utils/colors";

export const DATASET_KEY_PREFIX = "chart_dataset_";

export function getColor(color, win, doc) {
    if (!color) {
        return "";
    }
    return isCSSColor(color)
        ? color
        : getCSSVariableValue(color, win.getComputedStyle(doc.documentElement));
}

export function randomColor() {
    return "#" + ("00000" + ((Math.random() * (1 << 24)) | 0).toString(16)).slice(-6).toUpperCase();
}

export function addChartColumn(data, isPieChart, key = DATASET_KEY_PREFIX + Date.now()) {
    const fillDatasetArray = (value) => Array(data.labels.length).fill(value);
    data.datasets.push({
        key,
        label: "",
        data: fillDatasetArray(0),
        backgroundColor: isPieChart ? data.labels.map(() => randomColor()) : randomColor(),
        borderColor: isPieChart ? fillDatasetArray("") : "",
    });
}

export function addChartRow(data, isPieChart) {
    data.labels.push("");
    data.datasets.forEach((dataset) => {
        dataset.data.push(0);
        if (isPieChart) {
            dataset.backgroundColor.push(randomColor());
            dataset.borderColor.push("");
        }
    });
}
