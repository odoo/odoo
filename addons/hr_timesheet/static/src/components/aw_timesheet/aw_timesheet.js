/** @odoo-module **/

import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";
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
            ...this.defaultStateValues,
            groupBy: 'project',
            currentDate: DateTime.now().startOf('day'),
        });
        this.localKey = "aw_taken_deleted_events";
        this.consumedEvents = JSON.parse(localStorage.getItem(this.localKey) || "{}");

        onWillStart(async () => {
            await this.loadData();
        });

        this._onMouseUp = this.onMouseUp.bind(this);
        this._onClickOutsideBound = this.onClickOutside.bind(this);
        onMounted(() => {
            window.addEventListener("mouseup", this._onMouseUp)
            // document.addEventListener("click", this._onClickOutsideBound);
            // the problem with this that when we click on the form
        });
        onWillUnmount(() => {
            window.removeEventListener("mouseup", this._onMouseUp);
            // document.removeEventListener("click", this._onClickOutsideBound);
        });
    }

    get defaultStateValues() {
        return {
            records: [],
            grouped: {},
            billableTimesheets: [],
            nonBillableTimesheets: [],
            totalTime: 0,
            billableTime: 0,
            nonBillableTime: 0,
            billablePercentage: 0,
            nonBillablePercentage: 0,
            projectById: {},
            taskById: {},
            selectedRows: new Set(),
            isSelecting: false,
        };
    };

    onClickOutside(ev) {
        const cards = document.querySelector(".o_suggestion");
        if (cards && !cards.contains(ev.target)) {
            this.initSelectedRows();
        }
    }

    onDateChange(ev) {
        this.state.currentDate = DateTime.fromISO(ev.target.value);
        this.loadData();
    }

    navigateToDay(diff) {
        this.state.currentDate = this.state.currentDate.plus({ days: diff });
        this.loadData();
    }

    keyFor(groupKey, title) {
        return JSON.stringify({
            groupKey,
            title,
        });
    }

    projectTaskKey(project_id, task_id) {
        return JSON.stringify({
            project_id,
            task_id,
        });
    }

    keyForWithDay(groupKey, title) {
        return JSON.stringify({
            groupKey,
            title,
            day: this.state.currentDate.toISO().split("T")[0],
        });
    }

    get unmatchedProjectTaskKey() {
        return this.projectTaskKey(false, false);
    }

    disableTextSelection() {
        document.body.style.userSelect = "none";
    }

    enableTextSelection() {
        document.body.style.userSelect = "";
    }

    isSelected(groupKey, title) {
        return this.state.selectedRows.has(this.keyFor(groupKey, title));
    }

    onMouseDown(groupKey, title, ev) {
        if (ev.button !== 0) {
            return;
        }

        if (ev.target.closest('.btn')) {
            return; // click on Take/Delete btns
        }

        this.disableTextSelection();
        this.state.isSelecting = true;
        this.toggleSelect(groupKey, title);
    }

    onMouseEnter(groupKey, title) {
        if (!this.state.isSelecting) {
            return;
        }
        const key = this.keyFor(groupKey, title);
        if (!this.state.selectedRows.has(key)) {
            this.state.selectedRows.add(key);
        }
    }

    onMouseUp() {
        this.state.isSelecting = false;
        this.enableTextSelection();
    }

    toggleSelect(groupKey, title) {
        const key = this.keyFor(groupKey, title);
        if (this.state.selectedRows.has(key)) {
            this.state.selectedRows.delete(key);
        } else {
            this.state.selectedRows.add(key);
        }
    }

    extractWatcherActivity(event) {
        let data = event.data.title;
        if (event.data.url) {
            data += " " + event.data.url;
        }

        for (const rule of this.awRules) {
            const regex = new RegExp(rule.regex);
            const match = data.match(regex);
            if (match) {
                if (rule.project_id != null) {
                    event.project_id = rule.project_id[0];
                }

                if (rule.task_id != null) {
                    event.task_id = rule.task_id[0];
                }

                if (rule.template != null) {
                    let name = rule.template;
                    for (let i = 1; i < match.length; i++) {
                        name = name.replace(`$${i}`, match[i]);
                    }
                    event.name = name;
                } else {
                    event.name = rule.type;
                }
                event.always_active = rule.always_active;
                event.primary = rule.primary;
                event.type = rule.type;
                event.keyEvent = true;
                return;
            }
        }

        if (!event.data.url) {
            return;
        }

        // in the config, we should have a sequence field, because order is important
        // like the example of overlap in calendar and planning apps
        // project and task in odoo url
        const url = event.data.url;
        const odooUrl = RegExp.escape(window.location.origin); // should be moved outside (this function is called many times)
        let match = url.match(
            new RegExp(`^${odooUrl}(?:/[^?#]*)*/(?:tasks|project\\.task)/(\\d+)(?:\\?|$)`)
        );
        if (match) {
            event.name = _t("Odoo Project App");
            event.task_id = Number(match[1]);
            event.type = "project_task";
            event.keyEvent = true;
            return;
        }

        // only project in odoo url
        match = url.match(
            new RegExp(`^${odooUrl}(?:/[^?#]*)*/(?:project|project\\.project)/(\\d+)(?:\\?|$)`)
        );
        if (match) {
            event.project_id = Number(match[1]);
            event.type = "project_project";
            event.keyEvent = true;
            return;
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
                [
                    "aw-watcher-vscode",
                    "aw-watcher-window",
                    "aw-client-web",
                    "aw-watcher-afk",
                ].includes(buckets[key].client)
            )
            .map((key) => buckets[key]);
    }

    async loadAwEvents(baseUrl, start, end) {
        try {
            const watchers = await this.getWatchers(baseUrl);
            const requests = [];
            for (const watcher of watchers) {
                requests.push(
                    fetch(
                        `${baseUrl}/api/0/buckets/${watcher["id"]}/events?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`
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
                    for (const event of events) {
                        let eventType = watchers[index].client;
                        if (watchers[index].client === "aw-watcher-vscode") {
                            event.name = _t("Programming In VS Code"); // should be done in config
                            event.keyEvent = true;
                            event.type = "vs_code";
                        } else if (
                            ["aw-watcher-window", "aw-client-web"].includes(watchers[index].client)
                        ) {
                            this.extractWatcherActivity(event);
                            if (event.always_active) {
                                eventType = "always_active";
                            }
                        } else if (watchers[index].client === "aw-watcher-afk") {
                            if (event?.data?.status === "not-afk") {
                                continue;
                            }
                        }
                        event.start = DateTime.fromISO(event.timestamp);
                        event.stop = event.start.plus(
                            Duration.fromObject({ seconds: event.duration })
                        );
                        // assuming you have one watcher per type, if you have 2 browsers (extension on each browser, we need to change it a bit)
                        if (!res[eventType]) {
                            res[eventType] = [];
                        }
                        res[eventType].push(event);
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
                        sticky: true,
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
                        sticky: true,
                    }
                );
            }
            return res;
        } catch {
            this.notification.add(
                _t(
                    "Something went wrong getting data from Activity Watch, make sure to start the server with the right cors origins E.G ./aw-server --cors-origins http://localhost:8069"
                ),
                {
                    type: "danger",
                    sticky: true,
                }
            );
            return {};
        }
    }

    resetState() {
        Object.assign(this.state, {
            ...this.defaultStateValues,
            groupBy: this.state.groupBy,
            currentDate: this.state.currentDate,
        });
    }



    async loadData() {
        this.resetState();
        this.awRules = await this.orm.call("aw.rule", "search_read", [
            [],
            [
                "regex",
                "type",
                "template",
                "project_id",
                "task_id",
                "always_active",
                "primary",
                "sequence",
            ],
        ]);
        // not for nesting, start => activitywatch/aw-server$ ./aw-server --cors-origins http://localhost:8069
        const baseUrl = "http://localhost:5700";
        const todayStart = this.state.currentDate.toISO();
        const todayEnd = this.state.currentDate.endOf('day').toISO();
        const events = await this.loadAwEvents(baseUrl, todayStart, todayEnd);

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

        const ranges = await this.orm.call("account.analytic.line", "get_events", [[], this.state.currentDate.toISO().split("T")[0]]);
        for (const range of ranges) {
            range["start"] = deserializeDateTime(range["start"]);
            range["stop"] = deserializeDateTime(range["stop"]);
            range["keyEvent"] = true;
        }

        // in a loop
        this.merge(ranges, events["always_active"]);
        this.merge(ranges, events["aw-watcher-vscode"]);
        this.merge(ranges, events["aw-watcher-afk"]); // will work in the inverse way later
        this.merge(ranges, events["aw-client-web"]); // assumin one browser => if 2 two, the 2 pointers algo will fail (no sorted non overlapping ranges)
        this.merge(ranges, events["aw-watcher-window"]);

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

        this.state.projectById = Object.fromEntries([
            ...projects.map(({ id, name }) => [id, name]),
            ...tasks.filter((task) => task.project_id).map((task) => task.project_id),
        ]);
        this.state.taskById = Object.fromEntries(tasks.map(({ id, name }) => [id, name]));

        let prevKeyyEvent = null;
        let isLastEventPrimary = false;
        let prevProjectId = false;
        let prevTaskId = false;
        for (const range of ranges) {
            if (range?.data?.status === "afk") {
                continue;
            }

            if (range.primary) {
                // when rule is primary => we change project and task (to dicuss if we should have one of them mandatory)
                // it doesn't make sens to set primary event without project and task
                prevKeyyEvent = range.name;
                isLastEventPrimary = true;
                prevProjectId = range.project_id || false;
                prevTaskId = range.task_id || false;
                // non primary key event can only overide a previous non primary key event, but not primary events
            } else if (range.keyEvent) {
                // no primary key events preceed this event
                if (!isLastEventPrimary) {
                    prevKeyyEvent = range.name;
                }
                if (
                    (!isLastEventPrimary || (!prevProjectId && !prevTaskId)) &&
                    (range.project_id || range.task_id)
                ) {
                    prevProjectId = range.project_id;
                    prevTaskId = range.task_id;
                    // no need to overide if both are null
                }
            }
            const duration = (range.stop - range.start) / 1000;
            const projectTask = this.projectTaskKey(prevProjectId, prevTaskId);
            if (!(projectTask in this.state.grouped)) {
                this.state.grouped[projectTask] = {};
            }

            let name = prevKeyyEvent;
            if (name == null) {
                name = "NO prev key event"; // to check later, if i start with a non key event, what to do, put in "Others" or skip it
            }

            if (!this.state.grouped[projectTask][name]) {
                this.state.grouped[projectTask][name] = {
                    duration: 0.0,
                    type: range.type,
                    start: range.start,
                };
            }
            this.state.grouped[projectTask][name].duration += duration;
        }

        for (const [groupKey, activities] of Object.entries(this.state.grouped)) {
            for (const [title, {duration, start}] of Object.entries(activities)) {
                const eventKey = this.keyForWithDay(groupKey, title);
                if (this.consumedEvents[eventKey]) { // can be done directly when adding
                    delete this.state.grouped[groupKey][title];
                } else {
                    const data = {
                        start,
                        duration,
                        title,
                        groupKey,
                    }
                    const { project_id, task_id } = JSON.parse(groupKey);

                    if (project_id) {
                        data.project = this.projectName(project_id);
                    }

                    if (task_id) {
                        data.task = this.taskName(task_id);
                    }

                    this.state.records.push(data);
                }
            }
        }

        this.state.records.sort((a, b) => a.start - b.start);
        await this.loadTimesheets();
    }

    async loadTimesheets() {
        const todayStart = this.state.currentDate.toISO();
        // get timesheets
        // so_line, project_id, task_id should be added only if the right modules are installed
        const fields = ["id", "name", "date", "project_id", "task_id", "unit_amount", "so_line"];
        const domain = [
            ["date", "=", todayStart.split("T")[0]],
            ["user_id", "=", user.userId],
        ];

        this.state.billableTimesheets = [];
        this.state.nonBillableTimesheets = [];
        this.state.totalTime = 0;
        this.state.billableTime = 0;
        this.state.nonBillableTime = 0;

        const timesheets = await this.orm.searchRead("account.analytic.line", domain, fields);
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

        this.state.billablePercentage = this.state.totalTime ?
            (this.state.billableTime * 100) / this.state.totalTime :
            0
        ;
        this.state.nonBillablePercentage = this.state.totalTime ?
            (this.state.nonBillableTime * 100) / this.state.totalTime :
            0
        ;
    }

    merge(ranges, intervalsToInclude) {
        if (!intervalsToInclude || intervalsToInclude.length === 0) {
            return;
        }
        intervalsToInclude.sort((a, b) => a.start - b.start);
        if (ranges.length === 0) {
            ranges.push(...intervalsToInclude);
            return;
        }

        let j = 0;
        const res = [];
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
                res.push(interval);
                j++;
            }
        }
        ranges.push(...res);
        ranges.sort((a, b) => a.start - b.start);
    }

    parseId(id) {
        const res = Number.parseInt(id);
        return isNaN(res) ? null : res;
    }

    projectName(id) {
        return this.state.projectById[id] || "unmatched"; // manage if the project is wrong (not a valid key)
    }

    taskName(id) {
        return this.state.taskById[id] || "unmatched"; // same
    }

    getSuggestionParams(groupKey, title) {
        if (this.state.grouped[groupKey]?.[title] == null) {
            return false;
        }
        const { project_id, task_id } = JSON.parse(groupKey);
        const res = {
            name: title,
            unit_amount: this.state.grouped[groupKey][title].duration / 60,
        };
        if (project_id != null) {
            res["project_id"] = project_id;
        }
        if (task_id != null) {
            res["task_id"] = task_id;
        }

        return res;
    }

    initSelectedRows() {
        this.state.selectedRows = new Set();
    }

    async onTake(groupKey, title) {
        // duplicated in loadData
        const todayStart = this.currentDate.toISO();
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

        await this.orm.call("account.analytic.line", "create", [vals]);
        this.notification.add("Timesheet entry created!", { type: "success" });
        this.onDelete(groupKey, title);
        this.loadTimesheets();
    }

    onDelete(groupKey, title) {
        this.consumedEvents[this.keyForWithDay(groupKey, title)] = true;
        localStorage.setItem(this.localKey, JSON.stringify(this.consumedEvents));

        delete this.state.grouped[groupKey][title];
    }

    get selectedData() {
        let project_id = null;
        let task_id = null;
        let name = "";
        let total_amount = 0.0;

        for (const row of this.state.selectedRows) {
            const { groupKey, title } = JSON.parse(row);
            const params = this.getSuggestionParams(groupKey, title);

            if (!project_id && params.project_id) {
                project_id = params.project_id;
                task_id = params.task_id;
            }

            name += params.name + ' ';
            total_amount += params.unit_amount;
        }

        return {
            project_id,
            task_id,
            name,
            unit_amount: total_amount,
            date: this.state.currentDate.toISO().split("T")[0],
            user_id: user.userId,
        }
    }

    onSaveTimesheetForm() {
        for (const row of this.state.selectedRows) {
            const { groupKey, title } = JSON.parse(row);
            this.onDelete(groupKey, title);
        }

        this.state.records = this.state.records.filter(record => {
            return !this.state.selectedRows.has(JSON.stringify({
                groupKey: record.groupKey,
                title: record.title
            }));
        });

        this.initSelectedRows();
        this.notification.add("Timesheet entry created!", { type: "success" });
        this.loadTimesheets();
    }
}

ActivityWatchTimesheet.template = "hr_timesheet.ActivityWatchTimesheet";

registry.category("actions").add("hr_timesheet_activitywatch_action", ActivityWatchTimesheet);
