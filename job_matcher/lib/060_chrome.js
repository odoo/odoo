/* The toolbar that sits outside the card: progress and the arrow navigation.

   Survey keeps these fixed at the bottom of the viewport rather than inside the
   question, so they stay put as screens change. It is refreshed once per screen
   change, from the flow, instead of by every screen. */
JM.chrome = {
    bind: function () {
        JM.dom.inToolbar("nav_back").addEventListener("click", function () {
            JM.flow.back();
        });
        JM.dom.inToolbar("nav_next").addEventListener("click", function () {
            JM.flow.advance();
        });
    },

    render: function () {
        var step = JM.flow.current();
        var wrapper = JM.dom.inToolbar("progress_wrapper");

        /* The welcome and closing screens have nothing to report. */
        JM.dom.show(wrapper, JM.flow.counts(step));
        if (JM.flow.counts(step)) {
            JM.dom.text(JM.dom.inToolbar("progress"), JM.progress.label());
            JM.dom.inToolbar("bar").style.width = JM.progress.percentage() + "%";
        }

        var definition = JM.flow.definition();
        var canGoBack = true;
        if (definition.noBack) {
            canGoBack = false;
        }
        if (!JM.flow.at) {
            canGoBack = false;
        }
        JM.dom.inToolbar("nav_back").disabled = !canGoBack;
        JM.dom.inToolbar("nav_next").disabled = !definition.advance;
    }
};
