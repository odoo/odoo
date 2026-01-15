import { Interaction } from "@web/public/interaction";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
const { DateTime } = luxon;

class WebsiteLinksCharts extends Interaction {
    static selector = ".o_website_links_chart";
    dynamicContent = {
        "#all_time_charts, #last_month_charts, #last_week_charts": {
            "t-att-class": () => ({ "d-none": !!this.error }),
        },
        ".website_links_charts_error": {
            "t-out": () => this.error || "",
            "t-att-class": () => ({ "d-none": !this.error }),
        },
        "#all_time_clicks_chart > .title": {
            "t-out": () => `${this.numAllTimeClicks} ${_t("clicks")}`,
        },
        "#last_month_clicks_chart > .title": {
            "t-out": () => `${this.numLastMonthClicks} ${_t("clicks")}`,
        },
        "#last_week_clicks_chart > .title": {
            "t-out": () => `${this.numLastWeekClicks} ${_t("clicks")}`,
        },
        "#all_time_countries_charts > .title,\
         #last_month_countries_charts > .title,\
         #last_week_countries_charts > .title": {
            "t-out": (el) =>
                `${this.pieChartsData[el.parentNode.id].numCountries} ${_t("countries")}`,
        },
        "#all_time_countries_charts, #last_month_countries_charts, #last_week_countries_charts": {
            "t-att-style": (el) => ({
                height: `${Math.max(
                    this.pieChartsData[el.id].data.length * (this.chartWidth > 750 ? 1 : 2),
                    20
                )}em`,
            }),
        },
    };

    setup() {
        this.orm = this.services.orm;
        const linkId = parseInt(this.el.querySelector("#link_id").value);
        this.error = null;
        this.linksDomain = ["link_id", "=", linkId];
        this.totalClicks = [];
        this.clicksByDay = [];
        this.pieChartsData = {
            all_time_countries_charts: {
                fetch: this.getClicksByCountry.bind(this),
                data: [],
                numCountries: 0,
            },
            last_month_countries_charts: {
                fetch: this.getLastMonthClicksByCountry.bind(this),
                data: [],
                numCountries: 0,
            },
            last_week_countries_charts: {
                fetch: this.getLastWeekClicksByCountry.bind(this),
                data: [],
                numCountries: 0,
            },
        };
        this.chartWidth = this.el.querySelector(
            `#${Object.keys(this.pieChartsData)[0]}`
        ).scrollWidth;
    }

    async willStart() {
        this.totalClicks = await this.getTotalClicks();
        if (!this.totalClicks) {
            this.error = _t("There is no data to show");
            return;
        }
        this.clicksByDay = await this.getClicksByDay();
        for (const pieChartData of Object.values(this.pieChartsData)) {
            pieChartData.data = await pieChartData.fetch();
        }
        await loadBundle("web.chartjs_lib");
    }

    start() {
        if (!this.totalClicks) {
            return;
        }
        const formattedClicksByDay = {};
        let beginDate;
        for (let i = 0; i < this.clicksByDay.length; i++) {
            const date = deserializeDate(this.clicksByDay[i]["create_date:day"][0]);
            if (i === 0) {
                beginDate = date;
            }
            formattedClicksByDay[date.setLocale("en").toFormat("yyyy-MM-dd")] =
                this.clicksByDay[i]["__count"];
        }
        const endDate = DateTime.now();
        this.numAllTimeClicks = this.createLineChart(
            "#all_time_clicks_chart",
            beginDate,
            endDate,
            formattedClicksByDay
        );
        beginDate = endDate.minus({ days: 30 });
        this.numLastMonthClicks = this.createLineChart(
            "#last_month_clicks_chart",
            beginDate,
            endDate,
            formattedClicksByDay
        );
        beginDate = endDate.minus({ days: 7 });
        this.numLastWeekClicks = this.createLineChart(
            "#last_week_clicks_chart",
            beginDate,
            endDate,
            formattedClicksByDay
        );

        for (const pieChartId of Object.keys(this.pieChartsData)) {
            const pieChartData = this.pieChartsData[pieChartId];
            pieChartData.numCountries = this.createPieChart(`#${pieChartId}`, pieChartData.data);
        }
        this.updateContent();
    }

    createPieChart(selector, data) {
        const labels = [];
        const formattedData = [];
        for (const countryData of data) {
            const countryName = countryData["country_id"]
                ? countryData["country_id"][1]
                : _t("Undefined");
            labels.push(`${countryName} (${countryData["__count"]})`);
            formattedData.push(countryData["__count"]);
        }
        const config = {
            type: "pie",
            data: {
                labels,
                datasets: [
                    {
                        data: formattedData,
                        label: _t("# of clicks"),
                    },
                ],
            },
            options: {
                aspectRatio: 2,
                responsive: true,
                maintainAspectRatio: false,
            },
        };
        const containerEl = this.el.querySelector(selector);
        const canvasEl = containerEl.querySelector("canvas");
        const context = canvasEl.getContext("2d");
        new Chart(context, config);
        return formattedData.length;
    }

    createLineChart(selector, beginDate, endDate, dates) {
        const containerEl = this.el.querySelector(selector);
        beginDate = beginDate.startOf("day");
        endDate = endDate.startOf("day");
        if (beginDate.toISO() === endDate.toISO()) {
            endDate = endDate.plus({ days: 1 });
        }
        const numDays = Math.ceil(endDate.diff(beginDate).as("days"));
        let totalClicks = 0;
        const data = [];
        const labels = [];
        let currentDate = beginDate;
        for (let i = 0; i <= numDays; i++) {
            const dateKey = currentDate.toFormat("yyyy-MM-dd");
            labels.push(dateKey);
            const numClicks = dateKey in dates ? dates[dateKey] : 0;
            data.push(numClicks);
            totalClicks += numClicks;
            currentDate = currentDate.plus({ days: 1 });
        }
        const config = {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        data,
                        fill: "start",
                        label: _t("# of clicks"),
                        backgroundColor: "#ebf2f7",
                        borderColor: "#6aa1ca",
                    },
                ],
            },
            options: {
                scales: {
                    y: {
                        ticks: {
                            callback: (value) => {
                                if (Number.isInteger(value)) {
                                    return value;
                                }
                            },
                        },
                    },
                },
            },
        };
        const canvasEl = containerEl.querySelector("canvas");
        const context = canvasEl.getContext("2d");
        new Chart(context, config);
        return totalClicks;
    }

    getTotalClicks() {
        return this.orm.searchCount("link.tracker.click", [this.linksDomain]);
    }

    getClicksByDay() {
        return this.orm.formattedReadGroup(
            "link.tracker.click",
            [this.linksDomain],
            ["create_date:day"],
            ["__count"]
        );
    }

    getClicksByCountry() {
        return this.orm.formattedReadGroup(
            "link.tracker.click",
            [this.linksDomain],
            ["country_id"],
            ["__count"]
        );
    }

    getLastWeekClicksByCountry() {
        // 7 days * 24 hours * 60 minutes * 60 seconds * 1000 milliseconds.
        const aWeekAgoDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        // get the date in the format YYYY-MM-DD.
        const aWeekAgoString = aWeekAgoDate.toISOString().split("T")[0];
        return this.orm.formattedReadGroup(
            "link.tracker.click",
            [this.linksDomain, ["create_date", ">", aWeekAgoString]],
            ["country_id"],
            ["__count"]
        );
    }

    getLastMonthClicksByCountry() {
        // 30 days * 24 hours * 60 minutes * 60 seconds * 1000 milliseconds.
        const aMonthAgoDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        // get the date in the format YYYY-MM-DD.
        const aMonthAgoString = aMonthAgoDate.toISOString().split("T")[0];
        return this.orm.formattedReadGroup(
            "link.tracker.click",
            [this.linksDomain, ["create_date", ">", aMonthAgoString]],
            ["country_id"],
            ["__count"]
        );
    }
}

registry
    .category("public.interactions")
    .add("website_links.WebsiteLinksCharts", WebsiteLinksCharts);
