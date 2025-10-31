/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { TimesheetTimer } from "@timesheet_grid/components/static_timesheet_form/static_timesheet_timer";
import { session } from "@web/session";

const { DateTime, Duration } = luxon;

export class ActivityWatchTimesheet extends Component {
    static components = {
        TimesheetTimer,
    };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            grouped: {},
            selected: null,
            selectedData: {},
            billableTimesheets: [],
            nonBillableTimesheets: [],
            totalTime: [],
            billableTime: 0.0,
            nonBillableTime: 0.0,
            billablePercentage: 0.0,
            nonBillablePercentage: 0.0,
        });

        onWillStart(async () => {
            await this.loadData();
            this.state.loading = false;
        });
    }

    extractBrowserWatcherActivityName(event) {
        const url = event.data.url;
        // only for test, this should be a config, and the user can adapt it to his need
        if (/^https?:\/\/(localhost|github\.com)/.test(url)) {
            event.name = "Coding (browser)";
            return true;
        }
        // in the config, we should have a sequence field, because order is important
        // like the example of overlap in calendar and planning apps
        // project and task in odoo url
        let match = url.match(/^https:\/\/www\.odoo\.com\/odoo\/project\/(\d+)\/tasks\/(\d+)$/);
        if (match) {
            event.name = "Working on project"; // should come from config
            event.project_id = match[1];
            event.task_id = match[2];
            return true;
        }

        // only project in odoo url
        match = url.match(/^https:\/\/www\.odoo\.com\/odoo\/project\/(\d+)$/);
        if (match) {
            event.project_id = match[1];
            return true;
        }

        if (url.includes("meet.google")) {
            event.name = "In a meeting";
            return true;
        }

        // Reading or composing email
        if (url.startsWith("https://mail.google.com")) {
            if (/#inbox/.test(url)) {
                event.name = "Reading Emails";
                return true;
            } else if (/compose=/.test(url)) {
                event.name = "composing email";
                return true;
            }
        }

        return false;
    }

    async getWatchers(baseUrl) {
        // get all available buckets
        const buckets = await fetch(`${baseUrl}/api/0/buckets/`).then((response) =>
            response.json()
        );

        // we will focus on:
        // - vsCode watcher
        // - window watcher (browser + computer) giving the app and the tab title
        // - browser extension watcher (giving the url which is not returned by the previous watcher)
        return Object.keys(buckets)
            .filter((key) =>
                ["aw-watcher-vscode", "aw-watcher-window", "aw-client-web"].includes(
                    buckets[key].client
                )
            )
            .map((key) => buckets[key]);
    }

    async loadAwEvents(baseUrl, watchers, start, end) {
        try {
            const requests = [];
            for (const watcher of watchers) {
                requests.push(
                    fetch(
                        `${baseUrl}/api/0/buckets/${watcher["id"]}/events?start=${start}&end=${end}`
                    )
                );
            }

            const responses = await Promise.all(requests);
            const failed = [];
            const res = {};

            for (let index = 0; index < requests.length; index++) {
                if (responses[index].ok) {
                    // assuming that you have one watcher per client for the poc (one browser extension, no 2 browsers opened with the extension)
                    const events = await Promise.resolve(responses[index].json());
                    const formatedEvents = [];
                    for (const event of events) {
                        if (watchers[index].client === "aw-watcher-vscode") {
                            event.name = "Programming In VS Code"; // should be done in config
                        } else if (watchers[index].client === "aw-client-web") {
                            const name = this.extractBrowserWatcherActivityName(event);
                            if (name === false) {
                                // skip event
                                continue;
                            }
                        }

                        if (event.duration === 0) {
                            continue;
                        }
                        event.start = DateTime.fromISO(event.timestamp);
                        event.stop = event.start.plus(
                            Duration.fromObject({ seconds: event.duration })
                        );
                        formatedEvents.push(event);
                    }

                    if (formatedEvents.length > 0) {
                        res[watchers[index].client] = formatedEvents;
                    }
                } else {
                    failed.push(responses[index]);
                }
            }

            if (res.length === 0) {
                if (failed.length === 0) {
                    return {};
                }

                this.notification.add(
                    _t(
                        "All watchers failed to return data, please try again or check they're running well on Activity watch via %(url)s",
                        {
                            url: baseUrl,
                        }
                    ),
                    {
                        type: "danger",
                    }
                );
                return {};
            }

            if (failed.length > 0) {
                this.notification.add(
                    _t(
                        "Some watchers failed to return data (%(watchers)s), please try again or check they're running well on Activity watch via %(url)s",
                        {
                            watchers: failed,
                            url: baseUrl,
                        }
                    ),
                    {
                        type: "warning",
                    }
                );
            }
            return res;
        } catch {
            this.notification.add(
                _t(
                    "Something went wrong getting data from Activity Watch, make sure to start the server with the right cors origins E.G ./aw-server --cors-origins http://localhost:8069"
                ),
                { type: "danger" }
            );
            return {};
        }
    }

    async loadData() {
        this.state.loading = true;

        // not for nesting, start => activitywatch/aw-server$ ./aw-server --cors-origins http://localhost:8069
        const baseUrl = "http://localhost:5600";
        const todayStart = new Date(new Date().setHours(0, 0, 0, 0)).toISOString();
        const todayEnd = new Date(new Date().setHours(23, 59, 59, 999)).toISOString();

        const watchers = await this.getWatchers(baseUrl);
        const events = await this.loadAwEvents(baseUrl, watchers, todayStart, todayEnd);
        if (events.length === 0) {
            return;
        }

        // we get planning slot and calendar events from odoo
        // (intervals where the user should be doing a slot for a project or on a calendar event for a customer ..)
        // then we get watchers with priority:
        // 1- vsCodeWatcher (or any other IDE extension, VSCODE for the POC as an example)
        // both browser and vsCodeWatcher get the info of the vsCode => info duplicated, so i decided to get it from the ide watcher as
        // it's better (only returining active moment on vsCode, not only opeining it even if no using)
        // 2- browser watcher for some key events
        // 2- a- odoo project app (which project / task from url))
        // 2- b- google meet (as an example, more generic most used meet tools
        // 3- reading and composing emails
        // 4- chatting on discord
        // 5- other events like google slides, ..

        // algo:
        // we're assuming that events for each watcher can't overlap and sorted (i can't use vsCode 2 times at the same moment)
        // => all events coming from EACH Activity Watch are sorted and don't overlap
        // planning slot (can technically overlap, but it doesn't make sens to work on 2 slots at the same time for our base case, businees analyst / ps tech)
        // BUT we still keep the info and we can treat it later by merging ranges
        // calendar events ranges can't overlap (i can't be in 2 places at the same time)

        // this way, we can construct our ranges
        // 1- ranges = []
        // 2- fill ranges with first (in terme of priority) non empty range (planning or events probably)
        // 3- we're assuming that they're sorted non overlapping
        // --------  --------   ---------- ---------
        // 4- iterate ranges list one by one, and append the intersection with gaps from ranges

        // ranges                           =  gap before |-------| gap 1 |-----------| gap 2 |-------------| gap after
        // list                             =      -------------------   -------            --------------------------
        // intersection to append to ranges =      -------        ----   -                  ---              ---------

        // once the final ranges is ready
        // if the range contains project AND/OR task info, everything coming after belongs to that context

        let ranges = await this.orm.call("account.analytic.line", "get_events", [[]]);
        for (const range of ranges) {
            range["start"] = deserializeDateTime(range["start"]);
            range["stop"] = deserializeDateTime(range["stop"]);
        }

        ranges = this.merge(ranges, events["aw-watcher-vscode"]);
        ranges = this.merge(ranges, events["aw-client-web"]);

        let prevProjectId = false;
        let prevTaskId = false;

        for (const range of ranges) {
            if (range.project_id || range.task_id) {
                prevProjectId = range.project_id;
                prevTaskId = range.task_id;
            }
            const duration = (range.stop - range.start) / 1000;
            const project = `${prevProjectId}_${prevTaskId}`;
            if (!(project in this.state.grouped)) {
                this.state.grouped[project] = {};
            }

            if (range.name in this.state.grouped[project]) {
                this.state.grouped[project][range.name] += duration;
            } else {
                this.state.grouped[project][range.name] = duration;
            }
        }

        await this.loadTimesheets(todayStart);
        this.state.loading = false;
    }

    async loadTimesheets(todayStart) {
        // get timesheets
        const fields = ["id", "name", "date", "project_id", "task_id", "unit_amount", "so_line"];
        const domain = [
            ["date", "=", todayStart.split("T")[0]],
            ["user_id", "=", session.user_id], // uid and user_id are both nor working to check the reason not working
        ];

        const timesheets = await this.orm.searchRead("account.analytic.line", domain, fields);

        // init to avoid accumulating
        this.state.billableTimesheets = [];
        this.state.nonBillableTimesheets = [];
        this.state.billableTime = 0;
        this.state.nonBillableTime = 0;
        this.state.totalTime = 0;

        for (const timesheet of timesheets) {
            if (timesheet.so_line) {
                this.state.billableTimesheets.push(timesheet);
                this.state.billableTime += timesheet.unit_amount;
            } else {
                this.state.nonBillableTimesheets.push(timesheet);
                this.state.nonBillableTime += timesheet.unit_amount;
            }
            this.state.totalTime += timesheet.unit_amount;
        }

        this.state.billablePercentage = (this.state.billableTime * 100) / this.state.totalTime;
        this.state.nonBillablePercentage =
            (this.state.nonBillableTime * 100) / this.state.totalTime;
    }

    merge(ranges, intervalsToInclude) {
        if (intervalsToInclude == null || intervalsToInclude.length === 0) {
            return ranges;
        }
        if (ranges.length === 0) {
            return intervalsToInclude;
        }
        const gaps = [];
        ranges.sort((a, b) => a.start - b.start);
        intervalsToInclude.sort((a, b) => a.start - b.start);

        // gap before first range
        if (intervalsToInclude[0].start < ranges[0].start) {
            gaps.push([intervalsToInclude[0].start, ranges[0].start]);
        }

        // gaps between ranges
        for (let i = 0; i < ranges.length - 1; i++) {
            if (ranges[i].stop < ranges[i + 1].start) {
                gaps.push([ranges[i].stop, ranges[i + 1].start]);
            }
        }

        // gap after last range
        if (
            intervalsToInclude[intervalsToInclude.length - 1].stop > ranges[ranges.length - 1].stop
        ) {
            gaps.push([
                ranges[ranges.length - 1].stop,
                intervalsToInclude[intervalsToInclude.length - 1].stop,
            ]);
        }

        const res = [...ranges];
        let j = 0;

        for (const gap of gaps) {
            // advance if intervalsToInclude[j] ends before the gap
            while (j < intervalsToInclude.length && intervalsToInclude[j].stop <= gap[0]) {
                j++;
            }

            if (j === intervalsToInclude.length) {
                break;
            }

            // skip if interval starts after the gap
            if (intervalsToInclude[j].start >= gap[1]) {
                continue;
            }

            // intersect interval with gap
            const interval = { ...intervalsToInclude[j] };
            interval.start = Math.max(gap[0], interval.start);
            interval.stop = Math.min(gap[1], interval.stop);

            res.push(interval);
        }

        // sort by start
        res.sort((a, b) => a.start - b.start);

        return res;
    }

    parseId(id) {
        const res = Number.parseInt(id);
        return isNaN(res) ? null : res;
    }

    isSuggestionClicked(groupKey, title) {
        return this.state.selected?.groupKey === groupKey && this.state.selected?.title === title;
    }

    getSuggestionParams(groupKey, title) {
        if (this.state.grouped[groupKey]?.[title] == null) {
            return false;
        }
        const ids = groupKey.split("_");
        let project_id = this.parseId(ids[0]);
        let task_id = this.parseId(ids[1]);
        // to fix, i need to get projects by id (the one we get from odoo url)
        // just for testing as i need  an array [id, name]
        project_id = [8, "Internal"];
        task_id = [86, "Meeting"];
        const unit_amount = this.state.grouped[groupKey][title] / 60; // seconds => minutes
        const name = title;

        return { project_id, task_id, unit_amount, name };
    }

    onClickLeftSide() {
        this.state.selected = null;
        this.state.selectedData = {};
    }

    onSelectSuggestion(groupKey, title) {
        const params = this.getSuggestionParams(groupKey, title);
        if (params === false) {
            return;
        }
        this.state.selected = { groupKey, title };
        this.state.selectedData = params;
    }

    async onTake(groupKey, title) {
        // duplicated in loadData
        const todayStart = new Date(new Date().setHours(0, 0, 0, 0)).toISOString();
        const date = todayStart.split("T")[0];
        const params = this.getSuggestionParams(groupKey, title);
        if (params === false) {
            return;
        }

        const vals = {
            date,
            user_id: session.user_id,
            ...params,
        };

        // to fix hardcoded
        vals.project_id = vals.project_id[0];
        vals.task_id = vals.task_id[0];
        await this.orm.call("account.analytic.line", "create", [vals]);
        this.notification.add("Timesheet entry created!", { type: "success" });
        this.onDelete(groupKey, title);
        this.state.selected = null;
        this.loadTimesheets(todayStart);
    }

    onDelete(groupKey, title) {
        delete this.state.grouped[groupKey][title];
        if (Object.keys(this.state.grouped[groupKey]).length === 0) {
            delete this.state.grouped[groupKey];
        }
    }

    onSaveTimesheetForm() {
        // Assume the timesheet has been saved
        if (this.state.selected) {
            this.onDelete(this.state.selected.groupKey, this.state.selected.title);
        }
        this.notification.add("Timesheet entry created!", { type: "success" });
    }
}

ActivityWatchTimesheet.template = "hr_timesheet.ActivityWatchTimesheet";

registry.category("actions").add("hr_timesheet_activitywatch_action", ActivityWatchTimesheet);
