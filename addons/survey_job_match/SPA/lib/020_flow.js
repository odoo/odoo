/* Screen registry and the linear walk through them.

   A screen definition may provide:
     setup()      once at boot: wire listeners that never change
     enter(step)  every time the screen becomes visible, with its step
     advance()    what the primary action does, so Enter and the arrow keys can
                  trigger exactly the same path as the button
     noBack       true to refuse backwards navigation out of this screen
     counted      false for screens that are not steps the visitor answers, so
                  the welcome and closing screens stay out of the progress count

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
        var steps = [{screen: "start"}];
        (JM.data.questions || []).forEach(function (question, index) {
            /* The question's type picks the screen that renders it. */
            var screen = "question";
            if (question.type === "text") {
                screen = "text";
            }
            steps.push({screen: screen, question: question, index: index});
        });
        steps.push({screen: "result"});
        JM.flow.steps = steps;
    },

    /* A step counts toward progress unless its screen opts out. */
    counts: function (step) {
        return JM.screens[step.screen].counted !== false;
    },

    /* How many steps the visitor actually answers. */
    total: function () {
        return JM.flow.steps.filter(JM.flow.counts).length;
    },

    current: function () {
        return JM.flow.steps[JM.flow.at];
    },

    definition: function () {
        return JM.screens[JM.flow.current().screen];
    },

    /* True when no answerable step follows this one, which is what turns the
       primary button into Submit. */
    isLast: function () {
        return !JM.flow.steps.slice(JM.flow.at + 1).filter(JM.flow.counts).length;
    },

    goTo: function (index) {
        /* Hiding a screen does not blur a field inside it, and a focused field
           swallows the keyboard shortcuts, so hand the focus back first. */
        var active = document.activeElement;
        if (active) {
            if (JM.dom.root().contains(active)) {
                active.blur();
            }
        }

        JM.flow.at = index;
        var step = JM.flow.current();
        JM.dom.allScreens().forEach(function (element) {
            JM.dom.show(element, element.dataset.screen === step.screen);
        });
        var definition = JM.screens[step.screen];
        if (definition.enter) {
            definition.enter(step);
        }
        /* The toolbar lives outside the screens, so it is refreshed here rather
           than by each of them. */
        JM.chrome.render();
    },

    next: function () {
        JM.flow.goTo(JM.flow.at + 1);
    },

    back: function () {
        if (JM.flow.definition().noBack) {
            return;
        }
        if (JM.flow.at) {
            JM.flow.goTo(JM.flow.at - 1);
        }
    },

    /* The primary action of whatever screen is showing. */
    advance: function () {
        var definition = JM.flow.definition();
        if (definition.advance) {
            definition.advance();
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
    JM.keys.bind();
    JM.chrome.bind();
    JM.flow.goTo(0);
};
