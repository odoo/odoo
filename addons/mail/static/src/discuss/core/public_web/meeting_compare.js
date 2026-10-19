import { compareThreads } from "@mail/core/common/thread_compare";
import { compareFavorites } from "@mail/discuss/core/common/thread_compare_patch";
import { compareDatetime } from "@mail/utils/common/misc";

const { DateTime } = luxon;

/**
 * Order of the channels of a messaging menu tab, unless the tab or the active filter asks for
 * another one.
 *
 * @param {import("models").DiscussChannel} channel1
 * @param {import("models").DiscussChannel} channel2
 */
export function compareChannels(channel1, channel2) {
    return compareThreads(channel1.thread, channel2.thread) || channel2.id - channel1.id;
}

/**
 * Order of the meetings, read as an agenda: the one going on or coming next on top, the later
 * ones below, and the ones already over at the bottom, the most recently ended first. A meeting
 * hosting a call is going on however late it runs.
 *
 * @param {import("models").DiscussChannel} channel1
 * @param {import("models").DiscussChannel} channel2
 */
export function compareMeetings(channel1, channel2) {
    const favorite = compareFavorites(channel1.thread, channel2.thread);
    if (favorite !== undefined) {
        return favorite;
    }
    const now = DateTime.now();
    const isOver = (channel) =>
        Boolean(
            !channel.rtc_session_ids?.length &&
                channel.meeting_stop_dt &&
                channel.meeting_stop_dt < now
        );
    if (isOver(channel1) !== isOver(channel2)) {
        return isOver(channel1) ? 1 : -1;
    }
    const order = isOver(channel1)
        ? compareDatetime(channel2.meeting_stop_dt, channel1.meeting_stop_dt)
        : compareDatetime(channel1.meeting_start_dt, channel2.meeting_start_dt);
    return order || compareChannels(channel1, channel2);
}
