// @ts-check
/** @odoo-module native */
/* eslint-disable no-console -- dedicated debug logging utility; console is its output */

/**
 * Debug logger for the quality campaign: four channels (logic, perf, pipeline,
 * lifecycle), one namespace per subsystem, off by default and free when off.
 *
 *     const log = makeLogger("web.action");
 *     log.logic("doAction", { type: action.type });
 *     const end = log.perf("loadAction");  ...  end({ views: 3 });
 *
 * Enable from the console: `odooLog.enable("mail.*:perf,web.action")`, or with
 * `localStorage["odoo.log"]`, `?log=<spec>` in the URL, or `debug=log`.
 * `odooLog.help()` prints the spec grammar; `odooLog.table()` the perf stats.
 */

/** @typedef {"logic" | "perf" | "pipeline" | "lifecycle"} LogKind */

/**
 * @typedef {{
 * ns: string;
 * kind: LogKind;
 * label: string;
 * count: number;
 * totalMs: number;
 * maxMs: number;
 * }} PerfStat
 */

/**
 * @typedef {{
 * ns: string;
 * kind: LogKind;
 * label: string;
 * count: number;
 * totalMs: number;
 * avgMs: number;
 * maxMs: number;
 * }} StatRow
 */

/** @typedef {(extra?: unknown) => number} PerfEnd */

/** @typedef {{ pattern: RegExp; kinds: number; negate: boolean }} Rule */

const KIND_BIT = Object.freeze({ logic: 1, perf: 2, pipeline: 4, lifecycle: 8 });
const ALL_KINDS = 15;
const KIND_NAMES = /** @type {LogKind[]} */ (Object.keys(KIND_BIT));

const KIND_STYLE = Object.freeze({
    logic: "color:#1e88e5",
    perf: "color:#ef6c00",
    pipeline: "color:#00897b",
    lifecycle: "color:#43a047",
});
const NS_STYLE = "color:#7c4dff;font-weight:bold";
const RESET_STYLE = "color:inherit;font-weight:normal";

const STORAGE_KEY = "odoo.log";
const URL_PARAM = "log";
const DEBUG_TOKEN = "log";

const HELP = `odooLog spec: comma-separated "<namespace>[:<kinds>]" tokens.
  namespace   dotted, "*" matches anything ("mail.*", "web.model.record", "*")
  kinds       "+"-joined subset of logic, perf, pipeline, lifecycle (default: all)
  -token      negates: "*,-mail.*:lifecycle" logs everything but mail lifecycle
odooLog.enable(spec, { persist = true })   odooLog.disable()
odooLog.silent = true      count perf spans without printing anything
odooLog.status()           odooLog.table()      odooLog.reset()      odooLog.loggers()`;

const _globals = /** @type {Record<string, any>} */ (globalThis);

const STATE_KEY = "__odooLogState";
const isFirstCopy = !_globals[STATE_KEY];
/**
 * @type {{
 * version: number;
 * spec: string;
 * rules: Rule[];
 * silent: boolean;
 * stats: Map<string, PerfStat>;
 * loggers: Map<string, DebugLogger>;
 * }}
 */
const state = (_globals[STATE_KEY] ||= {
    version: 0,
    spec: "",
    rules: [],
    silent: false,
    stats: new Map(),
    loggers: new Map(),
});

/** @type {PerfEnd} */
const NOOP_END = () => 0;

/**
 * @param {string} glob
 * @returns {RegExp}
 */
function _globToRegExp(glob) {
    const escaped = glob.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*");
    return new RegExp(`^${escaped}$`);
}

/**
 * @param {string} raw
 * @returns {number}
 */
function _parseKinds(raw) {
    let kinds = 0;
    for (const part of raw.split(/[+/ ]/)) {
        const name = part.trim();
        if (name in KIND_BIT) {
            kinds |= KIND_BIT[/** @type {LogKind} */ (name)];
        }
    }
    return kinds || ALL_KINDS;
}

/**
 * @param {string} spec
 * @returns {Rule[]}
 */
export function parseSpec(spec) {
    /** @type {Rule[]} */
    const rules = [];
    for (const part of spec.split(/[,;\n]/)) {
        let token = part.trim();
        if (!token) {
            continue;
        }
        const negate = token.startsWith("-");
        if (negate) {
            token = token.slice(1);
        }
        const colon = token.indexOf(":");
        const ns = colon === -1 ? token : token.slice(0, colon);
        const kinds = colon === -1 ? ALL_KINDS : _parseKinds(token.slice(colon + 1));
        rules.push({ pattern: _globToRegExp(ns.trim() || "*"), kinds, negate });
    }
    return rules;
}

/**
 * @param {string} ns
 * @param {Rule[]} rules
 * @returns {number}
 */
export function resolveKinds(ns, rules) {
    let kinds = 0;
    for (const rule of rules) {
        if (!rule.pattern.test(ns)) {
            continue;
        }
        kinds = rule.negate ? kinds & ~rule.kinds : kinds | rule.kinds;
    }
    return kinds;
}

/** @returns {string} */
function _specFromStorage() {
    try {
        return _globals.localStorage?.getItem?.(STORAGE_KEY) || "";
    } catch {
        return "";
    }
}

/** @returns {string} */
function _specFromUrl() {
    try {
        const search = _globals.location?.search;
        if (!search) {
            return "";
        }
        return new URLSearchParams(search).get(URL_PARAM) || "";
    } catch {
        return "";
    }
}

/** @returns {string} */
function _specFromDebugMode() {
    const debug = _globals.odoo?.debug;
    if (typeof debug !== "string") {
        return "";
    }
    return debug.split(",").some((token) => token.trim() === DEBUG_TOKEN) ? "*" : "";
}

/** @returns {string} */
function _initialSpec() {
    return _specFromUrl() || _specFromStorage() || _specFromDebugMode();
}

/** @param {string} spec */
function _applySpec(spec) {
    state.spec = spec;
    state.rules = parseSpec(spec);
    state.version++;
}

/** @param {string} spec */
function _persist(spec) {
    try {
        if (spec) {
            _globals.localStorage?.setItem?.(STORAGE_KEY, spec);
        } else {
            _globals.localStorage?.removeItem?.(STORAGE_KEY);
        }
    } catch {}
}

/**
 * @param {string} spec
 * @param {{ persist?: boolean }} [options]
 */
export function enableLogging(spec, { persist = true } = {}) {
    _applySpec(spec || "*");
    if (persist) {
        _persist(state.spec);
    }
}

/** @param {{ persist?: boolean }} [options] */
export function disableLogging({ persist = true } = {}) {
    _applySpec("");
    if (persist) {
        _persist("");
    }
}

/** @returns {number} */
function _now() {
    return _globals.performance?.now?.() ?? Date.now();
}

/**
 * @param {string} ns
 * @param {LogKind} kind
 * @param {string} label
 * @param {number} ms
 */
function _recordStat(ns, kind, label, ms) {
    const key = `${ns}|${kind}|${label}`;
    let stat = state.stats.get(key);
    if (!stat) {
        stat = { ns, kind, label, count: 0, totalMs: 0, maxMs: 0 };
        state.stats.set(key, stat);
    }
    stat.count++;
    stat.totalMs += ms;
    if (ms > stat.maxMs) {
        stat.maxMs = ms;
    }
}

/**
 * @param {unknown[]} data
 * @returns {unknown[]}
 */
function _resolveLazy(data) {
    return data.map((item) => (typeof item === "function" ? item() : item));
}

/**
 * @param {string} ns
 * @param {LogKind} kind
 * @param {string} label
 * @param {unknown[]} data
 */
function _emit(ns, kind, label, data) {
    if (state.silent) {
        return;
    }
    console.debug(
        `%c[${ns}]%c ${kind}%c ${label}`,
        NS_STYLE,
        KIND_STYLE[kind],
        RESET_STYLE,
        ..._resolveLazy(data),
    );
}

/**
 * @param {string} ns
 * @param {string} label
 * @param {number} startedAt
 * @param {number} endedAt
 */
function _measure(ns, label, startedAt, endedAt) {
    try {
        _globals.performance?.measure?.(`odoo:${ns}:${label}`, {
            start: startedAt,
            end: endedAt,
        });
    } catch {}
}

export class DebugLogger {
    /** @param {string} ns */
    constructor(ns) {
        this.ns = ns;
        this._version = -1;
        this._kinds = 0;
    }

    /** @returns {number} */
    get kinds() {
        if (this._version !== state.version) {
            this._kinds = resolveKinds(this.ns, state.rules);
            this._version = state.version;
        }
        return this._kinds;
    }

    /** @returns {boolean} */
    get enabled() {
        return this.kinds !== 0;
    }

    /**
     * @param {LogKind} kind
     * @returns {boolean}
     */
    isEnabled(kind) {
        return (this.kinds & KIND_BIT[kind]) !== 0;
    }

    /**
     * @param {string} suffix
     * @returns {DebugLogger}
     */
    child(suffix) {
        return makeLogger(`${this.ns}.${suffix}`);
    }

    /**
     * @param {string} label
     * @param {...unknown} data
     */
    logic(label, ...data) {
        if (this.isEnabled("logic")) {
            _emit(this.ns, "logic", label, data);
        }
    }

    /**
     * @param {string} label
     * @param {...unknown} data
     */
    pipeline(label, ...data) {
        if (this.isEnabled("pipeline")) {
            _emit(this.ns, "pipeline", label, data);
        }
    }

    /**
     * @param {string} label
     * @param {...unknown} data
     */
    lifecycle(label, ...data) {
        if (this.isEnabled("lifecycle")) {
            _emit(this.ns, "lifecycle", label, data);
        }
    }

    /**
     * @param {string} label
     * @param {...unknown} data
     * @returns {PerfEnd}
     */
    perf(label, ...data) {
        if (!this.isEnabled("perf")) {
            return NOOP_END;
        }
        const startedAt = _now();
        return (extra) => {
            const endedAt = _now();
            const ms = endedAt - startedAt;
            _recordStat(this.ns, "perf", label, ms);
            _measure(this.ns, label, startedAt, endedAt);
            const parts = extra === undefined ? data : [...data, extra];
            _emit(this.ns, "perf", `${label} ${ms.toFixed(2)}ms`, parts);
            return ms;
        };
    }

    /**
     * @template T
     * @param {string} label
     * @param {() => T} fn
     * @returns {T}
     */
    measure(label, fn) {
        if (!this.isEnabled("perf")) {
            return fn();
        }
        const end = this.perf(label);
        /** @type {any} */
        let result;
        try {
            result = fn();
        } catch (error) {
            end({ threw: true });
            throw error;
        }
        if (result && typeof result.then === "function") {
            return result.then(
                (/** @type {unknown} */ value) => {
                    end();
                    return value;
                },
                (/** @type {unknown} */ error) => {
                    end({ rejected: true });
                    throw error;
                },
            );
        }
        end();
        return result;
    }
}

/**
 * @param {string} ns
 * @returns {DebugLogger}
 */
export function makeLogger(ns) {
    let logger = state.loggers.get(ns);
    if (!logger) {
        logger = new DebugLogger(ns);
        state.loggers.set(ns, logger);
    }
    return logger;
}

/** @returns {StatRow[]} */
export function getStats() {
    /** @type {StatRow[]} */
    const rows = [];
    for (const stat of state.stats.values()) {
        rows.push({
            ns: stat.ns,
            kind: stat.kind,
            label: stat.label,
            count: stat.count,
            totalMs: Number(stat.totalMs.toFixed(2)),
            avgMs: Number((stat.totalMs / stat.count).toFixed(2)),
            maxMs: Number(stat.maxMs.toFixed(2)),
        });
    }
    return rows.sort((a, b) => b.totalMs - a.totalMs);
}

export function resetStats() {
    state.stats.clear();
}

/** @returns {{ spec: string; silent: boolean; kinds: LogKind[]; active: string[] }} */
export function getStatus() {
    /** @type {string[]} */
    const active = [];
    for (const logger of state.loggers.values()) {
        if (logger.enabled) {
            const kinds = KIND_NAMES.filter((kind) => logger.isEnabled(kind));
            active.push(`${logger.ns}:${kinds.join("+")}`);
        }
    }
    return {
        spec: state.spec,
        silent: state.silent,
        kinds: KIND_NAMES,
        active: active.sort(),
    };
}

function _installGlobalApi() {
    if (_globals.odooLog) {
        return;
    }
    _globals.odooLog = {
        enable: enableLogging,
        disable: disableLogging,
        status: () => {
            const status = getStatus();
            console.info(`odooLog spec="${status.spec}" silent=${status.silent}`);
            console.info(status.active.join("\n") || "(no active logger)");
            return status;
        },
        stats: getStats,
        table: () => console.table(getStats()),
        reset: resetStats,
        loggers: () => [...state.loggers.keys()].sort(),
        help: () => console.info(HELP),
        get silent() {
            return state.silent;
        },
        set silent(value) {
            state.silent = Boolean(value);
        },
    };
}

if (isFirstCopy) {
    _applySpec(_initialSpec());
}
_installGlobalApi();
