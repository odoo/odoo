export class TalkingDetector {
    windowMs = 3000;
    dutyCycleThreshold = 0.6;

    _bursts = [];
    _burstStart = null;
    _timer;

    constructor(rtc) {
        this.rtc = rtc;
    }

    start() {
        this.stop();
        this.rtc.onChange(
            () => [this.rtc.selfSession?.isTalking, this.rtc.selfSession?.isMute],
            (isTalking, isMute) => {
                this._onStateChange(isTalking, isMute);
            }
        );
    }

    _shouldTrackTalking() {
        return (
            this.rtc.selfSession.isMute &&
            !this.rtc.showTalkWhileMutedSuggestion &&
            !this.rtc.isTalkWhileMutedSuggestionDismissed &&
            !this.rtc.isTalkWhileMutedSuggestionDisabled
        );
    }

    _onStateChange(isTalking, isMute) {
        if (!isMute) {
            this.stop();
            return;
        }
        if (!this._shouldTrackTalking()) {
            return;
        }
        this._clearTimer();
        const now = performance.now();
        if (isTalking && this._burstStart === null) {
            this._burstStart = now;
        } else if (!isTalking && this._burstStart !== null) {
            this._bursts.push({ start: this._burstStart, end: now });
            this._burstStart = null;
        }
        this._evaluate(now);
    }

    _evaluate(now) {
        const windowStart = now - this.windowMs;
        this._bursts = this._bursts.filter((burst) => burst.end > windowStart);
        let talkingTime = 0;
        for (const burst of this._bursts) {
            const talkingStart = Math.max(burst.start, windowStart);
            talkingTime += burst.end - talkingStart;
        }
        if (this._burstStart !== null) {
            const talkingStart = Math.max(this._burstStart, windowStart);
            talkingTime += now - talkingStart;
        }
        const thresholdMs = this.dutyCycleThreshold * this.windowMs;
        if (talkingTime >= thresholdMs) {
            this.rtc.showTalkWhileMutedSuggestion = true;
            return;
        }
        // ensure evaluation even if no future state change occurs
        if (this._burstStart !== null) {
            const delay = Math.max(0, thresholdMs - talkingTime);
            this._timer = setTimeout(() => {
                this._timer = undefined;
                this._evaluate(performance.now());
            }, delay);
        }
    }

    _clearTimer() {
        clearTimeout(this._timer);
        this._timer = undefined;
    }

    stop() {
        this._clearTimer();
        this._bursts = [];
        this._burstStart = null;
        this.rtc.showTalkWhileMutedSuggestion = false;
        this.rtc.isTalkWhileMutedSuggestionDismissed = false;
    }
}
