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

    /* Chrome lives outside the screens, so it is addressed separately. */
    inToolbar: function (roleName) {
        return JM.dom.root().querySelector(
            ".jm_toolbar [data-role=" + roleName + "]");
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
    },

    /* The one place markup is injected, and only ever from data/*.json, which
       is authored at build time: question descriptions and job descriptions are
       rich text with links (the GDPR notice, for one). Never pass anything a
       visitor typed through here. */
    html: function (element, value) {
        element.innerHTML = value || "";
    },

    /* Validation alerts slide in and out, as Survey's do, so setting the text
       and toggling the state belong together. Passing an empty message hides
       the alert. */
    error: function (element, message) {
        JM.dom.text(element, message);
        element.classList.toggle("jm_error_shown", !!message);
    }
};
