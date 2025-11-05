/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { TimesheetTimer } from "@timesheet_grid/components/static_timesheet_form/static_timesheet_timer";
import { user } from "@web/core/user";

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
            project_by_id: {},
            task_by_id: {},
        });

        onWillStart(async () => {
            await this.loadData();
            this.state.loading = false;
        });
    }

    extractBrowserWatcherActivityName(event) {
        const url = event.data.url;
        const odooUrl = RegExp.escape(window.location.origin);

        // in the config, we should have a sequence field, because order is important
        // like the example of overlap in calendar and planning apps
        // project and task in odoo url
        let match = url.match(
            new RegExp(`^${odooUrl}(?:/[^?#]*)*/(?:tasks|project\\.task)/(\\d+)$`)
        );
        if (match) {
            event.name = "Working on project"; // should come from config
            event.task_id = Number(match[1]);
            return true;
        }

        // only project in odoo url
        match = url.match(
            new RegExp(`^${odooUrl}(?:/[^?#]*)*/(?:project|project\\.project)/(\\d+)$`)
        );
        if (match) {
            event.project_id = Number(match[1]);
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

        // only for test, this should be a config, and the user can adapt it to his need
        if (/^https?:\/\/localhost/.test(url)) {
            event.name = "Programming (testing on browser)";
            return true;
        } else if (/^https:\/\/github\.com/.test(url)) {
            event.name = "Programming (reading code on github)";
            return true;
        } else if (/^https:\/\/app\.excalidraw\.com/.test(url)) {
            event.name = "Reading spec (Excalidraw)";
            return true;
        } else if (/chatgpt/i.test(url)) {
            event.name = "Discussing with ChatGPT";
            return true;
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

        const ranges = await this.orm.call("account.analytic.line", "get_events", [[]]);
        for (const range of ranges) {
            range["start"] = deserializeDateTime(range["start"]);
            range["stop"] = deserializeDateTime(range["stop"]);
        }

        this.merge(ranges, events["aw-watcher-vscode"]);
        this.merge(ranges, events["aw-client-web"]);

        let prevProjectId = false;
        let prevTaskId = false;
        const tasksIds = new Set();
        const projectsIds = new Set();

        ranges.forEach((range) => {
            if (range.project_id != null) {
                projectsIds.add(range.project_id);
            }
            if (range.task_id != null) {
                tasksIds.add(range.task_id);
            }
        });

        // get projects and tasks names
        // loading this data in can be in // ( to fix later )
        // we need to verify that the module is installed
        const projects = await this.orm.searchRead(
            "project.project",
            [["id", "in", Array.from(projectsIds)]],
            ["id", "name"]
        );
        const tasks = await this.orm.searchRead(
            "project.task",
            [["id", "in", Array.from(tasksIds)]],
            ["id", "name", "project_id"]
        );

        // Add missing project ids
        const taskToProject = Object.fromEntries(
            tasks
                .filter((task) => task.project_id && task.project_id[0] != null)
                .map((task) => [task.id, task.project_id[0]])
        );
        ranges.forEach((range) => (range.project_id ??= taskToProject[range.task_id]));

        this.state.project_by_id = Object.fromEntries([
            ...projects.map(({ id, name }) => [id, name]),
            ...tasks.filter((task) => task.project_id).map((task) => task.project_id),
        ]);
        this.state.task_by_id = Object.fromEntries(tasks.map(({ id, name }) => [id, name]));

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
        // so_line, project_id, task_id should be added only if the right modules are installed
        const fields = ["id", "name", "date", "project_id", "task_id", "unit_amount", "so_line"];
        const domain = [
            ["date", "=", todayStart.split("T")[0]],
            ["user_id", "=", user.userId],
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
        if (!intervalsToInclude || intervalsToInclude.length === 0) {
            return;
        }
        if (ranges.length === 0) {
            ranges.push(...intervalsToInclude);
            return;
        }

        let j = 0;
        for (let i = 0; i <= ranges.length; i++) {
            const gapStart = i === 0 ? -Infinity : ranges[i - 1].stop;
            const gapEnd = i === ranges.length ? Infinity : ranges[i].start;
            while (j < intervalsToInclude.length && intervalsToInclude[j].stop <= gapStart) {
                j++;
            }
            while (j < intervalsToInclude.length && intervalsToInclude[j].start < gapEnd) {
                const interval = { ...intervalsToInclude[j] };
                interval.start = Math.max(gapStart, interval.start);
                interval.stop = Math.min(gapEnd, interval.stop);
                ranges.splice(i, 0, interval);
                i++;
                j++;
            }
        }
    }

    parseId(id) {
        const res = Number.parseInt(id);
        return isNaN(res) ? null : res;
    }

    isSuggestionClicked(groupKey, title) {
        return this.state.selected?.groupKey === groupKey && this.state.selected?.title === title;
    }

    projectName(id) {
        return this.state.project_by_id[id] || "unmatched"; // manage if the project is wrong (not a valid key)
    }

    taskName(id) {
        return this.state.task_by_id[id] || "unmatched"; // same
    }

    getSuggestionParams(groupKey, title) {
        if (this.state.grouped[groupKey]?.[title] == null) {
            return false;
        }
        const ids = groupKey.split("_");
        const project_id = this.parseId(ids[0]);
        const task_id = this.parseId(ids[1]);
        const project_name = this.projectName(project_id);
        const task_name = this.taskName[project_id];

        const project = [project_id, project_name];
        const task = [task_id, task_name];
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
            user_id: user.userId,
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
