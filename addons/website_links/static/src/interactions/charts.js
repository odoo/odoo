import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export const createBarChart = function (selector, beginDateA, endDateA, dates) {
    const el = document.querySelector(selector);

    let beginDate = beginDateA.startOf("day");
    let endDate = endDateA.startOf("day");
    if (beginDate.toISO() === endDate.toISO()) {
        endDate = endDate.plus({ days: 1 });
    }
    const numberOfDays = endDate.diff(beginDate).as("days");

    // Fill data for each day (with 0 click for days without data)
    const clicksArray = [];
    for (let i = 0; i <= numberOfDays; i++) {
        const dateKey = beginDate.toFormat("yyyy-MM-dd");
        clicksArray.push([dateKey, (dateKey in dates) ? dates[dateKey] : 0]);
        beginDate = beginDate.plus({ days: 1 });
    }

    let nbClicks = 0;
    const data = [];
    const labels = [];
    clicksArray.forEach(function (pt) {
        nbClicks += pt[1];
        data.push(pt[1]);
        labels.push(pt[0]);
    });

    const titleEl = el.querySelector(".title");
    titleEl.textContent = _t("%(clicks)s clicks", { clicks: nbClicks });

    const config = {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                data: data,
                fill: "start",
                label: _t("# of clicks"),
                backgroundColor: "#ebf2f7",
                borderColor: "#6aa1ca",

            }],
        },
        options: {
            scales: {
                y: {
                    ticks: {
                        callback: function (value) {
                            if (Number.isInteger(value)) {
                                return value;
                            }
                        },
                    }
                }
            }
        }
    };
    const canvasEl = el.querySelector("canvas");
    new Chart(canvasEl.getContext("2d"), config);
}

export const createPieChart = function (selector, countryData) {
    const el = document.querySelector(selector);

    // Process country data to fit into the ChartJS scheme
    const data = [];
    const labels = [];
    for (let i = 0; i < countryData.length; i++) {
        const countryName = countryData[i]["country_id"]
            ? countryData[i]["country_id"][1]
            : _t("Undefined");
        data.push(countryData[i]["country_id_count"]);
        labels.push(countryName + " (" + countryData[i]["country_id_count"] + ")");
    }

    // Set title
    const titleEl = el.querySelector(".title");
    titleEl.textContent = _t("%(count)s countries", { count: countryData.length });

    const config = {
        type: "pie",
        data: {
            labels: labels,
            datasets: [{
                data: data,
                label: countryData.length > 0 ? countryData[0].key : _t("No data"),
            }]
        },
        options: {
            aspectRatio: 2,
        },
    };
    const canvasEl = el.querySelector("canvas");
    new Chart(canvasEl.getContext("2d"), config);
}

export class Charts extends Interaction {
    static selector = ".o_website_links_chart";

    setup() {
        this.animating_copy = false;
        this.charts = {};
        this.links_domain = ["link_id", "=", parseInt(document.querySelector("#link_id").value)];
    }

    async willStart() {
        const proms = [];
        proms.push(this.getTotalClicks());
        proms.push(this.getClicksByDay());
        proms.push(this.getClicksByCountry());
        proms.push(this.getLastWeekClicksByCountry());
        proms.push(this.getLastMonthClicksByCountry());
        proms.push(loadBundle("web.chartjs_lib"));
        this.results = await Promise.all(proms);
    }

    start() {
        const totalClicks = this.results[0];
        const clicksByDay = this.results[1];
        const clicksByCountry = this.results[2];
        const lastWeekClicksByCountry = this.results[3];
        const lastMonthClicksByCountry = this.results[4];

        const noDataMessage = _t("There is no data to show");
        if (!totalClicks) {
            const allTimeCharts = document.querySelector("#all_time_charts");
            const lastMonthCharts = document.querySelector("#last_month_charts");
            const lastWeekCharts = document.querySelector("#last_week_charts");
            this.insert(noDataMessage, allTimeCharts, "afterbegin");
            this.insert(noDataMessage, lastMonthCharts, "afterbegin");
            this.insert(noDataMessage, lastWeekCharts, "afterbegin");
            return;
        }

        const formattedClicksByDay = {};

        let beginDate;
        for (var i = 0; i < clicksByDay.length; i++) {
            // This is a trick to get the date without the local formatting.
            // We can't simply do .locale("en") because some Odoo languages
            // are not supported by moment.js (eg: Arabic Syria).
            // FIXME this now uses luxon, check if this is still needed? Probably can be replaced by deserializeDate
            const date = DateTime.fromFormat(
                clicksByDay[i]["__domain"].find((el) => el.length && el.includes(">="))[2]
                    .split(" ")[0], "yyyy-MM-dd"
            );
            if (i === 0) {
                beginDate = date;
            }
            formattedClicksByDay[date.setLocale("en").toFormat("yyyy-MM-dd")] =
                clicksByDay[i]["create_date_count"];
        }

        const now = DateTime.now();

        // Process bar charts
        this.charts.all_time_bar = new createBarChart(
            "#all_time_clicks_chart", beginDate, now, formattedClicksByDay);
        this.charts.last_month_bar = new createBarChart(
            "#last_month_clicks_chart", now.minus({ days: 30 }), now, formattedClicksByDay);
        this.charts.last_week_bar = new createBarChart(
            "#last_week_clicks_chart", now.minus({ days: 7 }), now, formattedClicksByDay);

        // Process pie charts
        this.charts.all_time_pie = new createPieChart(
            "#all_time_countries_charts", clicksByCountry);
        this.charts.last_month_pie = new createPieChart(
            "#last_month_countries_charts", lastMonthClicksByCountry);
        this.charts.last_week_pie = new createPieChart(
            "#last_week_countries_charts", lastWeekClicksByCountry);


        const chartsContainerEl = document.querySelector("#all_time_countries_charts").parentElement
        const rowWidth = chartsContainerEl.getBoundingClientRect().width;
        const chartCanvas = document
            .querySelector("#all_time_countries_charts,last_month_countries_charts,last_week_countries_charts")
            .querySelector("canvas");
        chartCanvas.height = Math.max(clicksByCountry.length * (rowWidth > 750 ? 1 : 2), 20) + "em";
    }

    getTotalClicks() {
        return this.services.orm.searchCount(
            "link.tracker.click",
            [this.links_domain],
        );
    }

    getClicksByDay() {
        return this.services.orm.readGroup(
            "link.tracker.click",
            [this.links_domain],
            ["create_date"],
            ["create_date:day"],
        );
    }

    getClicksByCountry() {
        return this.services.orm.readGroup(
            "link.tracker.click",
            [this.links_domain],
            ["country_id"],
            ["country_id"],
        );
    }

    getLastWeekClicksByCountry() {
        // 7 days * 24 hours * 60 minutes * 60 seconds * 1000 milliseconds.
        const aWeekAgoDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        // Convert to date in the format YYYY-MM-DD.
        const aWeekAgoString = aWeekAgoDate.toISOString().split("T")[0];
        return this.services.orm.readGroup(
            "link.tracker.click",
            [this.links_domain, ["create_date", ">", aWeekAgoString]],
            ["country_id"],
            ["country_id"],
        );
    }

    getLastMonthClicksByCountry() {
        // 30 days * 24 hours * 60 minutes * 60 seconds * 1000 milliseconds.
        const aMonthAgoDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        // Convert to date in the format YYYY-MM-DD.
        const aMonthAgoString = aMonthAgoDate.toISOString().split("T")[0];
        return this.services.orm.readGroup(
            "link.tracker.click",
            [this.links_domain, ["create_date", ">", aMonthAgoString]],
            ["country_id"],
            ["country_id"],
        );
    }
}

registry
    .category("public.interactions")
    .add("website_links.charts", Charts);
