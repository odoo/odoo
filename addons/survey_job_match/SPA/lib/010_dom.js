/* Small DOM helpers.

   Everything is looked up through the app root and addressed by data-screen /
   data-role attributes, so markup fragments and behaviour files stay decoupled:
   restyling a screen never breaks its JS as long as the roles survive.

   Text is always written with textContent. Markup is never built from strings,
   both because it would be an injection risk and because a less-than sign
   cannot appear in this code at all. Build nodes with createElement instead. */
JM.dom = {
    root: function () {
        return document.getElementById("jm_app");
    },

    screen: function (name) {
        return JM.dom.root().querySelector("[data-screen=" + name + "]");
    },

    /* The element playing `role` inside `screenName`. */
    role: function (screenName, roleName) {
        return JM.dom.screen(screenName).querySelector("[data-role=" + roleName + "]");
    },

    allScreens: function () {
        return Array.prototype.slice.call(
            JM.dom.root().querySelectorAll("[data-screen]"));
    },

    show: function (element, visible) {
        element.classList.toggle("jm_hide", !visible);
    },

    text: function (element, value) {
        element.textContent = value || "";
    }
};
