import { registry } from "@web/core/registry";

const { DateTime } = luxon;

function randomDuration(min = 600, max = 1800) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomChoice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

const gdocTitles = [
    "Roadmap Q1",
    "Tech Debt Cleanup",
    "Meeting Notes",
    "Incident Postmortem",
    "Design Spec Draft",
    "Architecture Proposal",
    "Release Plan",
    "User Feedback Summary",
    "Sprint Retrospective",
];

const discordContacts = [
    "Marc Demo",
    "Joel Willis",
    "Julian Pine",
    "Clara Larkspur",
    "Ethan Brightwood",
    "Fiona Vale",
    "Marcus Goldwyn",
    "Lydia Quill",
    "Sebastian Brook",
    "Cecilia Dawn",
];

export class AwFakeEventsService {
    constructor(env, services) {
        this.env = env;
        this.services = services;
        this.cache = {};
        this.odooUrl = window.location.origin;
    }

    async start() {
        return this;
    }

    async _loadProjectsAndTasks() {
        const orm = this.services.orm;
        const projects = await orm.searchRead("project.project", [], ["id"]);
        const tasks = await orm.searchRead("project.task", [], ["project_id"]);

        const tasksByProject = {};
        tasks.forEach((t) => {
            const pid = t.project_id[0];
            if (!tasksByProject[pid]) {
                tasksByProject[pid] = [];
            }
            tasksByProject[pid].push(t.id);
        });

        return { projects, tasksByProject };
    }

    async _generateEventsForDay(day) {
        const { projects, tasksByProject } = await this._loadProjectsAndTasks();

        const start = new Date(`${day}T09:00:00`).getTime();
        const end = new Date(`${day}T17:00:00`).getTime();
        let cursor = start;

        const awWindow = [];
        const awBrowser = [];

        const browserPatterns = [
            () => ({
                title: `Lorem Ipsum · Pull Request #${Math.floor(Math.random() * 500)} · cool-repo`,
                url: `https://github.com/company/cool-repo/pull/${Math.floor(Math.random() * 500)}`,
            }),
            () => ({
                title: "Inbox | https://mail.google.com",
                url: "https://mail.google.com/mail/u/0/#inbox",
            }),
            () => ({
                title: `${randomChoice(gdocTitles)} - Google Docs`,
                url: `https://docs.google.com/document/d/${Math.random().toString(36).slice(2)}`,
            }),
        ];

        const windowApps = [
            { app: "Discord", title: `@${randomChoice(discordContacts)} - Discord` },
            { app: "Terminal", title: "Terminal" },
        ];

        while (cursor < end) {
            const duration = randomDuration();
            const stop = Math.min(cursor + duration * 1000, end);
            const r = Math.random();

            const eventData = (title, url = null, app = "Chrome") => {
                const ev = {
                    timestamp: new Date(cursor).toISOString(),
                    duration: Math.floor((stop - cursor) / 1000),
                    start: DateTime.fromMillis(cursor),
                    stop: DateTime.fromMillis(stop),
                    data: { app, title },
                };
                if (url) {
                    ev.data.url = url;
                }
                return ev;
            };

            if (r < 0.1) {
                const proj = randomChoice(projects);
                const pid = proj.id;
                const tlist = tasksByProject[pid];
                const tid = tlist?.length ? randomChoice(tlist) : null;

                const url = tid
                    ? `${this.odooUrl}/odoo/project/${pid}/tasks/${tid}`
                    : `${this.odooUrl}/odoo/project/${pid}`;

                const title = tid ? `Project ${pid} - Task ${tid}` : `Project ${pid}`;

                awBrowser.push(eventData(title, url, "Chrome"));
            } else if (r < 0.65) {
                const gen = randomChoice(browserPatterns)();
                awBrowser.push(eventData(gen.title, gen.url, "Chrome"));
            } else {
                const app = randomChoice(windowApps);
                awWindow.push(eventData(app.title, null, app.app));
            }

            cursor = stop;
        }

        return {
            "aw-watcher-window": awWindow,
            "aw-client-web": awBrowser,
        };
    }

    async generate(day) {
        const data = await this._generateEventsForDay(day);
        this.cache[day] = data;
        return data;
    }

    get(day) {
        return this.cache[day] || [];
    }

    clear(day) {
        delete this.cache[day];
    }
}

export const awFakeEventsService = {
    dependencies: ["orm"],
    async start(env, services) {
        return new AwFakeEventsService(env, services);
    },
};

registry.category("services").add("aw_fake_events_service", awFakeEventsService);
