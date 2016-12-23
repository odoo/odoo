$(document).ready(function () {

    // When choosing an acquirer, display its Pay Now button
    var $payment = $("#payment_method");
    $payment.on("click", "input[name='acquirer']", function (ev) {
            var payment_id = $(ev.currentTarget).val();
            $("div.oe_sale_acquirer_button[data-id]", $payment).addClass("hidden");
            $("div.oe_sale_acquirer_button[data-id='"+payment_id+"']", $payment).removeClass("hidden");
        })
        .find("input[name='acquirer']:checked").click();

    // When clicking on payment button: create the tx using json then continue to the acquirer
    $payment.on("click", 'button[type="submit"],button[name="submit"]', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var $form = $(ev.currentTarget).parents('form');
      $form.validate({
	rules:{
		confirm_code:{
		    required: true,
		    minlength: 9,
		    maxlength: 9
		}
	},
	messages:{
		confirm_code:{
                    required: "You must enter MPESA confirmation code to proceed",
                    minlength: "MPESA Confirmation code is at least 9 characters long",
                    maxlength: "MPESA Confirmation code is at most 9 characters long"
                }
	}	
      });
      var acquirer_id = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
      if (! acquirer_id) {
        return false;
      }
      openerp.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {}).then(function (data) {
        $form.submit();
      });
   });

});
