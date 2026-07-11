import { session } from '@web/session';

const DEFAULT_INTERVAL = 30000;

/**
 * Return the configured auto-load interval in milliseconds.
 *
 * @returns {number}
 */
export function getAutoLoadInterval() {
    return session.pager_autoload_interval ?? DEFAULT_INTERVAL;
}
