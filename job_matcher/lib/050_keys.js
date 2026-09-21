/* Keyboard navigation, mirroring the Survey app.

     Enter, ArrowRight   the primary action of the current screen
     ArrowLeft           back to the previous screen
     a letter            pick the answer carrying that key badge

   Survey listens on the document, and so do we, so the keys work without
   having to focus anything first. The cost is that these keys are claimed for
   the whole page, which is fine on a page whose only content is the app.

   While a field has the focus, everything belongs to the field and only
   Ctrl+Enter moves on (Cmd on a Mac), exactly as Survey does it: a stray Enter
   must not submit half-typed input. Screens with a field say so in their hint. */
JM.keys = {
    bind: function () {
        document.addEventListener("keydown", JM.keys.onKeyDown);
    },

    /* Every input type a visitor types into, not just "text": an email question
       renders type=email, and missing it would hand plain Enter the keyboard
       while Ctrl+Enter did nothing. */
    TYPED: ["text", "email", "tel", "number", "search", "url", "password"],

    isTyping: function () {
        var active = document.activeElement;
        if (!active) {
            return false;
        }
        var tag = active.tagName.toLowerCase();
        if (tag === "textarea") {
            return true;
        }
        if (tag === "input") {
            if (JM.keys.TYPED.indexOf(active.type) !== -1) {
                return true;
            }
        }
        return false;
    },

    onKeyDown: function (event) {
        if (event.altKey) {
            return;
        }
        var forcing = event.ctrlKey || event.metaKey;

        if (JM.keys.isTyping()) {
            if (event.key === "Enter") {
                /* Swallowed either way, so a stray Enter cannot submit a
                   surrounding form. */
                event.preventDefault();
                if (forcing) {
                    JM.flow.advance();
                }
            }
            return;
        }
        if (forcing) {
            return;
        }
        if (event.key === "Enter") {
            event.preventDefault();
            JM.flow.advance();
            return;
        }
        if (event.key === "ArrowRight") {
            event.preventDefault();
            JM.flow.advance();
            return;
        }
        if (event.key === "ArrowLeft") {
            JM.flow.back();
            return;
        }
        if (event.key.length === 1) {
            if (event.key.match(/[a-z]/i)) {
                JM.keys.pick(event.key.toUpperCase(), event);
            }
        }
    },

    /* Letter badges are per screen, so only the visible screen is searched. */
    pick: function (letter, event) {
        var screen = JM.dom.screen(JM.flow.current().screen);
        var input = screen.querySelector("input[data-key=" + letter + "]");
        if (!input) {
            return;
        }
        event.preventDefault();
        input.checked = true;
        input.dispatchEvent(new Event("change", {bubbles: true}));
    }
};
