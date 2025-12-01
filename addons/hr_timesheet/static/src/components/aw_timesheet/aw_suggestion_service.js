import { registry } from "@web/core/registry";

const STORAGE_KEY = "aw_event_data";

// Parameters to fine-tune

const HISTORY_LIMIT = 10;
// If no candidate is above this threshold, no suggestion will be returned.
// Highly dependent on the values of the other parameters.
const SCORE_THRESHOLD = 1.5;
// If the last n choices are identical, suggest that no matter the history
const RECENT_OVERRIDE_COUNT = 3;
// The number of days it takes to divide the score of an entry by half due to time decay
const TIME_DECAY_HALF_LIFE = 30;
// The minimum factor applied to the score due to time decay
const MIN_TIME_DECAY = 0.25;
// Recency decay factor. The nth entry is worth 1 / n ^ α, so 0 means no decay and 1 means f(n) = 1 / n
const RECENCY_ALPHA = 0.25;

export class AwSuggestionService {
    constructor(env, services) {
        this.env = env;
        this.services = services;
    }

    async start() {
        return this;
    }

    _loadData() {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    }

    _saveData(data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }

    _getHistory(key) {
        const db = this._loadData();
        return db[key]?.history || [];
    }

    _pushHistory(key, projectId, taskId) {
        const db = this._loadData();
        const entry = db[key] || { history: [] };
        entry.history = [{ projectId, taskId, ts: Date.now() }, ...entry.history].slice(
            0,
            HISTORY_LIMIT
        );
        db[key] = entry;
        this._saveData(db);
    }

    _timeWeight(ts) {
        const age = (Date.now() - ts) / (1000 * 60 * 60 * 24);
        return Math.max(MIN_TIME_DECAY, Math.pow(0.5, age / TIME_DECAY_HALF_LIFE));
    }

    _recencyWeight(index) {
        return 1 / Math.pow(index + 1, RECENCY_ALPHA);
    }

    _computeScores(history) {
        if (!history.length) {
            return { projectScores: {}, taskScores: {} };
        }

        const lastN = history.slice(0, RECENT_OVERRIDE_COUNT);
        const allSameTask = lastN.every(
            (e) => e.projectId === lastN[0].projectId && e.taskId === lastN[0].taskId
        );
        if (allSameTask) {
            const key = `${lastN[0].projectId}-${lastN[0].taskId || ""}`;
            return {
                projectScores: { [lastN[0].projectId]: 1 },
                taskScores: { [key]: 10 },
            };
        }

        const projectScores = {};
        const taskScores = {};

        history.forEach((entry, index) => {
            const timeWeight = this._timeWeight(entry.ts);
            const recencyWeight = this._recencyWeight(index);
            const score = timeWeight * recencyWeight;

            projectScores[entry.projectId] = (projectScores[entry.projectId] || 0) + score;
            if (entry.taskId != null) {
                const taskKey = `${entry.projectId}-${entry.taskId}`;
                taskScores[taskKey] = (taskScores[taskKey] || 0) + score;
            }
        });

        return { projectScores, taskScores };
    }

    _getTopCandidate(history) {
        const { projectScores, taskScores } = this._computeScores(history);

        const sortedTasks = Object.entries(taskScores).sort((a, b) => b[1] - a[1]);
        if (sortedTasks.length) {
            const [key, score] = sortedTasks[0];
            if (score >= SCORE_THRESHOLD) {
                const [projectId, taskId] = key.split("-").map((v) => Number(v));
                return { projectId, taskId };
            }
        }

        const sortedProjects = Object.entries(projectScores).sort((a, b) => b[1] - a[1]);
        if (sortedProjects.length) {
            const [projectId, score] = sortedProjects[0];
            if (score >= SCORE_THRESHOLD) {
                return { projectId, taskId: null };
            }
        }

        return null;
    }

    ////////////////
    // Public API //
    ////////////////

    recordSelection(key, projectId, taskId) {
        this._pushHistory(key, projectId, taskId);
    }

    getSuggestion(key) {
        const history = this._getHistory(key);
        return this._getTopCandidate(history);
    }

    clear(key) {
        const db = this._loadData();
        delete db[key];
        this._saveData(db);
    }
}

export const awSuggestionService = {
    dependencies: [],
    async start(env, services) {
        const service = new AwSuggestionService(env, services);
        await service.start();
        return service;
    },
};

registry.category("services").add("aw_suggestion_service", awSuggestionService);
