import { describe, expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { animationFrame, press, queryFirst } from "@odoo/hoot-dom";

defineWebsiteModels();

const chartTemplate = (type, data) => `
    <div class="s_chart" data-snippet="s_chart" data-name="Chart" data-type="${type}" data-legend-position="none" data-tooltip-display="false" data-border-width="2"
        data-data='${JSON.stringify(data)}'>
        <p><br></p>
        <canvas style="box-sizing: border-box; display: block; height: 153px; width: 307px;" width="307" height="153"></canvas>
    </div>
`;

const getData = (type) => {
    const isPieChart = ["pie", "doughnut"].includes(type);
    return {
        labels: ["First", "Second", "Third"],
        datasets: [
            {
                key: "chart_dataset_1740645626800",
                label: "One",
                data: ["25", "75", "30"],
                backgroundColor: isPieChart ? ["o-color-1", "o-color-2", "o-color-3"] : "o-color-1",
                borderColor: isPieChart ? ["rgb(255, 127, 80)", "", ""] : "rgb(255, 127, 80)",
            },
            {
                key: "chart_dataset_1740646194838",
                label: "Two",
                data: ["10", "50", "45"],
                backgroundColor: isPieChart ? ["#4A7B8C", "#963512", "4CCE3A"] : "#4A7B8C",
                borderColor: isPieChart ? ["", "", ""] : "",
            },
        ],
    };
};

describe("Differences between pie & non-pie charts", () => {
    test("toggling to pie chart updates the dataset", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        let data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets[0].backgroundColor).toBeOfType("string");
        expect(data.datasets[0].borderColor).toBeOfType("string");
        await contains(":iframe .s_chart").click();
        await contains(".options-container .dropdown-toggle:contains('Bar Vertical')").click();
        await contains("[data-action-id=setChartType][data-action-value=pie]").click();
        expect(":iframe .s_chart").toHaveAttribute("data-type", "pie");
        data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets[0].backgroundColor).toHaveLength(3);
        expect(data.datasets[0].borderColor).toHaveLength(3);
    });
    test("toggling from pie to bar chart updates the dataset", async () => {
        const type = "pie";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        let data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets[0].backgroundColor).toHaveLength(3);
        expect(data.datasets[0].borderColor).toHaveLength(3);
        await contains(":iframe .s_chart").click();
        await contains(".options-container .dropdown-toggle:contains('Pie')").click();
        await contains("[data-action-id=setChartType][data-action-value=bar]").click();
        expect(":iframe .s_chart").toHaveAttribute("data-type", "bar");
        data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets[0].backgroundColor).toBeOfType("string");
        expect(data.datasets[0].borderColor).toBeOfType("string");
    });
    test("Bar chart => background color set as border on header input", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        await contains(":iframe .s_chart").click();
        await animationFrame();
        expect(
            ".options-container table [data-action-id=updateDatasetLabel]:first input"
        ).toHaveStyle({
            border: "2px solid rgb(217, 217, 217)",
        });
        expect(
            ".options-container table [data-action-id=updateDatasetValue]:first input"
        ).toHaveAttribute("style", "");
    });
    test("Pie chart => background color set as border on individual data inputs", async () => {
        const type = "pie";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        await contains(":iframe .s_chart").click();
        await animationFrame();
        expect(
            ".options-container table [data-action-id=updateDatasetValue]:first input"
        ).toHaveStyle({
            border: "2px solid rgb(217, 217, 217)",
        });
        expect(
            ".options-container table [data-action-id=updateDatasetLabel]:first input"
        ).toHaveAttribute("style", "");
    });
});

describe("Add & Delete buttons", () => {
    test("Hovering a data input displays the remove row/column buttons", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        await contains(":iframe .s_chart").click();
        expect(".options-container table [data-action-id=removeColumn]:first").toHaveClass(
            "visually-hidden-focusable"
        );
        expect(".options-container table [data-action-id=removeRow]:first").toHaveClass(
            "visually-hidden-focusable"
        );
        await contains(
            ".options-container table [data-action-id=updateDatasetValue]:first"
        ).hover();
        expect(".options-container table [data-action-id=removeColumn]:first").not.toHaveClass(
            "visually-hidden-focusable"
        );
        expect(".options-container table [data-action-id=removeRow]:first").not.toHaveClass(
            "visually-hidden-focusable"
        );
    });
    test("Focusing a data input displays the remove row/column buttons", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        await contains(":iframe .s_chart").click();
        expect(".options-container table [data-action-id=removeColumn]:first").toHaveClass(
            "visually-hidden-focusable"
        );
        expect(".options-container table [data-action-id=removeRow]:first").toHaveClass(
            "visually-hidden-focusable"
        );
        await contains(
            ".options-container table [data-action-id=updateDatasetValue]:first"
        ).focus();
        expect(".options-container table [data-action-id=removeColumn]:first").not.toHaveClass(
            "visually-hidden-focusable"
        );
        expect(".options-container table [data-action-id=removeRow]:first").not.toHaveClass(
            "visually-hidden-focusable"
        );
    });
    test("Adding a row updates the data and available cells", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        let data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.labels).toHaveLength(3);
        expect(data.datasets[0].data).toHaveLength(3);
        await contains(":iframe .s_chart").click();
        await contains(".options-container table [data-action-id=addRow]").click();
        data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.labels).toHaveLength(4);
        expect(data.datasets[0].data).toHaveLength(4);
        expect(".options-container table tbody tr").toHaveCount(5);
    });
    test("Adding a column updates the data and available cells", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        let data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets).toHaveLength(2);
        await contains(":iframe .s_chart").click();
        await contains(".options-container table [data-action-id=addColumn]").click();
        data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets).toHaveLength(3);
        expect(".options-container table thead tr th").toHaveCount(5);
        expect(".options-container table tbody tr:first td").toHaveCount(4);
    });
    test("Deleting a row updates the data and available cells", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        let data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.labels).toHaveLength(3);
        expect(data.datasets[0].data).toHaveLength(3);
        expect(data.labels[0]).toBe("First");
        await contains(":iframe .s_chart").click();
        await contains(".options-container table [data-action-id=removeRow]:first").click();
        data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.labels).toHaveLength(2);
        expect(data.datasets[0].data).toHaveLength(2);
        expect(data.labels[0]).toBe("Second");
        expect(".options-container table tbody tr").toHaveCount(3);
    });
    test("Deleting a column updates the data and available cells", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        let data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets).toHaveLength(2);
        expect(data.datasets[0].label).toBe("One");
        await contains(":iframe .s_chart").click();
        await contains(".options-container table [data-action-id=removeColumn]:first").click();
        data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets).toHaveLength(1);
        expect(".options-container table thead tr th").toHaveCount(3);
        expect(".options-container table tbody tr:first td").toHaveCount(2);
        expect(data.datasets[0].label).toBe("Two");
    });
    test("Cannot delete column if there is only 1 dataset", async () => {
        await setupWebsiteBuilder(
            chartTemplate("bar", {
                labels: ["First", "Second"],
                datasets: [
                    {
                        key: "chart_dataset_1740645626800",
                        label: "One",
                        data: ["25", "10"],
                        backgroundColor: "blue",
                        borderColor: "red",
                    },
                ],
            })
        );
        await contains(":iframe .s_chart").click();
        expect(".options-container table [data-action-id=removeColumn]").toHaveCount(0);
    });
    test("Cannot delete row if there is only 1 label", async () => {
        await setupWebsiteBuilder(
            chartTemplate("bar", {
                labels: ["First"],
                datasets: [
                    {
                        key: "chart_dataset_987654321",
                        label: "One",
                        data: ["25"],
                        backgroundColor: "blue",
                        borderColor: "",
                    },
                    {
                        key: "chart_dataset_123456789",
                        label: "Two",
                        data: ["10"],
                        backgroundColor: "blue",
                        borderColor: "",
                    },
                ],
            })
        );
        await contains(":iframe .s_chart").click();
        expect(".options-container table [data-action-id=removeRow]").toHaveCount(0);
    });
    test("Tab to a delete row button and enter to validate", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        await contains(":iframe .s_chart").click();
        let data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.labels).toHaveLength(3);
        expect(data.labels[0]).toBe("First");
        await contains(".options-container table tbody input").focus();
        await press("Tab");
        await press("Tab");
        await press("Tab");
        await press("Enter");
        data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.labels).toHaveLength(2);
        expect(data.labels[0]).toBe("Second");
    });
    test("Tab to a delete column button and enter to validate", async () => {
        const type = "bar";
        await setupWebsiteBuilder(chartTemplate(type, getData(type)));
        await contains(":iframe .s_chart").click();
        let data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets).toHaveLength(2);
        expect(data.datasets[0].label).toBe("One");
        await contains(".options-container table tbody tr:eq(2) input:last").focus();
        await press("Tab"); // remove row button
        await press("Tab"); // add row button
        await press("Tab");
        await press("Enter");
        data = JSON.parse(queryFirst(":iframe .s_chart").dataset.data);
        expect(data.datasets).toHaveLength(1);
        expect(data.datasets[0].label).toBe("Two");
    });
});

test("Focusing input displays related data color/data border colorpickers", async () => {
    const type = "bar";
    await setupWebsiteBuilder(chartTemplate(type, getData(type)));
    await contains(":iframe .s_chart").click();
    expect(".options-container [data-label='Dataset Color']").not.toHaveCount();
    expect(".options-container [data-label='Dataset Border']").not.toHaveCount();
    await contains(".options-container table tbody input:eq(1)").click();
    expect(".options-container [data-label='Dataset Color']").toBeVisible();
    expect(".options-container [data-label='Dataset Border']").toBeVisible();
});

test("CSS colors and CSS custom variables are correctly computed", async () => {
    const type = "bar";
    await setupWebsiteBuilder(chartTemplate(type, getData(type)), {
        styleContent: /*css*/ `
            html {
                --o-color-1: rgb(255, 0, 0);
                --o-color-2: rgb(0, 0, 255);
                --o-color-3: rgb(0, 255, 0);
            }`,
    });
    await contains(":iframe .s_chart").click();
    await contains(".options-container table tbody input:eq(1)").click();
    expect(".options-container [data-label='Dataset Color'] .o_we_color_preview").toHaveStyle({
        "background-color": "rgb(255, 0, 0)",
    });
    expect(".options-container [data-label='Dataset Border'] .o_we_color_preview").toHaveStyle({
        "background-color": "rgb(255, 127, 80)",
    });
});

test("Stacked option is only available with more than 1 dataset", async () => {
    const type = "bar";
    await setupWebsiteBuilder(chartTemplate(type, getData(type)));
    await contains(":iframe .s_chart").click();
    expect(".options-container [data-label='Stacked']").toBeVisible();
    await contains(".options-container table [data-action-id=removeColumn]").click();
    expect(".options-container [data-label='Stacked']").not.toHaveCount();
});
