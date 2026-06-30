import { BuilderAction } from "@html_builder/core/builder_action";
import { ChartOption, DATASET_KEY_PREFIX, getColor } from "./chart_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } ChartOptionShared
 * @property { ChartOptionPlugin['isPieChart'] } isPieChart
 */

class ChartOptionPlugin extends Plugin {
    static id = "chartOptionPlugin";
    static dependencies = ["history"];
    static shared = ["isPieChart"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [ChartOption],
        so_content_addition_selector: [".s_chart"],
        builder_actions: {
            SetChartTypeAction,
            AddColumnAction,
            RemoveColumnAction,
            AddRowAction,
            RemoveRowAction,
            UpdateDatasetValueAction,
            UpdateDatasetLabelAction,
            UpdateLabelNameAction,
            setMinMaxAction,
            ColorChangeAction,
        },
    };

    isPieChart(editingElement) {
        return ["pie", "doughnut"].includes(editingElement.dataset.type);
    }
}

export class BaseChartAction extends BuilderAction {
    static id = "baseChart";
    static dependencies = ["chartOptionPlugin"];
    updateDOMData(editingElement, data) {
        editingElement.dataset.data = JSON.stringify(data);
    }

    getData(editingElement) {
        return JSON.parse(editingElement.dataset.data);
    }

    getMaxValue(editingElement) {
        const datasets = this.getData(editingElement).datasets;
        let dataValues;
        if (!editingElement.dataset.stacked) {
            dataValues = datasets.flatMap((set) => set.data.map((data) => parseInt(data) || 0));
        } else {
            dataValues = datasets.reduce((acc, set) => {
                const data = set.data.map((data) => parseInt(data) || 0);
                return acc.map((value, i) => value + data[i]);
            }, Array(datasets[0].data.length).fill(0));
        }
        return Math.ceil(Math.max(...dataValues) / 5) * 5;
    }

    isPieChart(editingElement) {
        return this.dependencies.chartOptionPlugin.isPieChart(editingElement);
    }

    getColor(color) {
        return getColor(color, this.window, this.document);
    }

    randomColor() {
        return (
            "#" + ("00000" + ((Math.random() * (1 << 24)) | 0).toString(16)).slice(-6).toUpperCase()
        );
    }
}

export class SetChartTypeAction extends BaseChartAction {
    static id = "setChartType";
    isApplied({ editingElement, value }) {
        return editingElement.dataset.type === value;
    }
    apply({ editingElement, value }) {
        editingElement.dataset.type = value;

        const data = this.getData(editingElement);
        if (this.isPieChart(editingElement)) {
            if (typeof data.datasets[0].backgroundColor === "string") {
                data.datasets.forEach((dataset) => {
                    dataset.backgroundColor = [dataset.backgroundColor];
                    dataset.borderColor = [dataset.borderColor];
                    for (let i = 1; i < data.labels.length; i++) {
                        dataset.backgroundColor.push(this.randomColor());
                        dataset.borderColor.push("");
                    }
                });
            }
        } else if (Array.isArray(data.datasets[0].backgroundColor)) {
            data.datasets.forEach((dataset) => {
                dataset.backgroundColor = dataset.backgroundColor[0];
                dataset.borderColor = dataset.borderColor[0];
            });
        }
        this.updateDOMData(editingElement, data);
    }
}
export class AddColumnAction extends BaseChartAction {
    static id = "addColumn";
    apply({ editingElement }) {
        const data = this.getData(editingElement);
        const fillDatasetArray = (value) => Array(data.labels.length).fill(value);

        const newDataset = {
            key: DATASET_KEY_PREFIX + Date.now(),
            label: "",
            data: fillDatasetArray(0),
            backgroundColor: this.isPieChart(editingElement)
                ? data.labels.map(() => this.randomColor())
                : this.randomColor(),
            borderColor: this.isPieChart(editingElement) ? fillDatasetArray("") : "",
        };
        data.datasets.push(newDataset);
        this.updateDOMData(editingElement, data);
    }
}
export class RemoveColumnAction extends BaseChartAction {
    static id = "removeColumn";
    apply({ editingElement, params: { mainParam: key } }) {
        const data = this.getData(editingElement);
        const toRemoveIndex = data.datasets.findIndex((dataset) => dataset.key === key);
        data.datasets.splice(toRemoveIndex, 1);
        this.updateDOMData(editingElement, data);
    }
}
export class AddRowAction extends BaseChartAction {
    static id = "addRow";
    apply({ editingElement }) {
        const data = this.getData(editingElement);
        data.labels.push("");
        data.datasets.forEach((dataset) => {
            dataset.data.push(0);
            if (this.isPieChart(editingElement)) {
                dataset.backgroundColor.push(this.randomColor());
                dataset.borderColor.push("");
            }
        });
        this.updateDOMData(editingElement, data);
    }
}
export class RemoveRowAction extends BaseChartAction {
    static id = "removeRow";
    apply({ editingElement, params: { mainParam: labelIndex } }) {
        const data = this.getData(editingElement);
        data.labels.splice(labelIndex, 1);
        data.datasets.forEach((dataset) => {
            dataset.data.splice(labelIndex, 1);
            if (this.isPieChart(editingElement)) {
                dataset.backgroundColor.splice(labelIndex, 1);
                dataset.borderColor.splice(labelIndex, 1);
            }
        });
        this.updateDOMData(editingElement, data);
    }
}
export class UpdateDatasetValueAction extends BaseChartAction {
    static id = "updateDatasetValue";
    getValue({ editingElement, params: { datasetKey, valueIndex } }) {
        const data = this.getData(editingElement);
        const targetDataset = data.datasets.find((dataset) => dataset.key === datasetKey);
        return targetDataset?.data[valueIndex] || 0;
    }
    apply({ editingElement, value, params: { datasetKey, valueIndex } }) {
        const data = this.getData(editingElement);
        const targetDataset = data.datasets.find((dataset) => dataset.key === datasetKey);
        targetDataset.data[valueIndex] = value;
        this.updateDOMData(editingElement, data);
    }
}
export class UpdateDatasetLabelAction extends BaseChartAction {
    static id = "updateDatasetLabel";
    getValue({ editingElement, params: { mainParam: datasetKey } }) {
        const data = this.getData(editingElement);
        const targetDataset = data.datasets.find((dataset) => dataset.key === datasetKey);
        return targetDataset?.label;
    }
    apply({ editingElement, value, params: { mainParam: datasetKey } }) {
        const data = this.getData(editingElement);
        const targetDataset = data.datasets.find((dataset) => dataset.key === datasetKey);
        targetDataset.label = value;
        this.updateDOMData(editingElement, data);
    }
}

export class UpdateLabelNameAction extends BaseChartAction {
    static id = "updateLabelName";
    getValue({ editingElement, params: { mainParam: labelIndex } }) {
        const data = this.getData(editingElement);
        return data.labels[labelIndex];
    }
    apply({ editingElement, value, params: { mainParam: labelIndex } }) {
        const data = this.getData(editingElement);
        data.labels[labelIndex] = value;
        this.updateDOMData(editingElement, data);
    }
}
export class setMinMaxAction extends BaseChartAction {
    static id = "setMinMax";
    getValue({ editingElement, params: { mainParam: type } }) {
        if (type === "min") {
            return parseInt(editingElement.dataset.ticksMin) || "";
        }
        if (type === "max") {
            return parseInt(editingElement.dataset.ticksMax) || "";
        }
    }
    apply({ editingElement, value, params: { mainParam: type } }) {
        let minValue, maxValue;
        let noMin = false;
        let noMax = false;
        if (type === "min") {
            minValue = parseInt(value);
            maxValue = parseInt(editingElement.dataset.ticksMax);
        }
        if (type === "max") {
            maxValue = parseInt(value);
            minValue = parseInt(editingElement.dataset.ticksMin);
        }
        if (isNaN(minValue)) {
            noMin = true;
            minValue = 0;
        }

        if (!isNaN(maxValue)) {
            if (maxValue < minValue) {
                [minValue, maxValue] = [maxValue, minValue];
                [noMin, noMax] = [noMax, noMin];
            } else if (maxValue === minValue) {
                minValue = minValue < 0 ? 2 * minValue : 0;
                maxValue = minValue < 0 ? 0 : 2 * maxValue;
            }
        } else {
            noMax = true;
            maxValue = this.getMaxValue(editingElement);
            // When max value is not given and min value is greater
            // than chart data values
            if (minValue > maxValue) {
                maxValue = minValue;
                [noMin, noMax] = [noMax, noMin];
            }
        }

        if (noMin) {
            delete editingElement.dataset.ticksMin;
        } else {
            editingElement.dataset.ticksMin = minValue;
        }
        if (noMax) {
            delete editingElement.dataset.ticksMax;
        } else {
            editingElement.dataset.ticksMax = maxValue;
        }
    }
}
export class ColorChangeAction extends BaseChartAction {
    static id = "colorChange";
    getValue({ editingElement, params: { type, datasetIndex, dataIndex } }) {
        const data = this.getData(editingElement);
        if (this.isPieChart(editingElement)) {
            // TODO: shouldn't getColor be done directly in BuilderColorPicker?
            return this.getColor(data.datasets[datasetIndex]?.[type][dataIndex]);
        } else {
            return this.getColor(data.datasets[datasetIndex]?.[type]);
        }
    }
    apply({ editingElement, value, params: { type, datasetIndex, dataIndex } }) {
        value = value.replace("var(--", "").replace(")", "");
        const data = this.getData(editingElement);
        if (this.isPieChart(editingElement)) {
            data.datasets[datasetIndex][type][dataIndex] = value;
        } else {
            data.datasets[datasetIndex][type] = value;
        }
        this.updateDOMData(editingElement, data);
    }
}

registry.category("website-plugins").add(ChartOptionPlugin.id, ChartOptionPlugin);
