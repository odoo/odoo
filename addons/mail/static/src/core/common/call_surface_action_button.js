import { ActionButton } from "@mail/core/common/action_button";

/**
 * Chrome for actions rendered on a call surface: the call view, a fullscreen
 * meeting, the call invitation, the pip banner, or the welcome page. Adds the
 * enlarged fullscreen-meeting sizing on top of the base chrome; dark-theme
 * simulation is already handled generically by {@link ActionButton}.
 */
export class CallSurfaceActionButton extends ActionButton {
    get isFullscreenCallButton() {
        return this.props.inline && this.env.inMeetingView && this.store.rtc.isFullscreen;
    }
}
