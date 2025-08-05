/** @odoo-module **/

$(document).on("show.bs.modal", ".modal", function () {
  $("body").addClass("body-has-active-modal");
});

$(document).on("hidden.bs.modal", ".modal", function () {
  setTimeout(function () {
    if ($(".modal.show").length === 0) {
      $("body").removeClass("body-has-active-modal");
    }
  }, 100);
});
