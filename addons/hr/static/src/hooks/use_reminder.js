/**
 * Reminders use three LocalStorage keys per user to keep all the user's tabs in sync:
 * 1. "hr.reminder.{userId}" stores a string like "0.2026-06-04.1".
 *    Parts are the session key, today's date, and 1 if the reminder was shown, 0 otherwise.
 *    Whenever components get fresh data (like check IN/OUT or refresh)
 *    If the prefix changes, it resets the last digit to 0.
 * 2. "hr.reminder.{userId}.armedAt" stores the 10-min deadline.
 *    It starts ticking when the user first becomes active (presence).
 * 3. "hr.reminder.{userId}.workIntervals" caches today's work intervals so that
 *    the RPC runs at most once per day (memory -> storage -> RPC).
 * When the deadline passes, the reminder pops up (if the tab is visible) and sets "Done" to 1.
 */

import { useEffect, useListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useBus, useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export const REMINDER_DELAY = 10 * 60 * 1000;
export const REMINDER_FOCUS_DELAY = 5 * 1000;

export function reminderDoneKey(userId) {
    return `hr.reminder.${userId}`;
}

export function reminderArmedKey(userId) {
    return `hr.reminder.${userId}.armedAt`;
}

export function workIntervalsKey(userId) {
    return `hr.reminder.${userId}.workIntervals`;
}

const todayStr = () => luxon.DateTime.now().toISODate();

let orm;
let workIntervals;
let workIntervalsDate;

async function fetchTodayWorkIntervals(today) {
    const stored = JSON.parse(browser.localStorage.getItem(workIntervalsKey(user.userId)));
    if (stored?.date === today) {
        return stored.intervals;
    }
    const intervals = (await orm.call("hr.employee", "get_today_work_intervals")).map(([start, stop]) => [
        luxon.DateTime.fromISO(start).toMillis(),
        luxon.DateTime.fromISO(stop).toMillis(),
    ]);
    browser.localStorage.setItem(
        workIntervalsKey(user.userId),
        JSON.stringify({ date: today, intervals })
    );
    return intervals;
}

export async function isWorkingNow() {
    const today = todayStr();
    if (workIntervalsDate !== today) {
        workIntervalsDate = today;
        workIntervals = fetchTodayWorkIntervals(today);
    }
    const now = Date.now();
    return (await workIntervals).some(([start, stop]) => now >= start && now < stop);
}

export function clearWorkIntervalsCache() {
    workIntervalsDate = undefined;
    browser.localStorage.removeItem(workIntervalsKey(user.userId));
}

export function useReminder({
    isEligible,
    show,
    getPopover,
    getSessionKey,
}) {
    const presence = useService("presence");
    orm = useService("orm");
    let visibilityTimerId;
    const DONE_KEY = reminderDoneKey(user.userId);
    const ARMED_KEY = reminderArmedKey(user.userId);

    const isDoneToday = () =>
        browser.localStorage.getItem(DONE_KEY)?.endsWith(`${todayStr()}.1`);

    const setDone = () => {
        const sessionKey = browser.localStorage.getItem(DONE_KEY).split(".")[0];
        browser.localStorage.setItem(DONE_KEY, `${sessionKey}.${todayStr()}.1`);
        browser.localStorage.removeItem(ARMED_KEY);
    };

    // If prefix changed, reset done to 0 AND clear armedAt
    const syncStorage = () => {
        const raw = browser.localStorage.getItem(DONE_KEY);
        const prefix = `${getSessionKey()}.${todayStr()}`;
        if (raw) {
            const storedPrefix = raw.substring(0, raw.lastIndexOf("."));
            if (storedPrefix === prefix) {
                return;
            }
        }
        browser.localStorage.setItem(DONE_KEY, `${prefix}.0`);
        browser.localStorage.removeItem(ARMED_KEY);
        onPresence();
    };

    const cancelVisibilityTimer = () => {
        browser.clearTimeout(visibilityTimerId);
        visibilityTimerId = undefined;
    };

    const tryShowReminder = async () => {
        if (
            document.visibilityState !== "visible" ||
            isDoneToday() ||
            getPopover().isOpen ||
            !(await isEligible())
        ) {
            return;
        }
        await show();
        setDone();
    };

    const scheduleVisibilityShow = () => {
        if (visibilityTimerId) {
            return;
        }
        visibilityTimerId = browser.setTimeout(() => {
            visibilityTimerId = undefined;
            tryShowReminder();
        }, REMINDER_FOCUS_DELAY);
    };

    const onPresence = async () => {
        if (isDoneToday() || !(await isEligible())) {
            return;
        }
        const armedAt = browser.localStorage.getItem(ARMED_KEY);
        const now = Date.now();
        if (!armedAt || armedAt < new Date().setHours(0, 0, 0, 0)) {
            browser.localStorage.setItem(ARMED_KEY, now + REMINDER_DELAY);
            return;
        }
        if (now < armedAt) {
            return;
        }
        scheduleVisibilityShow();
    };

    const onVisibilityChange = () => {
        if (document.visibilityState !== "visible") {
            cancelVisibilityTimer();
        }
    };

    // Cross-tab : onPresence handle state management
    const onStorage = (e) => {
        if (e.key === DONE_KEY) {
            onPresence();
        }
    };

    const syncIfEligible = async () => {
        if (await isEligible()) {
            syncStorage();
        } else if (getPopover().isOpen) {
            getPopover().close();
        }
    };

    useBus(presence.bus, "presence", onPresence);
    useListener(document, "visibilitychange", onVisibilityChange);
    useListener(window, "storage", onStorage);

    // Resync Reminder when Eligible
    useEffect(() => {
        syncIfEligible();
    });
}
