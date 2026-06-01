/**
 * Reminders use two LocalStorage keys to keep all browser tabs in sync:
 * 1. "HrReminderDone" stores a string like "7.2026-06-04.0.1".
 *    The first parts are the user's ID, today's date, and session key. The last digit is 1 if the reminder was shown, 0 otherwise.
 *    Whenever components get fresh data (like checking in via RPC), they call `syncStorage()`. If the prefix changes, it resets the last digit to 0.
 * 2. "hr.reminder.{userId}.armedAt" stores the 15-min deadline.
 *    It starts ticking when the user first becomes active (presence).
 *
 * When the deadline passes, the reminder pops up (if the tab is visible) and sets "Done" to 1.
 */

import { useEffect, useListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useBus, useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export const REMINDER_DELAY = 15 * 1000;
export const REMINDER_FOCUS_DELAY = 5 * 1000;
export const REMINDER_LS_KEY = "HrReminderDone";

export function reminderArmedKey(userId) {
    return `hr.reminder.${userId}`;
}

export function useReminder({
    isEligible,
    show,
    getPopover,
    getSessionKey = () => 0,
}) {
    const presence = useService("presence");
    let visibilityTimerId = null;
    const ARMED_KEY = reminderArmedKey(user.userId);

    const buildPrefix = () => {
        const date = luxon.DateTime.now().toFormat("yyyy-MM-dd");
        return `${user.userId}.${date}.${getSessionKey()}`;
    };

    const isDone = () => browser.localStorage.getItem(REMINDER_LS_KEY)?.at(-1) === "1";

    const setDone = () => {
        browser.localStorage.setItem(REMINDER_LS_KEY, `${buildPrefix()}.1`);
        browser.localStorage.removeItem(ARMED_KEY);
    };

    // If prefix changed, reset done to 0 AND clear armedAt
    const syncStorage = () => {
        const raw = browser.localStorage.getItem(REMINDER_LS_KEY);
        const prefix = buildPrefix();
        if (raw) {
            const storedPrefix = raw.substring(0, raw.lastIndexOf("."));
            if (storedPrefix === prefix) {
                return;
            }
        }
        browser.localStorage.setItem(REMINDER_LS_KEY, `${prefix}.0`);
        browser.localStorage.removeItem(ARMED_KEY);
    };

    const getArmedAt = () => browser.localStorage.getItem(ARMED_KEY);

    const setArmedAt = (d) => browser.localStorage.setItem(ARMED_KEY, d);

    const cancelVisibilityTimer = () => {
        if (visibilityTimerId != null) {
            browser.clearTimeout(visibilityTimerId);
            visibilityTimerId = null;
        }
    };

    const tryShowReminder = async () => {
        if (
            document.visibilityState !== "visible" ||
            !isEligible() ||
            isDone() ||
            getPopover().isOpen
        ) {
            return;
        }
        const armedAt = getArmedAt();
        if (!armedAt || Date.now() < armedAt) {
            return;
        }
        await show();
        setDone();
    };

    const scheduleVisibilityShow = () => {
        if (visibilityTimerId != null) {
            return;
        }
        visibilityTimerId = browser.setTimeout(() => {
            visibilityTimerId = null;
            tryShowReminder();
        }, REMINDER_FOCUS_DELAY);
    };

    const onPresence = () => {
        if (isDone()) {
            return;
        }
        const armedAt = getArmedAt();
        const now = Date.now();
        if (!armedAt) {
            setArmedAt(now + REMINDER_DELAY);
            return;
        }
        if (now >= armedAt) {
            scheduleVisibilityShow();
        }
    };

    const onVisibilityChange = () => {
        if (document.visibilityState !== "visible") {
            cancelVisibilityTimer();
        }
    };

    // Cross-tab: Check Dismiss & Re-evaluate according to local state
    const onStorage = (e) => {
        if (e.key !== REMINDER_LS_KEY) {
            return;
        }
        if (e.newValue.at(-1) !== "1") {
            onPresence();
        }
    };

    useBus(presence.bus, "presence", onPresence);
    useListener(document, "visibilitychange", onVisibilityChange);
    useListener(window, "storage", onStorage);

// Resync Reminder when Eligible
    useEffect(() => {
        if (isEligible()) {
            syncStorage();
        }
    });

    return { syncStorage };
}
