/** @odoo-module **/
//enables a popover on elements with the ID 'popover' when a mouseover event occurs.
  $(document).on("mouseover", "#popover", function (event) {
    var self = this;
    var item_text = "";
    if (self.parentElement.parentElement.children[3]) {
      item_text =
        "Ticket : " +
        self.parentElement.parentElement.children[1].outerText +
        "<br/>" +
        "Subject : " +
        self.parentElement.parentElement.children[2].outerText +
        "<br/>" +
        "Cost : " +
        self.parentElement.parentElement.children[4].outerText +
        "<br/>" +
        "Priority : " +
        self.parentElement.parentElement.children[6].outerText+
          "<br/>" +"<br/>" +
         "Description : " +
        self.parentElement.parentElement.children[3].outerText +
        "<br/>";
    }
    $(this).popover({
      html: true,
      placement: "right",
      trigger: "hover",
      title: "Ticket Details",
      content: "<span>" + item_text + "</span>",
    });
  });
