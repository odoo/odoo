odoo.define('pragtech_tender_management.tenders', function (require) {

    $(document).ready(function() {
        $('.material_input_amount').css('display','none')
        $('.labour_input_amount').css('display','none')
        $('.overhead_input_amount').css('display','none')
        $('.total_input_amount').css('display','none')

        $('input[class=material_your_price]').change(function(event) {
            if(event && event.currentTarget && event.currentTarget.attributes && event.currentTarget.attributes.my_id) {
                var id = event.currentTarget.attributes.my_id.value
                var a = ''
                var b = ''
                var qty = '#material_quantity-'+id+' span'
                var price = 'input[name=material_your_price-'+id+']'
                var mat_amt = '#material_amount-'+id+' span'
                var total = '#total_amount'
                var total_amount_duplicate = '#total_amount_duplicate'
                var material_amount_duplicate = 'material_amount_duplicate-'+id
                var labour_amount_duplicate = 'labour_amount_duplicate-'+id
                var overhead_amount_duplicate = 'overhead_amount_duplicate-'+id

                a = $(qty).text()
                b = $(price)[0].value

                var aa = a.replace(/[^0-9.-]+/g,"");
                var aValue = parseFloat(aa)

                var bb = b.replace(/[^0-9.-]+/g,"");
                var bValue = parseFloat(bb)

                var material_amount = aValue * bValue

                var mat_amt1 = $('#material_amount-'+id+' span').text(material_amount)
                $('[name="' + material_amount_duplicate + '"]').val(material_amount)

                var mat_all = $('.material_amount')
                var lab_all = $('.labour_amount')
                var overhead_all = $('.overhead_amount')
                var all_tot = 0.00

                for (var i=0; i<mat_all.length; i++) {
                    all_tot += Number(mat_all[i].innerText)
                    material_amount_duplicate = Number(mat_all[i].innerText)
                    $(material_amount_duplicate).val(material_amount)
                }

                for (var i=0; i<lab_all.length; i++) {
                    all_tot += Number(lab_all[i].innerText)
                    labour_amount_duplicate = Number(lab_all[i].innerText)
                    $(labour_amount_duplicate).val(labour_amount)
                }

                for (var i=0; i<overhead_all.length; i++) {
                    all_tot += Number(overhead_all[i].innerText)
                    overhead_amount_duplicate = Number(overhead_all[i].innerText)
                    $(overhead_amount_duplicate).val(overhead_amount)
                }

                $(total).html(all_tot)
                $(total_amount_duplicate).val(all_tot)
            }
        });

        $('input[class=labour_your_price]').change(function(event) {
            if(event && event.currentTarget && event.currentTarget.attributes && event.currentTarget.attributes.my_id) {
                var id = event.currentTarget.attributes.my_id.value
                var qty2 = '#labour_quantity-'+id+' span'
                var price2 = 'input[name=labour_your_price-'+id+']'
                var mat_amt = '#labour_amount-'+id+' span'
                var total = '#total_amount'
                var total_amount_duplicate = '#total_amount_duplicate'
                var material_amount_duplicate = 'material_amount_duplicate-'+id
                var labour_amount_duplicate = 'labour_amount_duplicate-'+id
                var overhead_amount_duplicate = 'overhead_amount_duplicate-'+id

                a2 = $(qty2).text()
                b2 = $(price2)[0].value

                var aa2 = a2.replace(/[^0-9.-]+/g,"");
                var aValue2 = parseFloat(aa2)

                var bb2 = b2.replace(/[^0-9.-]+/g,"");
                var bValue2 = parseFloat(bb2)

                var labour_amount = aValue2 * bValue2
                var lab_amt1 = $('#labour_amount-'+id+' span').text(labour_amount)
                $('[name="' + labour_amount_duplicate + '"]').val(labour_amount)

                var mat_all = $('.material_amount')
                var lab_all = $('.labour_amount')
                var overhead_all = $('.overhead_amount')
                var all_tot = 0.00

                for (var i=0; i<mat_all.length; i++) {
                    all_tot += Number(mat_all[i].innerText)
                    material_amount_duplicate = Number(mat_all[i].innerText)
                    $(material_amount_duplicate).val(material_amount)
                }

                for (var i=0; i<lab_all.length; i++) {
                    all_tot += Number(lab_all[i].innerText)
                    labour_amount_duplicate = Number(lab_all[i].innerText)
                    $(labour_amount_duplicate).val(labour_amount)
                }

                for (var i=0; i<overhead_all.length; i++) {
                    all_tot += Number(overhead_all[i].innerText)
                    overhead_amount_duplicate = Number(overhead_all[i].innerText)
                    $(overhead_amount_duplicate).val(overhead_amount)
                }

                $(total).html(all_tot)
                $(total_amount_duplicate).val(all_tot)
            }
        });

        $('input[class=overhead_your_price]').change(function(event) {
            if(event && event.currentTarget && event.currentTarget.attributes && event.currentTarget.attributes.my_id) {
                var id = event.currentTarget.attributes.my_id.value
                var qty3 = '#overhead_quantity-'+id+' span'
                var price3 = 'input[name=overhead_your_price-'+id+']'
                var overhead_amt = '#overhead_amount-'+id+' span'
                var total = '#total_amount'
                var total_amount_duplicate = '#total_amount_duplicate'
                var material_amount_duplicate = 'material_amount_duplicate-'+id
                var labour_amount_duplicate = 'labour_amount_duplicate-'+id
                var overhead_amount_duplicate = 'overhead_amount_duplicate-'+id

                a3 = $(qty3).text()
                b3 = $(price3)[0].value

                var aa3 = a3.replace(/[^0-9.-]+/g,"");
                var aValue3 = parseFloat(aa3)

                var bb3 = b3.replace(/[^0-9.-]+/g,"");
                var bValue3 = parseFloat(bb3)

                var overhead_amount = aValue3*bValue3

                var overhead_amt1 = $('#overhead_amount-'+id+' span').text(overhead_amount)
                $('[name="' + overhead_amount_duplicate + '"]').val(overhead_amount)
                var mat_all = $('.material_amount')
                var lab_all = $('.labour_amount')
                var overhead_all = $('.overhead_amount')
                var all_tot = 0.00

                for (var i=0; i<mat_all.length; i++) {
                    all_tot += Number(mat_all[i].innerText)
                    material_amount_duplicate = Number(mat_all[i].innerText)
                    $(material_amount_duplicate).val(material_amount)
                }

                for (var i=0; i<lab_all.length; i++) {
                    all_tot += Number(lab_all[i].innerText)
                    labour_amount_duplicate = Number(lab_all[i].innerText)
                    $(labour_amount_duplicate).val(labour_amount)
                }

                for (var i=0; i<overhead_all.length; i++) {
                    all_tot += Number(overhead_all[i].innerText)
                    overhead_amount_duplicate = Number(overhead_all[i].innerText)
                    $(overhead_amount_duplicate).val(overhead_amount)
                }

                $(total).html(all_tot)
                $(total_amount_duplicate).val(all_tot)
            }
        });

    })

})

