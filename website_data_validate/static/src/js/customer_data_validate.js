$(document).ready(function () {

    var $checkout_form = $("#CheckoutForm");
      $checkout_form.validate({
	rules:{
		email:{
		    required: true,
		    email: true,
		    minlength:2
		},
		name:{
		    required: true,
		    minlength:2
		},
		shipping_name:{
		    required: true,
		    minlength:2
		},
		street2:{
		    required: true,
		    minlength:2
		},
		shipping_street:{
		    required: true,
		    minlength:2
		},
		city:{
		    required: true,
		    minlength:2
		},
		shipping_city:{
		    required: true,
		    minlength:2
		},
		country_id:{
		    required: true,
		    number: true,
		    minlength:1
		},
		shipping_country_id:{
		    required: true,
		    number: true,
		    minlength:1
		},
		phone:{
		    required: true,
		    number: true,
		    minlength:8
		},
		shipping_phone:{
		    required: true,
		    number: true,
		    minlength:8
		}

	},
	messages:{
		email:{
                    required: "Please enter your email",
                    email: "Please enter a valid email"
                },
		name:{
                    required: "Please enter your name"
                },
		shipping_name:{
                    required: "Please enter your shipping name"
                },
		street2:{
                    required: "Please enter your street"
                },
		shipping_street:{
                    required: "Please enter your shipping street"
                },
		city:{
                    required: "Please enter your city"
                },
		shipping_city:{
                    required: "Please enter your shipping city"
                },
		country_id:{
                    required: "Please select your country",
                    number: "Please select a valid country_id"
                },
		shipping_country_id:{
                    required: "Please select your shipping country",
                    number: "Please select a valid shipping country"
                },
		phone:{
                    required: "Please enter your phone number",
		    number: "Please enter a valid phone number",
		    minlength: "Please enter at least 8 digits as phone number"
                },
		shipping_phone:{
                    required: "Please enter your shipping phone number",
		    number: "Please enter a valid shipping phone number",
		    minlength: "Please enter at least 8 digits as shipping phone number"
                }
	}	
      });
});
