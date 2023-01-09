$(function () {
    $('input.o-purchase-datetimepicker').datetimepicker();
    $('input.o-purchase-datetimepicker').on("hide.datetimepicker", function () {
        $(this).parents('form').submit();
    });
})
