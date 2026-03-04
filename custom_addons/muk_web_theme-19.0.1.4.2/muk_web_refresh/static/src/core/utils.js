import { session } from '@web/session';

const DEFAULT_INTERVAL = 30000;

export function getAutoLoadInterval() {
    return session.pager_autoload_interval ?? DEFAULT_INTERVAL;
}
