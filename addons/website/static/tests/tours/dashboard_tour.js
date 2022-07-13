odoo.define("website.tour.backend_dashboard", function (require) {
  "use strict";

  const wTourUtils = require("website.tour_utils");

  wTourUtils.registerEditionTour(
    "backend_dashboard",
    {
      test: true,
      url: '/',
    },
    [
      {
        trigger: 'button[data-menu-xmlid="website.menu_reporting"]',
      },
      {
        trigger: '.dropdown-item[data-menu-xmlid="website.menu_website_google_analytics"]',
      },
      {
        // Analytics section should always be present even when empty / not hooked to anything
        trigger: 'h2:contains("Analytics")',
        content: "Check if dashboard loads",
        run: function () {},
      },
    ]
  );
});
