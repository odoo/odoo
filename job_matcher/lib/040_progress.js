/* Progress reporting, phrased the way Survey phrases it.

   Survey counts what is behind you rather than where you are, so the first
   screen reads "0 of 3 answered" and the bar starts empty. Any screen that
   wants it just needs a [data-role=progress] label and a [data-role=bar]. */
JM.progress = {
    /* Answerable steps already behind the visitor. */
    answered: function () {
        return JM.flow.steps.slice(0, JM.flow.at).filter(JM.flow.counts).length;
    },

    total: function () {
        return JM.flow.total();
    },

    percentage: function () {
        if (!JM.progress.total()) {
            return 0;
        }
        return Math.round(100 * JM.progress.answered() / JM.progress.total());
    },

    /* Survey offers both readouts and picks one per survey; ours is
       progression_mode in data/config.json. */
    label: function () {
        if (JM.config.progression_mode === "number") {
            return JM.progress.answered() + " of " + JM.progress.total() + " answered";
        }
        return JM.progress.percentage() + "%";
    }
};
