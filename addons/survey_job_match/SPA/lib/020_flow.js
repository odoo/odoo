/* Screen registry and the linear walk through them.

   A screen definition may provide:
     setup()      once at boot: wire listeners that never change
     enter(step)  every time the screen becomes visible, with its step

   The step list is built from the data, not hardcoded, so adding questions to
   data/questions.json adds screens to the flow with no code change. One markup
   fragment can therefore serve many steps -- the question screen does. */
JM.registerScreen = function (name, definition) {
    JM.screens[name] = definition;
};

JM.flow = {
    steps: [],
    at: 0,

    build: function () {
        var steps = [{screen: "name"}];
        (JM.data.questions || []).forEach(function (question, index) {
            steps.push({screen: "question", question: question, index: index});
        });
        steps.push({screen: "done"});
        JM.flow.steps = steps;
    },

    /* Steps the visitor fills in, excluding the closing screen. */
    total: function () {
        return JM.flow.steps.length - 1;
    },

    /* "Step 2 of 3", or empty on the closing screen. */
    label: function () {
        if (JM.flow.total() > JM.flow.at) {
            return "Step " + (JM.flow.at + 1) + " of " + JM.flow.total();
        }
        return "";
    },

    current: function () {
        return JM.flow.steps[JM.flow.at];
    },

    goTo: function (index) {
        JM.flow.at = index;
        var step = JM.flow.current();
        JM.dom.allScreens().forEach(function (element) {
            JM.dom.show(element, element.dataset.screen === step.screen);
        });
        var definition = JM.screens[step.screen];
        if (definition.enter) {
            definition.enter(step);
        }
    },

    next: function () {
        JM.flow.goTo(JM.flow.at + 1);
    },

    back: function () {
        if (JM.flow.at) {
            JM.flow.goTo(JM.flow.at - 1);
        }
    }
};

JM.boot = function () {
    var root = JM.dom.root();
    if (!root) {
        return;
    }
    /* The snippet is stored twice in the page and the editor can re-inject it,
       so refuse to wire the same root up more than once. */
    if (root.dataset.jmReady) {
        return;
    }
    root.dataset.jmReady = "1";

    JM.config = JM.data.config || {};
    Object.keys(JM.screens).forEach(function (name) {
        var definition = JM.screens[name];
        if (definition.setup) {
            definition.setup();
        }
    });
    JM.flow.build();
    JM.flow.goTo(0);
};
